"""Compare all catalog data and PNG bytes against the full CLI baseline."""
import argparse
import json
from pathlib import Path
import zipfile


def compare(before, after):
    with zipfile.ZipFile(before) as old, zipfile.ZipFile(after) as new:
        assert json.loads(old.read('catalog.json')) == json.loads(new.read('catalog.json')), 'Catalog differs'
        images = {name for name in old.namelist() if name.startswith('images/') and name.endswith('.png')}
        assert images == {name for name in new.namelist() if name.startswith('images/') and name.endswith('.png')}, 'Image set differs'
        for name in images:
            assert old.read(name) == new.read(name), 'PNG bytes differ: '+name
    return {'catalog_identical': True, 'png_bytes_identical': True, 'images': len(images)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.before, args.after)))
