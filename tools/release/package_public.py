"""Create local release candidates from an untouched build; never publish anything."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
VERSION = '0.3.0-rc2'
ROOT_FILES = ('README.md', 'LICENSE', 'ASSET_NOTICE.md', 'THIRD_PARTY_NOTICES.md',
              '.gitignore', 'requirements-animation.txt',
              'requirements-build.txt', 'start-animation.cmd')
DOCS = ('REQUIREMENTS.md', 'PACKAGE_FORMAT.md', 'BUILD.md', 'NATIVE_SOURCES.md')
IGNORED = {'__pycache__', 'bin', 'obj', '.git', 'node_modules'}
BUILD_RECORDS = {'packaging-profile.json', 'build-profile.json',
                 'upstream-source-build.json', 'FFmpeg-build-profile.json',
                 'Magick.Native-provenance.json'}


def sha256(file):
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source_files():
    files = [ROOT / name for name in ROOT_FILES]
    files += [ROOT / 'docs' / name for name in DOCS]
    for folder in ('tools', 'assets', 'licenses'):
        files += [p for p in (ROOT / folder).rglob('*') if p.is_file()
                  and not IGNORED.intersection(p.relative_to(ROOT).parts)
                  and p.suffix not in {'.pyc', '.log'}
                  and p.name not in BUILD_RECORDS]
    return sorted(files)


def zip_files(destination, entries, compression=zipfile.ZIP_DEFLATED):
    with zipfile.ZipFile(destination, 'w', compression, compresslevel=9) as archive:
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
                 'THIRD_PARTY_NOTICES.md', 'ASSET_NOTICE.md'):
        if not (runtime / name).is_file():
            raise ValueError('Runtime missing ' + name)
    runtime_files = sorted(p for p in runtime.rglob('*')
                           if p.is_file() and p.name not in BUILD_RECORDS)
    for file in runtime.rglob('*'):
        relative = file.relative_to(runtime)
        if file.is_symlink() or {'data', 'library', '.git', '__pycache__'}.intersection(relative.parts):
            raise ValueError('Runtime is not pristine: ' + str(relative))
        standard_library = relative.as_posix() == 'backend/_internal/base_library.zip'
        if file.suffix.lower() in {'.zip', '.sqlite', '.sqlite3', '.db', '.win', '.log'} and not standard_library:
            raise ValueError('Unexpected package/user data: ' + str(relative))
    # Require the notices and app entry points to match this source checkout.
    for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md', 'ASSET_NOTICE.md'):
        if sha256(ROOT / name) != sha256(runtime / name):
            raise ValueError('Stale runtime notice: ' + name)
    for name in ('main.cjs', 'preload.cjs', 'package.json'):
        if sha256(ROOT / 'tools/desktop' / name) != sha256(runtime / 'resources/app' / name):
            raise ValueError('Stale desktop source: ' + name)
    for name in ('BUILD.md', 'NATIVE_SOURCES.md'):
        if sha256(ROOT/'docs'/name) != sha256(runtime/'docs'/name):
            raise ValueError('Stale runtime build documentation: '+name)
    upstream = ROOT / 'vendor/release-sources'
    records = json.loads((upstream / 'manifest.json').read_text(encoding='utf-8'))
    if len({record['file'] for record in records}) != 48:
        raise ValueError('Incomplete fixed upstream source set')
    for record in records:
        if 'error' in record or Path(record['file']).name != record['file']:
            raise ValueError('Incomplete upstream download manifest')
        if sha256(upstream / record['file']) != record['sha256']:
            raise ValueError('Upstream source checksum mismatch')
    sources_by_name = {r['file']: r['sha256'] for r in records}
    ffmpeg = json.loads((runtime/'backend/licenses/FFmpeg-build-profile.json').read_text())
    if (sha256(runtime/'backend/_internal/ffmpeg.exe') != ffmpeg['ffmpeg_sha256']
        or sources_by_name.get(ffmpeg['source_archive']) != ffmpeg['source_sha256']
        or sha256(ROOT/'tools/ffmpeg/build.py') != ffmpeg['build_script_sha256']):
        raise ValueError('FFmpeg does not match the source/build recipe')
    umt = json.loads((runtime/'backend/extractor/upstream-source-build.json').read_text())
    if sha256(ROOT/'tools/extractor/build_upstream.py') != umt['build_script_sha256']:
        raise ValueError('Upstream extractor source build recipe differs')
    for name, digest in umt['source_archives'].items():
        if sources_by_name.get(name) != digest:
            raise ValueError('Upstream extractor source archive differs')
    native = json.loads((ROOT/'licenses/third-party/Magick.Native-provenance.json').read_text())
    if (sha256(runtime/'backend/extractor/Magick.Native-Q8-x64.dll') != native['bundled_sha256']
        or sha256(runtime/'licenses/third-party/Magick.Native-NOTICE.txt') != native['notice_sha256']):
        raise ValueError('Native library or its license notice differs')
    files = source_files()
    if any(not file.is_file() for file in files):
        raise ValueError('Missing source file')
    out.mkdir(parents=True, exist_ok=False)
    name = 'UTdrSpriteLibrary-' + VERSION
    zip_files(out / (name + '-source.zip'), [(p, name + '/' + p.relative_to(ROOT).as_posix()) for p in files])
    zip_files(out / (name + '-windows-x64.zip'),
              [(p, name + '/' + p.relative_to(runtime).as_posix()) for p in runtime_files])
    entries = [(upstream/r['file'], 'upstream-sources/'+r['file']) for r in records]
    entries += [(upstream/'manifest.json', 'upstream-sources/manifest.json'),
                (ROOT/'docs/NATIVE_SOURCES.md', 'upstream-sources/README.md')]
    zip_files(out/(name+'-upstream-sources.zip'), entries, zipfile.ZIP_STORED)
    print(json.dumps({'directory': str(out), 'runtime_MiB': round(sum(p.stat().st_size for p in runtime_files)/1048576, 2),
                      'archives': {p.name: round(p.stat().st_size/1048576, 2) for p in out.glob('*.zip')}}, indent=2))


if __name__ == '__main__':
    main()
