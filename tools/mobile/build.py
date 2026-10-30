"""Build a self-contained static site; no Python service is required after building."""
import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    for name in ('index.html', 'app.js', 'style.css', 'encode.js', 'gif.js'):
        shutil.copy2(Path(__file__).parent / name, args.out / name)
    data = args.out / 'data'
    data.mkdir()
    catalog = json.loads((ROOT / 'library/catalog.json').read_text(encoding='utf-8'))
    variants = [v for g in catalog['items'] if g['kind'] == 'sprite' for v in g['variants']]
    index = []
    for start in range(0, len(variants), 128):
        shard = str(start // 128)
        group = variants[start:start+128]
        details = {}
        for v in group:
            frames = [f.get('image') for f in v['frames']]
            details[v['id']] = dict(frames=frames)
            index.append(dict(id=v['id'], name=v['name'], chapters=v['chapters'], width=v['width'], height=v['height'], count=len(frames), complete=bool(frames) and all(frames), thumbnail=next((f for f in frames if f), None), shard=shard))
        (data / (shard + '.json')).write_text(json.dumps(details, separators=(',', ':')), encoding='utf-8')
    (data / 'index.json').write_text(json.dumps(index, separators=(',', ':')), encoding='utf-8')
    shutil.copytree(ROOT / 'library/images', args.out / 'images')
    print(f'Built {len(index)} variants: {args.out.resolve()}')

if __name__ == '__main__':
    main()
