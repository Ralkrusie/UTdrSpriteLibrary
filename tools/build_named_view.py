"""Create a human-readable, same-volume hard-link view of the local image library."""
import argparse,json,os,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--library',type=Path,default=Path(__file__).resolve().parents[1]/'library');a=p.parse_args();root=a.library.resolve();out=root/'按名称'
data=json.loads((root/'catalog.json').read_text(encoding='utf-8'))
labels={'sprite':'精灵','background':'背景与图块','font':'字体图集'}
def safe(name):
    result=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',name).rstrip(' .')
    if result.upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:result='_'+result
    return result or '_'
seen={};count=0;missing=0;mapping=[]
for g in data['items']:
    name=safe(g['name']);token=(g['kind'],name.casefold())
    if token in seen and seen[token]!=g['name']:name+='_'+g['variants'][0]['id'][:8]
    seen[token]=g['name']
    for v in g['variants']:
        folder=out/labels[g['kind']]/name/('Ch'+'-'.join(map(str,v['chapters'])))
        folder.mkdir(parents=True,exist_ok=True)
        for i,f in enumerate(v['frames']):
            if 'image' not in f:missing+=1;continue
            src=(root/f['image']).resolve()
            if not src.is_relative_to(root/'images'):raise ValueError('Unsafe input path')
            dst=folder/f'{name}_{i:04d}.png'
            if dst.exists():
                if not os.path.samefile(src,dst):raise ValueError(f'Existing unrelated file: {dst}')
            else:os.link(src,dst)
            if not os.path.samefile(src,dst):raise ValueError(f'Link verification failed: {dst}')
            count+=1
        mapping.append({'name':g['name'],'kind':g['kind'],'chapters':v['chapters'],'variant':v['id'],'folder':folder.relative_to(root).as_posix()})
(root/'named-index.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'使用说明.txt').write_text('这里使用游戏原始资源名。\n目录：类型 / 资源名 / Ch章节列表 / 资源名_从0000开始的帧序.png\nCh2-3-4-5 表示这几章共用这一变体；同名不同变体分别放置。\n这些 PNG 是去重原图的硬链接，增加名字而不重复存储图片内容。查看和复制即可；如需编辑，请先复制到别处，避免改动共享原图。\n没有 PNG 的目录代表资源没有普通位图帧，详细数据见 catalog.json。\n',encoding='utf-8')
print(json.dumps({'named_pngs':count,'variant_folders':len(mapping),'non_image_slots':missing,'output':str(out)},ensure_ascii=False))
