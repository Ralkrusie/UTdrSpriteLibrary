"""Bundle the mobile UI into one file:// HTML and a seekable, stored asset ZIP."""
import argparse
import json
import zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def replace_once(text, old, new):
    if text.count(old)!=1:
        raise ValueError('Mobile source changed; update offline adapter: '+old[:70])
    return text.replace(old,new,1)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    app=(HERE/'app.js').read_text(encoding='utf-8')
    app=replace_once(app,"import {apng} from './encode.js';\nimport {gif} from './gif.js';",'')
    start=app.index('async function json(');end=app.index('\nasync function detail(',start)
    app=app[:start]+"async function json(path){if(!offlineArchive)throw Error('请先选择素材包');return offlineArchive.json(path)}"+app[end:]
    app=replace_once(app,'i.src=path;await i.decode();return i',"const url=await offlineArchive.image(path);try{i.src=url;await i.decode();const frame=document.createElement('canvas');frame.width=i.naturalWidth;frame.height=i.naturalHeight;frame.getContext('2d').drawImage(i,0,0);return frame}finally{URL.revokeObjectURL(url)}")
    app=replace_once(app,'img.src=v.thumbnail;', 'offlineThumbnail(img,v.thumbnail);')
    app=replace_once(app,"$('retry').onclick=init;init();", "$('retry').onclick=init;mountOffline();")
    encoder=(HERE/'encode.js').read_text(encoding='utf-8').replace('export function ','function ').replace('export async function ','async function ')
    script=encoder+'\n'+(HERE/'gif.js').read_text(encoding='utf-8').replace('export function ','function ')+'\n'+(HERE/'offline.js').read_text(encoding='utf-8')+'\n'+app
    html=(HERE/'index.html').read_text(encoding='utf-8')
    html=replace_once(html,'<link rel="stylesheet" href="style.css">','<style>'+(HERE/'style.css').read_text(encoding='utf-8')+'\n#pack-input{max-width:100%;width:100%}#pack-status{overflow-wrap:anywhere}</style>')
    html=replace_once(html,'第 1–5 章 · 手机版','第 1–5 章 · 离线版')
    html=replace_once(html,'<main>', '<section style="padding:16px"><button id="choose-pack" type="button">选择素材包（无需解压）</button><input id="pack-input" hidden type="file" accept=".zip,application/zip"><p id="pack-status" role="status">选择随附的素材包.zip。关闭页面后，下次打开需要重新选择。</p></section><main>')
    html=replace_once(html,'<script type="module" src="app.js"></script>','<script>'+script.replace('</script','<\\/script')+'</script>')
    (args.out/'打开素材库.html').write_text(html,encoding='utf-8')
    cat=json.loads((ROOT/'library/catalog.json').read_text(encoding='utf-8'))
    variants=[v for g in cat['items'] if g['kind']=='sprite' for v in g['variants']]
    def dump(data):return json.dumps(data,ensure_ascii=False,separators=(',',':'))
    with zipfile.ZipFile(args.out/'素材包.zip','w',compression=zipfile.ZIP_STORED) as z:
        z.writestr('offline-pack.json',dump({'format':'deltarune-sprites-offline','version':1}))
        index=[];images=set()
        for start in range(0,len(variants),128):
            shard=str(start//128);details={}
            for v in variants[start:start+128]:
                frames=[f.get('image') for f in v['frames']]
                images.update(f for f in frames if f)
                details[v['id']]={'frames':frames}
                index.append(dict(id=v['id'],name=v['name'],chapters=v['chapters'],width=v['width'],height=v['height'],count=len(frames),complete=bool(frames) and all(frames),thumbnail=next((f for f in frames if f),None),shard=shard))
            z.writestr('data/'+shard+'.json',dump(details))
        z.writestr('data/index.json',dump(index))
        for name in sorted(images):z.write(ROOT/'library'/name,name)
    (args.out/'使用说明.txt').write_text('1. 解压外层分享包。不要解压“素材包.zip”。\n2. 用浏览器打开“打开素材库.html”。\n3. 点击选择素材包，选择同目录的“素材包.zip”。无需联网或启动服务。\n4. 搜索、预览，导出后点击“保存文件”。全部帧直接生成多张图片，可保存全部或逐张保存。\n\n关闭页面后需重新选择素材包。安卓文件管理器若仅预览 HTML，请尝试“用浏览器打开”；不同手机是否允许执行本地 HTML 需要实测。支持 PNG、APNG、GIF；预设暂不支持。游戏素材版权归原权利人。\n',encoding='utf-8-sig')
    bundle=args.out.parent/(args.out.name+'.zip')
    with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in args.out.iterdir():z.write(file,file.name)
    print(json.dumps({'bundle':str(bundle.resolve()),'bytes':bundle.stat().st_size,'images':len(images)},ensure_ascii=False))

if __name__=='__main__':main()
