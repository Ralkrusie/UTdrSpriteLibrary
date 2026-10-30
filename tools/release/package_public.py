"""Create local release candidates from an untouched build; never publish anything."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
VERSION = '0.3.0-rc1'
ROOT_FILES = ('README.md', 'LICENSE', 'ASSET_NOTICE.md', 'THIRD_PARTY_NOTICES.md',
              'RELEASE_PREPARATION.md', '.gitignore', 'requirements-animation.txt',
              'requirements-build.txt', 'start-animation.cmd')
DOCS = ('REQUIREMENTS.md', 'PACKAGE_FORMAT.md', 'BUILD.md')
IGNORED = {'__pycache__', 'bin', 'obj', '.git', 'node_modules'}


def sha256(file):
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source_files():
    files = [ROOT / name for name in ROOT_FILES]
    files += [ROOT / 'docs' / name for name in DOCS]
    for folder in ('tools', 'assets', 'licenses'):
        files += [p for p in (ROOT / folder).rglob('*') if p.is_file()
                  and not IGNORED.intersection(p.relative_to(ROOT).parts)
                  and p.suffix not in {'.pyc', '.log'}]
    return sorted(files)


def zip_files(destination, entries):
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file, name in entries:
            archive.write(file, name)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP integrity failure: ' + str(destination))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    runtime, out = args.runtime.resolve(), args.out.resolve()
    if out == runtime or out.is_relative_to(runtime):
        raise ValueError('Output must be outside the runtime')
    for name in ('SpriteLibrary.exe', 'LICENSE', 'Electron-LICENSE', 'LICENSES.chromium.html',
                 'THIRD_PARTY_NOTICES.md', 'ASSET_NOTICE.md', 'RELEASE_PREPARATION.md'):
        if not (runtime / name).is_file():
            raise ValueError('Runtime missing ' + name)
    runtime_files = sorted(p for p in runtime.rglob('*') if p.is_file())
    for file in runtime.rglob('*'):
        relative = file.relative_to(runtime)
        if file.is_symlink() or {'data', 'library', '.git', '__pycache__'}.intersection(relative.parts):
            raise ValueError('Runtime is not pristine: ' + str(relative))
        standard_library = relative.as_posix() == 'backend/_internal/base_library.zip'
        if file.suffix.lower() in {'.zip', '.sqlite', '.sqlite3', '.db', '.win', '.log'} and not standard_library:
            raise ValueError('Unexpected package/user data: ' + str(relative))
    # Require the notices and app entry points to match this source checkout.
    for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md', 'ASSET_NOTICE.md', 'RELEASE_PREPARATION.md'):
        if sha256(ROOT / name) != sha256(runtime / name):
            raise ValueError('Stale runtime notice: ' + name)
    for name in ('main.cjs', 'preload.cjs', 'package.json'):
        if sha256(ROOT / 'tools/desktop' / name) != sha256(runtime / 'resources/app' / name):
            raise ValueError('Stale desktop source: ' + name)
    upstream = ROOT / 'vendor/release-sources'
    records = json.loads((upstream / 'manifest.json').read_text(encoding='utf-8'))
    for record in records:
        if 'error' in record or Path(record['file']).name != record['file']:
            raise ValueError('Incomplete upstream download manifest')
        if sha256(upstream / record['file']) != record['sha256']:
            raise ValueError('Upstream source checksum mismatch')
    files = source_files()
    if any(not file.is_file() for file in files):
        raise ValueError('Missing source file')
    out.mkdir(parents=True, exist_ok=False)
    name = 'UTdrSpriteLibrary-' + VERSION
    zip_files(out / (name + '-source.zip'), [(p, name + '/' + p.relative_to(ROOT).as_posix()) for p in files])
    zip_files(out / (name + '-windows-x64-candidate.zip'),
              [(p, name + '/' + p.relative_to(runtime).as_posix()) for p in runtime_files])
    sources = out / 'upstream-sources'
    sources.mkdir()
    for record in records:
        shutil.copy2(upstream / record['file'], sources / record['file'])
    shutil.copy2(upstream / 'manifest.json', sources / 'manifest.json')
    if (upstream / 'FFmpeg-build.txt').is_file():
        shutil.copy2(upstream / 'FFmpeg-build.txt', sources / 'FFmpeg-build.txt')
    for doc in ('RELEASE_PREPARATION.md', 'THIRD_PARTY_NOTICES.md', 'ASSET_NOTICE.md', 'LICENSE'):
        shutil.copy2(ROOT / doc, out / doc)
    report = {'version': VERSION, 'binary_distribution_cleared': False,
              'status': 'Local candidate; see RELEASE_PREPARATION.md for unresolved corresponding-source checks',
              'contains_game_packages': False, 'contains_personal_data': False,
              'runtime_bytes': sum(p.stat().st_size for p in runtime_files),
              'source_files': len(files), 'upstream_sources': records,
              'source_sha256': {p.relative_to(ROOT).as_posix(): sha256(p) for p in files},
              'runtime_sha256': {p.relative_to(runtime).as_posix(): sha256(p) for p in runtime_files}}
    (out / 'release-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    checksums = [f'{sha256(p)}  {p.relative_to(out).as_posix()}' for p in sorted(out.rglob('*')) if p.is_file()]
    (out / 'SHA256SUMS.txt').write_text('\n'.join(checksums) + '\n', encoding='utf-8')
    print(json.dumps({'directory': str(out), 'runtime_MiB': round(report['runtime_bytes']/1048576, 2),
                      'archives': {p.name: round(p.stat().st_size/1048576, 2) for p in out.glob('*.zip')}}, indent=2))


if __name__ == '__main__':
    main()
