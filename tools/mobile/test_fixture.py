"""Generate tiny original test images, never game assets, under releases."""
import io
import json
import zipfile
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[2] / 'releases/mobile-pwa-test'
root.mkdir(parents=True, exist_ok=True)
frames = {}
for i in range(2):
    image = Image.new('RGBA', (9, 7), (255, 50 * i, 0, 0))
    image.putpixel((i, 1), (0, 255, 0, 255))
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    frames[f'images/frame{i}.png'] = buffer.getvalue()
meta = dict(format='UTdrSpriteLibrary', schema=1, game='DR', name='测试素材包', version='1', language='测试', sources=[])
variant = dict(id='a' * 64, name='sample', chapters=[2, 5], width=9, height=7,
               frames=[dict(image=p, width=9, height=7) for p in frames])
files = {'manifest.json': json.dumps(meta).encode(),
         'catalog.json': json.dumps({'items': [dict(kind='sprite', variants=[variant])]}).encode(), **frames}
for name, compression in [('sample', zipfile.ZIP_DEFLATED), ('stored', zipfile.ZIP_STORED), ('bad', zipfile.ZIP_DEFLATED)]:
    with zipfile.ZipFile(root / (name + '.zip'), 'w', compression=compression) as archive:
        for path, data in files.items():
            archive.writestr(path, data)
        if name == 'bad':
            archive.writestr('../evil.png', b'bad')
