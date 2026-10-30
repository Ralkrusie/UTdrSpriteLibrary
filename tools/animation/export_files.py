"""Readable, collision-safe names and checks against intact completed exports."""
import hashlib
import json
from pathlib import Path
from encoder import filename, settings
from library import sha


def named_entries(entries):
    names, used = {}, set()
    for package, variant in sorted(entries, key=lambda entry: entry[1]['id']):
        # Only our allocator may assign an export name; ignore any extra ZIP metadata.
        base = filename({'name': variant['name'], 'chapters': variant['chapters']})
        name, number = base, 1
        while name.casefold() in used:
            number += 1
            name = f'{base}_{number}'
        used.add(name.casefold())
        names[variant['id']] = name
    return [(p, v | {'export_name': names[v['id']]}) for p, v in entries]


def signature(entries, options):
    scale, fps, fmt, _ = settings({}, options)
    original = bool(options.get('original'))
    normalized = {'format': fmt, 'scale': scale}
    if original:
        normalized = {'original': True}
    elif fmt == 'png':
        normalized['frame_index'] = options.get('frame_index')
    else:
        normalized['fps'] = fps
    items = []
    for package, v in entries:
        frames = v['frames']
        index = normalized.get('frame_index')
        if index is not None:
            if type(index) is not int or not 0 <= index < len(frames):
                raise ValueError('Invalid frame index')
            frames = [frames[index]]
        hashes = [hashlib.sha256(package.read(f['image'])).hexdigest() if original or not f.get('pixel_sha256')
                  else f['pixel_sha256'] for f in frames if 'image' in f]
        items.append([filename(v), hashes])
    value = {'schema': 1, 'options': normalized, 'items': sorted(items)}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def file_hashes(folder, records):
    names = [item['file'] for record in records for item in record.get('files', [record])]
    return {name: sha(folder / name) for name in names}


def find_duplicate(category, fingerprint):
    # Manifests are already part of each export. No new export-history database.
    for bucket in ('normal', 'drag', 'export'):
        for path in (category / bucket).glob('*/manifest.json'):
            try:
                manifest = json.loads(path.read_text(encoding='utf-8'))
                hashes = manifest.get('file_hashes', {})
                if manifest.get('signature') != fingerprint or not hashes or manifest.get('errors') or manifest.get('cancelled'):
                    continue
                if all(Path(name).name == name and sha(path.parent / name) == digest for name, digest in hashes.items()):
                    return {'folder': str(path.parent), 'count': len(hashes)}
            except (OSError, ValueError, TypeError):
                continue
    return None
