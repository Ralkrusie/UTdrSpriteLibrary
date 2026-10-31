"""Build the asset-free mobile PWA from current sources."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    names = ['index.html', 'app.js', 'style.css', 'encode.js', 'gif.js',
             'archive.js', 'native.js', 'storage.js', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png']
    for name in names:
        shutil.copy2(HERE / name, args.out / name)
    version = hashlib.sha256(b''.join((HERE / name).read_bytes() for name in names) + (HERE / 'sw.js').read_bytes()).hexdigest()[:16]
    worker = (HERE / 'sw.js').read_text(encoding='utf-8').replace('__VERSION__', version).replace('__FILES__', json.dumps(['./'] + ['./' + name for name in names]))
    (args.out / 'sw.js').write_text(worker, encoding='utf-8')
    (args.out / '.nojekyll').touch()
    print(f'PWA built: {args.out.resolve()} ({sum(p.stat().st_size for p in args.out.iterdir())} bytes)')

if __name__ == '__main__':
    main()
