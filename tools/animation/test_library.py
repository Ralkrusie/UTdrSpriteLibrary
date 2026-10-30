"""Integration coverage for real ZIP imports, version isolation and exports."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from PIL import Image
from import_game import discover
from library import Package, make_package, sha

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', type=Path)
    args = parser.parse_args()
    work = Path(tempfile.mkdtemp(prefix='desktop-integration-', dir=ROOT / 'releases'))
    source = work / 'fixture'
    (source / 'images').mkdir(parents=True)
    frames = []
    for n in range(3):
        name = f'images/{n}.png'
        im = Image.new('RGBA', (7, 9), (0, 0, 0, 0))
        im.putpixel((n + 1, 2), (13, 79, 203, 83 + n * 60))
        im.save(source / name)
        frames.append({'image': name, 'width': 7, 'height': 9})
    vid = hashlib.sha256(b'fixture').hexdigest()
    variant = {'id': vid, 'name': 'spr_same_name', 'chapters': [2, 5], 'width': 7, 'height': 9, 'speed': 1, 'speed_type': 'FramesPerGameFrame', 'frames': frames}
    (source / 'catalog.json').write_text(json.dumps({'schema': 1, 'items': [{'kind': 'sprite', 'variants': [variant]}]}), encoding='utf-8')
    metadata = {'game': 'DR', 'name': 'Test DR', 'version': '1', 'language': 'EN', 'sources': [{'file': 'fixture/data.win', 'sha256': 'a' * 64}]}
    zip1 = make_package(source, work / 'one.zip', metadata)
    zip2 = make_package(source, work / 'two.zip', metadata | {'version': '2', 'language': 'ZH'})
    original_digest = sha(zip1)
    with zipfile.ZipFile(zip1) as src, zipfile.ZipFile(work/'rezipped.zip', 'w', compression=zipfile.ZIP_STORED) as dest:
        for name in reversed(src.namelist()):dest.writestr(name, src.read(name))
    # Path traversal and duplicate paths must never enter managed storage.
    bad = work / 'bad.zip'
    with zipfile.ZipFile(zip1) as src, zipfile.ZipFile(bad, 'w') as dest:
        for name in src.namelist():
            dest.writestr(name, src.read(name))
        dest.writestr('../outside.png', b'x')
    try:
        Package(bad, verify=True)
        raise AssertionError('Unsafe ZIP accepted')
    except ValueError:
        pass
    try:
        Package(zip1, verify=True, cancel=lambda:True)
        raise AssertionError('Cancelled validation continued')
    except InterruptedError:
        pass
    chapters = work / 'game'
    for chapter in (2, 5, 8):
        p = chapters / f'chapter{chapter}_windows'
        p.mkdir(parents=True)
        (p / 'data.win').write_bytes(b'fixture')
    assert [ch for ch, _ in discover(chapters, 'DR')] == [2, 5, 8]
    data = work / 'data'
    ready = work / 'ready.json'
    process = None
    base = ''
    def start():
        nonlocal process, base
        ready.unlink(missing_ok=True)
        command = [str(args.backend.resolve())] if args.backend else [sys.executable, str(ROOT / 'tools/animation/server.py')]
        env = dict(os.environ)
        if args.backend:
            env['PATH'] = str(Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32') if os.name == 'nt' else '/nonexistent'
            env.pop('PYTHONPATH', None)
            env.pop('PYTHONHOME', None)
        process = subprocess.Popen(command + ['--port', '0', '--data', str(data), '--ready-file', str(ready), '--parent-pid', str(os.getpid())], env=env, stdout=subprocess.DEVNULL, stderr=(work / 'server.log').open('ab'), creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        for _ in range(300):
            if ready.exists():
                r = json.loads(ready.read_text())
                assert 'url' in r, r
                base = r['url'].rstrip('/')
                return
            assert process.poll() is None, (work / 'server.log').read_text(errors='replace')
            time.sleep(.1)
        raise AssertionError('Backend startup timeout')
    def stop():
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=15)
    def api(path, body=None):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    def job(result):
        for _ in range(600):
            status = api('/api/job/' + result['id'])
            if status['state'] not in ('queued', 'running'):
                assert status['state'] == 'done' and not status['errors'], status
                return status
            time.sleep(.1)
        raise AssertionError('Job timeout')
    try:
        start()
        assert api('/api/settings')['presets'] == []
        assert api('/api/settings')['card_width'] == 230
        assert api('/api/settings', {'card_width': 360})['card_width'] == 360
        for width in (179, 361, 230.5, True, '230', None):
            try:
                api('/api/settings', {'card_width': width})
                raise AssertionError('Invalid card size accepted')
            except urllib.error.HTTPError as error:
                assert error.code == 400
        assert api('/api/libraries')['packages'] == []
        p1 = job(api('/api/library/import', {'path': str(zip1)}))['package_id']
        p2 = job(api('/api/library/import', {'path': str(zip2)}))['package_id']
        assert p1 != p2
        assert job(api('/api/library/import', {'path': str(zip1)}))['package_id'] == p1
        assert job(api('/api/library/import', {'path': str(work/'rezipped.zip')}))['package_id'] == p1
        assert len(api('/api/libraries')['packages']) == 2
        try:
            api('/api/export', {'ids': [], 'options': {}})
            raise AssertionError('Empty selection accepted')
        except urllib.error.HTTPError as error:
            assert error.code == 400
        key = p1 + ':' + vid
        api('/api/favorite', {'id': key, 'enabled': True})
        assert api('/api/catalog?package=' + p1)[0]['favorite']
        assert not api('/api/catalog?package=' + p2)[0]['favorite']
        api('/api/favorite', {'ids': [key, p2+':'+vid], 'enabled': True})
        assert api('/api/catalog?package='+p2)[0]['favorite']
        api('/api/favorite', {'ids': [p2+':'+vid], 'enabled': False})
        api('/api/library/rename', {'id': p1, 'name': 'Renamed DR'})
        api('/api/library/metadata', {'id': p1, 'name': 'Renamed DR', 'version': '2.0', 'language': '中文补丁'})
        assert sha(data/'packages'/(p1+'.zip')) == original_digest
        assert api('/api/catalog?package='+p1)[0]['favorite']
        package_info = next(p for p in api('/api/libraries')['packages'] if p['id']==p1)
        assert package_info['version']=='2.0' and package_info['language']=='中文补丁'
        target = work/'custom-packages'/'我的素材.zip'
        api('/api/library/save', {'id':p1, 'path':str(target)})
        with zipfile.ZipFile(target) as z:
            saved=json.loads(z.read('manifest.json'))
            assert saved['name']=='Renamed DR' and saved['version']=='2.0' and saved['language']=='中文补丁'
            assert z.read('images/0.png')==(source/'images/0.png').read_bytes()
        exported_hash=sha(target)
        try:
            api('/api/library/save', {'id':p1, 'path':str(target)})
            raise AssertionError('Existing package overwritten')
        except urllib.error.HTTPError as error:assert error.code==400
        assert sha(target)==exported_hash
        preset = {'id': 'user', 'name': 'Own preset', 'format': 'mov', 'fps': 3.75, 'scale': 2.5}
        api('/api/settings', {'presets': [preset]})
        out = work / 'exports'
        outputs = []
        for fmt in ('png', 'gif', 'apng', 'mov', 'original'):
            opts = {'format': 'png' if fmt == 'original' else fmt, 'scale': 5, 'fps': 3.75}
            if fmt == 'original':
                opts.update(original=True, open=False)
            status = job(api('/api/export', {'ids': [key], 'options': opts, 'output_dir': str(out)}))
            folder = Path(status['folder'])
            outputs.append(folder)
            assert folder.parent.name=='normal'
            manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
            assert manifest['package']['id'] == p1 and manifest['package']['name'] == 'Renamed DR'
            record = manifest['records'][0]
            names = [f['file'] for f in record.get('files', [record])]
            assert all(vid[:12] not in name for name in names)
            suffix = '_original_1x_' if fmt == 'original' else '_5x_' if fmt == 'png' else '_3.75fps_5x.'
            assert all(suffix in name for name in names), names
            repeat = {'ids': [key], 'options': opts, 'output_dir': str(out)}
            assert api('/api/export', repeat)['duplicate']['folder'] == str(folder)
            if fmt == 'png':
                assert 'duplicate' in api('/api/export', repeat | {'options': opts | {'fps': 7.5}})
                allowed = job(api('/api/export', repeat | {'allow_duplicate': True}))
                assert allowed['folder'] != str(folder)
                # Missing or modified files must not trigger a stale duplicate prompt.
                (Path(allowed['folder']) / names[0]).write_bytes(b'changed')
                (folder / names[0]).rename(folder / ('saved-' + names[0]))
                recovered = job(api('/api/export', repeat))
                assert recovered['success'] == 1
                (folder / ('saved-' + names[0])).rename(folder / names[0])
            if fmt in ('png', 'original'):
                assert len(record['files']) == 3
                for n, entry in enumerate(record['files']):
                    file = folder / entry['file']
                    if fmt == 'original':
                        assert file.read_bytes() == (source / f'images/{n}.png').read_bytes()
                    with Image.open(file) as im:
                        assert im.size == ((7, 9) if fmt == 'original' else (35, 45))
            else:
                assert (folder / record['file']).stat().st_size > 0
        default_package=Path(api('/api/library/export-path',{'id':p1})['file'])
        for scale,dimensions in ((.25,(2,2)),(2.5,(18,22)),(20,(140,180))):
            status=job(api('/api/export', {'ids':[key], 'options':{'format':'png','scale':scale}, 'output_dir':str(out)}))
            folder=Path(status['folder'])
            manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
            for entry in manifest['records'][0]['files']:
                with Image.open(folder/entry['file']) as im:assert im.size==dimensions
        assert default_package.parent==outputs[0].parent.parent
        assert Path(api('/api/settings')['output_dir'])==out
        assert len(set(outputs)) == len(outputs)
        assert sha(zip1) == original_digest
        assert not list((data / 'packages').rglob('*.png'))
        stop()
        start()
        assert api('/api/settings')['presets'] == [preset]
        assert api('/api/settings')['card_width'] == 360
        assert next(p for p in api('/api/libraries')['packages'] if p['id']==p1)['version']=='2.0'
        assert api('/api/catalog?package=' + p1)[0]['favorite']
        api('/api/library/delete', {'id': p1})
        assert all(folder.exists() for folder in outputs)
        assert zip1.exists()
        assert len(api('/api/libraries')['packages']) == 1
        job(api('/api/library/import', {'path': str(zip1)}))
        assert api('/api/catalog?package=' + p1)[0]['favorite']
        print('PASS: ZIP validation, arbitrary chapters, multi-version isolation, scoped favorites, persistent presets, all export formats, original bytes, restart, safe deletion/reimport')
        print('Test artifacts:', work)
    finally:
        stop()


if __name__ == '__main__':
    main()
