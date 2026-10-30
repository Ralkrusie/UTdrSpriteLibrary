"""Subprocess contract and real media tests; all fixtures stay under releases/."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from PIL import Image
from library import make_package, sha

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cli', type=Path, help='Frozen console executable; omit to test source')
    args = p.parse_args()
    work = Path(tempfile.mkdtemp(prefix='cli-integration-', dir=ROOT / 'releases'))
    data = work / 'data with spaces 中文'
    command = [str(args.cli.resolve())] if args.cli else [sys.executable, str(ROOT / 'tools/animation/cli.py')]
    env = dict(os.environ, UTDR_DATA_DIR=str(data), PYTHONIOENCODING='utf-8')
    if args.cli:
        env['PATH'] = str(Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32') if os.name == 'nt' else '/nonexistent'
        env.pop('PYTHONPATH', None)
        env.pop('PYTHONHOME', None)

    def call(*parts, code=0, stdin=None, extra_env=None):
        result = subprocess.run(command + list(parts) + ['--json'], input=stdin, text=True, encoding='utf-8',
                                capture_output=True, timeout=90, env=env | (extra_env or {}))
        assert result.returncode == code, (parts, result.returncode, result.stdout, result.stderr)
        assert len(result.stdout.splitlines()) == 1, result.stdout
        value = json.loads(result.stdout)
        assert value['schema_version'] == 1 and value['ok'] == (code == 0), value
        return value['data'] if code == 0 else value['error']

    schema = call('schema')
    assert 'export' in schema['commands'] and schema['limits']['scale'] == [.25, 20]
    assert call('paths')['data'] == str(data)
    assert not data.exists(), 'Discovery should not create data'
    assert call('version')['cli_schema'] == 1
    assert call('no-command', code=2)['code'] == 'invalid_argument'
    assert call('export', code=2)['code'] == 'invalid_argument'
    assert call('paths', extra_env={'UTDR_DATA_DIR': 'relative'}, code=2)['code'] == 'invalid_argument'
    separate = work / 'separate'
    assert call('--data', str(separate), 'paths')['data'] == str(separate)
    assert call('paths', '--data', str(separate))['data'] == str(separate)
    assert call('packages', '--data', str(separate), 'list')['packages'] == []
    assert call('packages', 'list')['packages'] == []
    assert call('presets', 'list')['presets'] == []

    source = work / 'fixture'
    (source / 'images').mkdir(parents=True)
    frames = []
    for i in range(3):
        name = f'images/{i}.png'
        with Image.new('RGBA', (7, 9), (0, 0, 0, 0)) as im:
            im.putpixel((i + 1, 2), (13, 79, 203, 83 + i * 60))
            im.save(source / name)
        frames.append({'image': name, 'width': 7, 'height': 9})
    variants = [{'id': hashlib.sha256(name.encode()).hexdigest(), 'name': name, 'chapters': chapters,
                 'width': 7, 'height': 9, 'frames': refs, 'speed': 1, 'speed_type': 'FramesPerGameFrame'}
                for name, chapters, refs in [('spr_中文_hero', [2, 5], frames), ('spr_static', [1], frames[:1]),
                                             ('spr_other', [2], frames)]]
    (source / 'catalog.json').write_text(json.dumps({'schema': 1, 'items': [{'kind': 'sprite', 'variants': variants}]}), encoding='utf-8')
    package = make_package(source, work / '素材包.zip', {'game': 'DR', 'name': '测试包', 'version': '1', 'language': '中文', 'sources': []})
    before = sha(package)
    imported = call('packages', 'import', str(package))
    pid = imported['package']['id']
    assert not imported['duplicate'] and call('packages', 'import', str(package))['duplicate']
    scope = ['--package', pid]
    keys = [pid + ':' + v['id'] for v in variants]
    assert call('packages', 'info', *scope)['count'] == 3
    assert call('sprites', 'list', *scope, '--limit', '1')['next_offset'] == 1
    assert call('sprites', 'list', *scope, '--offset', '3')['items'] == []
    assert call('sprites', 'list', *scope, '--query', 'HERO')['total'] == 1
    assert call('sprites', 'list', *scope, '--chapter', '2', '--multi-frame')['total'] == 2
    assert call('sprites', 'info', *scope, '--id', variants[0]['id'])['frames'][0]['image'] == 'images/0.png'
    call('sprites', 'info', *scope, '--id', 'missing', code=3)
    call('sprites', 'list', *scope, '--limit', '0', code=2)
    call('favorites', 'add', *scope, '--id', keys[0], '--id', 'missing', code=3)
    assert call('sprites', 'list', *scope, '--favorites')['total'] == 0
    call('favorites', 'add', *scope, '--all', '--chapter', '2')
    assert call('sprites', 'list', *scope, '--favorites')['total'] == 2
    call('favorites', 'remove', *scope, '--ids-file', '-', stdin=json.dumps([keys[2]]))
    assert call('sprites', 'list', *scope, '--favorites')['total'] == 1
    call('favorites', 'add', *scope, '--ids-file', '-', stdin='{}', code=2)
    call('favorites', 'add', *scope, '--id', keys[0], '--query', 'hero', code=2)

    preset = call('presets', 'save', '--name', '半倍', '--format', 'png', '--scale', '.5')
    assert call('presets', 'list')['presets'][0]['id'] == preset['id']
    call('presets', 'save', '--id', preset['id'], '--name', '两倍', '--format', 'png', '--scale', '2')
    renamed = call('presets', 'save', '--id', preset['id'], '--name', '只改名')
    assert renamed['format'] == 'png' and renamed['scale'] == 2
    base = ['export', *scope, '--id', keys[0]]
    output = work / 'output with spaces'
    plan = call(*base, '--preset', preset['id'], '--dry-run', '--output', str(output))
    assert plan['options']['scale'] == 2 and not output.exists()
    call(*base, '--preset', preset['id'], '--scale', '3', code=2)
    for scale in ('0', '20.1', 'nan', 'inf'):
        call(*base, '--scale', scale, code=2)
    call(*base, '--fps', '0', code=2)
    call(*base, '--frame', '0', code=2)
    call(*base, '--format', 'png', '--frame', '3', code=2)
    call(*base, '--original', '--scale', '2', code=2)
    call(*base, '--output', str(data / 'packages'), code=2)
    call('export', *scope, '--id', keys[1], '--format', 'gif', code=2)
    assert not (data / 'exports').exists(), 'Invalid requests must not create exports'

    results = []
    for fmt in ('png', 'gif', 'apng', 'mov'):
        result = call(*base, '--format', fmt, '--scale', '2', '--fps', '6.3', '--output', str(output))
        results.append(result)
        assert result['success'] == 1 and result['failed'] == 0
        assert all(Path(f).is_file() for f in result['files'])
        manifest = json.loads(Path(result['manifest']).read_text(encoding='utf-8'))
        assert manifest['options']['scale'] == 2 and not manifest['cancelled']
        if fmt != 'mov':
            with Image.open(result['files'][0]) as image:
                assert image.size == (14, 18)
        duplicate = call(*base, '--format', fmt, '--scale', '2', '--fps', '6.3', '--output', str(output), code=4)
        assert duplicate['details']['folder'] == result['folder']
    repeat = call(*base, '--format', 'png', '--scale', '2', '--output', str(output), '--allow-duplicate')
    assert repeat['folder'] != results[0]['folder']
    original = call(*base, '--original', '--output', str(output))
    assert [Path(f).read_bytes() for f in original['files']] == [(source / f['image']).read_bytes() for f in frames]
    single = call(*base, '--format', 'png', '--frame', '1', '--scale', '.25', '--output', str(output))
    assert len(single['files']) == 1
    with Image.open(single['files'][0]) as image:
        assert image.size == (2, 2)
    # Missing output invalidates duplicate detection; unrelated exports stay intact.
    Path(single['files'][0]).unlink()
    call(*base, '--format', 'png', '--frame', '1', '--scale', '.25', '--output', str(output))
    idsfile = work / 'ids.json'
    idsfile.write_text(json.dumps([keys[0], keys[2], keys[0]]), encoding='utf-8-sig')
    assert call('export', *scope, '--ids-file', str(idsfile), '--dry-run')['count'] == 2

    call('packages', 'edit', *scope, '--name', '新名称', '--version', '2', '--language', '')
    copy = work / 'edited.zip'
    call('packages', 'export', *scope, '--output', str(copy))
    with zipfile.ZipFile(copy) as z:
        metadata = json.loads(z.read('manifest.json'))
        assert metadata['name'] == '新名称' and metadata['language'] == ''
    copy_hash = sha(copy)
    call('packages', 'export', *scope, '--output', str(copy), code=4)
    assert sha(copy) == copy_hash and sha(package) == before
    bad = work / 'bad.zip'
    with zipfile.ZipFile(bad, 'w') as z:
        z.writestr('../escape.png', b'bad')
    call('packages', 'import', str(bad), code=2)
    assert len(call('packages', 'list')['packages']) == 1
    assert not list((data / 'packages').glob('.import-*'))
    game = work / 'game'
    call('packages', 'create', '--game', str(game), '--kind', 'DR', '--name', 'test', '--data', str(game / 'tool-data'), code=2)
    assert not game.exists()
    call('presets', 'remove', '--id', preset['id'], code=4)
    call('presets', 'remove', '--id', preset['id'], '--yes')
    call('packages', 'remove', *scope, code=4)
    call('packages', 'remove', *scope, '--yes')
    assert not call('packages', 'list')['packages']
    assert Path(original['files'][0]).exists() and (data / 'personal/settings.sqlite3').is_file()
    # JSON flag at the beginning, with stdout still a single structured document.
    process = subprocess.run(command + ['--json', 'version'], capture_output=True, text=True, encoding='utf-8', env=env)
    assert process.returncode == 0 and json.loads(process.stdout)['ok']
    help_result = subprocess.run(command + ['export', '--help'], capture_output=True, text=True, encoding='utf-8', env=env)
    assert help_result.returncode == 0 and '--dry-run' in help_result.stdout
    if not args.cli:
        check_failure_and_cancel(work, package)
        check_game_creation(work, source)
    print('CLI integration passed: ' + str(work))


def check_failure_and_cancel(work, package):
    """Exercise failures after preflight, which must preserve earlier completed files."""
    from contextlib import redirect_stdout
    from io import StringIO
    from unittest.mock import patch
    import cli
    import export_service
    from library import LibraryStore
    from preferences import Preferences
    data = work / 'failure-data'
    prefs = Preferences(data)
    store = LibraryStore(data / 'packages', prefs)
    pid, _ = store.import_zip(package)
    store.close()
    original_encode = export_service.encode_png
    calls = 0

    def failing_encode(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError('Simulated encoder failure')
        return original_encode(*args, **kwargs)

    base = ['--data', str(data), 'export', '--package', pid, '--all', '--format', 'png', '--json']
    with patch.object(export_service, 'encode_png', side_effect=failing_encode), redirect_stdout(StringIO()) as stdout:
        code = cli.main(base)
    value = json.loads(stdout.getvalue())
    assert code == 6 and value['error']['code'] == 'export_failed'
    result = value['error']['details']
    assert result['success'] == 2 and result['failed'] == 1
    assert all(Path(f).exists() for f in result['files'])
    for interruption in (InterruptedError, KeyboardInterrupt):
        with patch.object(export_service, 'encode_png', side_effect=interruption), redirect_stdout(StringIO()) as stdout:
            code = cli.main(base)
        value = json.loads(stdout.getvalue())
        assert code == 130 and value['error']['code'] == 'cancelled'
        manifest = json.loads(Path(value['error']['details']['manifest']).read_text(encoding='utf-8'))
        assert manifest['cancelled'] and not manifest['file_hashes']


def check_game_creation(work, source):
    # Extraction itself already has a Windows-only implementation. Test CLI wiring
    # with generated frames, without reading the user's game or requiring it in CI.
    from contextlib import redirect_stdout
    from io import StringIO
    from unittest.mock import patch
    import shutil
    import cli
    game = work / 'fake-game'
    game.mkdir()
    game_file = game / 'data.win'
    game_file.write_bytes(b'unchanged input')
    tool = work / 'fake-extractor.exe'
    tool.write_bytes(b'not executed')

    def extracted(game_path, extractor, out, kind, version, progress):
        assert game_path == game and extractor == tool and kind == 'UT' and version == 'test'
        shutil.copytree(source, out)
        return {'inputs': {str(game_file): sha(game_file)}, 'umt_sha256': sha(tool)}

    with patch.object(cli.sys, 'platform', 'win32'), patch.object(cli, 'extract', side_effect=extracted), redirect_stdout(StringIO()) as stdout:
        code = cli.main(['--data', str(work / 'game-data'), 'packages', 'create', '--game', str(game),
                         '--kind', 'UT', '--name', '合成游戏', '--version', 'test', '--extractor', str(tool), '--json'])
    assert code == 0
    assert json.loads(stdout.getvalue())['data']['package']['sources'][0]['sha256'] == sha(game_file)
    assert game_file.read_bytes() == b'unchanged input'
    assert not list((work / 'game-data/cache').iterdir())


if __name__ == '__main__':
    main()
