"""Read-only UT/DR extraction using an explicitly supplied UMT CLI."""
import argparse,hashlib,json,os,subprocess,time,re,sys
from pathlib import Path
SCRIPT=Path(__file__).resolve().parent/'export.csx'
if not SCRIPT.exists():SCRIPT=Path(__file__).resolve().parents[1]/'export.csx'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def discover(game, kind):
    game=Path(game).resolve()
    if kind=='UT':
        source=game/'data.win'
        if not source.is_file():raise ValueError('UT 目录中找不到 data.win')
        return [(None,source)]
    sources=[]
    for directory in game.iterdir():
        match=re.fullmatch(r'chapter([1-9][0-9]*)_windows',directory.name,re.IGNORECASE)
        if match and (directory/'data.win').is_file():sources.append((int(match[1]),directory/'data.win'))
    if not sources:raise ValueError('DR 目录中找不到 chapterN_windows/data.win')
    sources.sort()
    if len({ch for ch,_ in sources})!=len(sources):raise ValueError('同一章节存在多个目录')
    return sources

def extract(game, umt, out, kind, version='', progress=lambda message:None, cancel=lambda:False):
    class Args:pass
    a=Args();a.game=Path(game);a.umt=Path(umt);a.out=Path(out)
    out=a.out.resolve();game=a.game.resolve();cli=a.umt.resolve()
    if out==game or out.is_relative_to(game):raise ValueError('Output must be separate from game')
    out.mkdir(parents=True,exist_ok=False);(out/'logs').mkdir(exist_ok=True)
    sources=discover(game,kind);source=[p for _,p in sources]
    fingerprints={str(p):sha(p) for p in source}
    dedicated=cli.name.lower()=='spriteextractor.exe'
    evidence={'schema':1,'game':kind,'game_version':version,'inputs':fingerprints,'umt_sha256':sha(cli),'export_script_sha256':sha(SCRIPT),'started':time.strftime('%Y-%m-%dT%H:%M:%S')}
    if dedicated:
        evidence['extractor_sha256']=sha(cli.with_suffix('.dll'))
        evidence['umt_library_sha256']=sha(cli.parent/'UndertaleModLib.dll')
    prior=out/'provenance.json'
    if prior.exists():
        old=json.loads(prior.read_text(encoding='utf-8'))
        if any(old.get(k)!=evidence[k] for k in ('inputs','umt_sha256','export_script_sha256')):raise ValueError('Existing export has different inputs/tools; choose a new output directory')
    save(prior,evidence)
    for ch,package in sources:
        if (out/f'chapters/ch{ch}.json').exists():continue
        progress('正在提取 '+(f'第 {ch} 章' if ch else 'UNDERTALE'))
        if cancel():raise InterruptedError('已取消导入')
        env={**os.environ,'DR_LIBRARY_OUT':str(out),'DR_LIBRARY_CHAPTER':f'ch{ch}'}
        with (out/f'logs/ch{ch}.log').open('w',encoding='utf-8') as log:
            command=[str(cli),str(package)] if dedicated else [str(cli),'load',str(package),'-s',str(SCRIPT)]
            process=subprocess.Popen(command,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
            try:
                while process.poll() is None:
                    if cancel():raise InterruptedError('已取消导入')
                    time.sleep(.1)
                if process.returncode:raise RuntimeError('UMT 提取失败：'+(out/f'logs/ch{ch}.log').read_text(encoding='utf-8',errors='replace')[-2000:])
            except BaseException:
                process.kill();process.wait();raise
    groups={};totals=[];errors=[]
    for ch,_ in sources:
        data=json.loads((out/f'chapters/ch{ch}.json').read_text(encoding='utf-8-sig'));totals.append({'chapter':ch,'resources':len(data['entries']),'frames':sum(len(e['frames']) for e in data['entries'])});errors.extend({'chapter':ch,**e} for e in data['errors'])
        for e in data['entries']:
            # Storage geometry differs between atlases; identity uses decoded full frames and resource metadata.
            identity={k:v for k,v in e.items() if k not in ('index','frames')};identity['frames']=[{k:f[k] for k in ('pixel_sha256','width','height','missing','error') if k in f} for f in e['frames']]
            sig=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
            group=groups.setdefault((e['kind'],e['name']),{'kind':e['kind'],'name':e['name'],'variants':{}})
            variant=group['variants'].setdefault(sig,{'id':sig,**{k:v for k,v in e.items() if k!='index'},'chapters':[],'resource_indices':{}})

            if ch is not None:variant['chapters'].append(ch)
            variant['resource_indices'][str(ch)]=e['index']
    items=[]
    for g in sorted(groups.values(),key=lambda g:(g['kind'],g['name'].lower())):
        g['variants']=list(g['variants'].values());items.append(g)
    images=list((out/'images').rglob('*.png'))
    report={'chapters':totals,'names':len(items),'variants':sum(len(g['variants']) for g in items),'different_same_name':sum(len(g['variants'])>1 for g in items),'unique_images':len(images),'image_bytes':sum(p.stat().st_size for p in images),'errors':errors,'no_texture_resources':sum(not v['frames'] or all('image' not in f for f in v['frames']) for g in items for v in g['variants'])}
    catalog={'schema':1,'summary':report,'items':items};save(out/'catalog.json',catalog)
    (out/'catalog.js').write_text('window.SPRITE_LIBRARY='+json.dumps(catalog,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
    if {str(p):sha(p) for p in source}!=fingerprints:raise ValueError('Game package changed during export')
    evidence['finished']=time.strftime('%Y-%m-%dT%H:%M:%S');evidence['inputs_unchanged']=True;save(prior,evidence);save(out/'report.json',report)
    progress('提取完成，正在制作 ZIP')
    return evidence


def main():
    p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--umt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--kind',choices=['UT','DR'],required=True);p.add_argument('--version',default='');a=p.parse_args()
    extract(a.game,a.umt,a.out,a.kind,a.version,progress=lambda message:print(message,flush=True))

if __name__=='__main__':main()
