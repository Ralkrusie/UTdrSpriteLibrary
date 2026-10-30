"""Copy one named resource's frames into readable filenames, preserving variants."""
import argparse,json,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--library',type=Path,default=Path(__file__).resolve().parents[1]/'library');p.add_argument('--out',type=Path,required=True);p.add_argument('--kind',choices=['sprite','background','font']);a=p.parse_args()
root=a.library.resolve();out=a.out.resolve()
if out==root or out.is_relative_to(root):raise SystemExit('Choose an output outside the library')
if out.exists():raise SystemExit('Output exists; choose a new folder')
data=json.loads((root/'catalog.json').read_text(encoding='utf-8'));matches=[g for g in data['items'] if g['name']==a.name and (not a.kind or g['kind']==a.kind)]
if not matches:raise SystemExit('Resource name not found (exact case required)')
out.mkdir(parents=True)
for g in matches:
    safe=re.sub(r'[^a-zA-Z0-9_-]','_',g['name'])
    for v in g['variants']:
        folder=out/(g['kind']+'_'+safe+'_ch'+'-'.join(map(str,v['chapters']))+'_'+v['id'][:8]);folder.mkdir()
        for i,f in enumerate(v['frames']):
            if 'image' not in f:continue
            src=(root/f['image']).resolve()
            if not src.is_relative_to(root/'images'):raise ValueError('Unsafe image path')
            shutil.copyfile(src,folder/f'{safe}_{i:04d}.png')
        (folder/'metadata.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(out)
