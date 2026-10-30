"""Typeset only the fixed title's visible pixels; never embed the font atlas."""
import argparse, json, hashlib
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('--metrics',type=Path,required=True);p.add_argument('--atlas',type=Path,required=True);a=p.parse_args()
d=json.loads(a.metrics.read_text(encoding='utf-8'));assert d['name']=='fnt_main'
glyphs={g['code']:g for g in d['glyphs']};text='UTdrSpriteLibrary';x=0;parts=[]
with Image.open(a.atlas) as source:
 pixels=source.convert('RGBA')
 for c in text:
  g=glyphs[ord(c)]
  for y in range(g['h']):
   col=0
   while col<g['w']:
    color=pixels.getpixel((g['x']+col,g['y']+y));end=col+1
    while end<g['w'] and pixels.getpixel((g['x']+end,g['y']+y))==color:end+=1
    if color[3]:
     fill='#%02x%02x%02x'%color[:3];opacity='' if color[3]==255 else f' opacity="{color[3]/255:.8f}"'
     parts.append(f'<rect x="{x+g["offset"]+col}" y="{y}" width="{end-col}" height="1" fill="{fill}"{opacity}/>')
    col=end
  x+=g['advance']
height=max(glyphs[ord(c)]['h'] for c in text)
svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{x*2}" height="{height*2}" viewBox="0 0 {x} {height}" shape-rendering="crispEdges">'+''.join(parts)+'</svg>'
out=Path(__file__).resolve().parents[2]/'assets/ui';out.mkdir(exist_ok=True,parents=True)
(out/'fnt-main-title.svg').write_text(svg,encoding='utf-8')
(out/'fnt-main-source.json').write_text(json.dumps({'font':d['name'],'display_name':d['display'],'text':text,'representation':'Visible title pixels only; no embedded atlas','metrics_sha256':hashlib.sha256(a.metrics.read_bytes()).hexdigest(),'atlas_sha256':hashlib.sha256(a.atlas.read_bytes()).hexdigest(),'title_sha256':hashlib.sha256(svg.encode()).hexdigest()},indent=2),encoding='utf-8')
print(hashlib.sha256(svg.encode()).hexdigest())
