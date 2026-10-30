"""Copy the user-selected, unmodified DR heart frame from an explicit asset package."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HEART_SHA256 = 'cf2e8376574f1ccd958063bafd59267a2829e8790783a9d5a029cdb348a2c377'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=Path, required=True)
    args = parser.parse_args()
    with zipfile.ZipFile(args.package) as archive:
        if json.loads(archive.read('manifest.json'))['game'] != 'DR':
            raise ValueError('A DELTARUNE package is required')
        catalog = json.loads(archive.read('catalog.json'))
        variant = next(v for item in catalog['items'] for v in item.get('variants', [])
                       if v['name'] == 'spr_dodgeheart')
        frame = variant['frames'][0]
        content = archive.read(frame['image'])
    if hashlib.sha256(content).hexdigest() != HEART_SHA256:
        raise ValueError('The selected heart differs from the verified UI frame')
    output = ROOT / 'assets/ui'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'spr_dodgeheart_0.png').write_bytes(content)
    (output / 'source.json').write_text(json.dumps({
        'resource': variant['name'], 'frame': 0, 'chapters': variant['chapters'],
        'dimensions': [frame['width'], frame['height']],
        'package_sha256': hashlib.sha256(args.package.read_bytes()).hexdigest(),
        'member': frame['image'], 'file_sha256': HEART_SHA256,
    }, indent=2), encoding='utf-8')
    print(output / 'spr_dodgeheart_0.png')


if __name__ == '__main__':
    main()
