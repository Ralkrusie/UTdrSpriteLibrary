"""Prepare fixed Windows dependencies and attach tested binaries to a draft."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path.cwd()
REPO = 'Ralkrusie/UTdrSpriteLibrary'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response, path.open('wb') as stream:
        shutil.copyfileobj(response, stream)


def prepare():
    (ROOT / 'releases').mkdir(exist_ok=True)
    electron = ROOT / 'vendor/electron'
    base = 'https://github.com/electron/electron/releases/download/v45.1.0/'
    fetch(base + 'SHASUMS256.txt', electron / 'SHASUMS256.txt')
    fetch(base + 'electron-v45.1.0-win32-x64.zip', electron / 'electron-verified.zip')
    archive = ROOT / 'vendor/umt/cli-download.zip'
    fetch('https://github.com/UnderminersTeam/UndertaleModTool/releases/download/0.9.2.0/UTMT_CLI_v0.9.2.0-Windows.zip', archive)
    if digest(archive) != 'e7573e45d107be34f81f955c6e4afc3c7c8f2628e5a6f307a871e3825b3dfb40':
        raise ValueError('UMT checksum mismatch')
    with zipfile.ZipFile(archive) as z:
        if any(Path(n).is_absolute() or '..' in Path(n).parts for n in z.namelist()):
            raise ValueError('Invalid UMT archive path')
        z.extractall(ROOT / 'vendor/umt/0.9.2.0')
    fetch('https://github.com/dlemstra/Magick.Native/releases/download/2026.727.1945/windows-Q8-x64.zip', ROOT / 'vendor/release-sources/windows-Q8-x64.zip')


def api(path):
    req = urllib.request.Request('https://api.github.com/repos/' + REPO + path,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'User-Agent': 'UTdr-release', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def upload():
    tag, commit = os.environ['RELEASE_TAG'], os.environ['RELEASE_COMMIT']
    if os.environ.get('GITHUB_REPOSITORY') != REPO or os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        raise ValueError('Manual repository workflow required')
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() != commit:
        raise ValueError('Wrong source checkout')
    version = json.loads((ROOT / 'tools/desktop/package.json').read_text())['version']
    if tag != 'v' + version:
        raise ValueError('Wrong version')
    release = next(r for r in api('/releases?per_page=100') if r['tag_name'] == tag)
    if not release['draft'] or release['target_commitish'] != commit:
        raise ValueError('Wrong draft target')
    for suffix in ('windows-x64', 'upstream-sources'):
        file = ROOT / 'releases/public' / f'UTdrSpriteLibrary-{version}-{suffix}.zip'
        rid = release['id']
        existing = next((a for a in api(f'/releases/{rid}/assets') if a['name'] == file.name), None)
        if existing is None:
            subprocess.run(['gh', 'release', 'upload', tag, str(file)], check=True, timeout=600)
        asset = next(a for a in api(f'/releases/{rid}/assets') if a['name'] == file.name)
        if asset['state'] != 'uploaded' or asset['size'] != file.stat().st_size or asset['digest'] != 'sha256:' + digest(file):
            raise ValueError('Uploaded archive mismatch')
        print('Verified Windows attachment: ' + file.name, flush=True)
    print('Attachments ready; release remains a draft.', flush=True)


if __name__ == '__main__':
    {'prepare': prepare, 'upload': upload}[sys.argv[1]]()
