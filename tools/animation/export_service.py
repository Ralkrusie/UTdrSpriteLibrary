"""Export implementation shared by the desktop HTTP server and the headless CLI."""
import json
import re
from pathlib import Path

from encoder import encode, encode_png, export_filename
from export_files import file_hashes


def label(value):
    return re.sub(r'[^\w.-]', '_', value)[:70].strip('.') or 'library'


def compact_manifest(manifest):
    """Keep provenance, frame mapping and integrity data; omit repeated encoder diagnostics."""
    options = manifest['options']
    if options.get('original'):
        options = {'format': 'png', 'original': True}
    else:
        options = {k: v for k, v in options.items()
                   if k in ('format', 'scale', 'fps', 'frame_index')}
    records = []
    for record in manifest['records']:
        item = {k: record[k] for k in ('name', 'variant', 'chapters', 'file') if k in record}
        if 'files' in record:
            item['files'] = [{k: f[k] for k in ('file', 'frame') if k in f} for f in record['files']]
        records.append(item)
    return manifest | {
        'package': {k: manifest['package'][k] for k in ('id', 'name', 'game', 'version', 'language')
                    if k in manifest['package']},
        'options': options, 'records': records,
    }


def export_batch(store, entries, options, folder, fingerprint, cancel=lambda: False,
                 progress=lambda done, success, errors, current: None):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    records, failures = [], []
    cancelled = False
    try:
        for package, v in entries:
            if cancel():
                cancelled = True
                break
            progress(len(records) + len(failures), len(records), len(failures), v['name'])
            try:
                if options.get('original'):
                    files = []
                    if not v['frames']:
                        raise ValueError('No bitmap frames')
                    for i, f in enumerate(v['frames']):
                        if cancel():
                            raise InterruptedError('Cancelled')
                        if 'image' not in f:
                            raise ValueError('素材帧不完整')
                        name = export_filename(v, options) + f'_{i:04d}.png'
                        (folder / name).write_bytes(package.read(f['image']))
                        files.append({'file': name, 'frame': i, 'size': [f['width'], f['height']]})
                    record = {'name': v['name'], 'variant': v['id'], 'format': 'png', 'original': True, 'files': files}
                elif options['format'] == 'png':
                    record = encode_png(package, v, folder, options, cancel)
                else:
                    out = folder / (export_filename(v, options) + {'gif': '.gif', 'mov': '.mov', 'apng': '.png'}[options['format']])
                    record = encode(package, v, out, options, cancel) | {'file': out.name}
                records.append(record | {'package_id': package.id, 'chapters': v['chapters']})
            except InterruptedError:
                cancelled = True
                break
            except Exception as error:
                failures.append({'name': v['name'], 'variant': v['id'], 'error': str(error)})
            progress(len(records) + len(failures), len(records), len(failures), v['name'])
    except KeyboardInterrupt:
        cancelled = True
    package = entries[0][0]
    manifest = {'package': store.metadata(package.id) | {'id': package.id},
                'options': options, 'records': records, 'errors': failures,
                'cancelled': cancelled or cancel(), 'signature': fingerprint,
                'file_hashes': file_hashes(folder, records)}
    manifest = compact_manifest(manifest)
    (folder / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return manifest
