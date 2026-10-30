"""Attach a verified native build to an existing draft release; never publish it."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import urllib.request
import zipfile

REPO = 'Ralkrusie/UTdrSpriteLibrary'
ROOT = Path(__file__).resolve().parents[2]


def api(path):
    request = urllib.request.Request('https://api.github.com/repos/' + REPO + path,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json', 'User-Agent': 'UTdrSpriteLibrary-release'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def digest(file):
    with file.open('rb') as stream:
        return 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    if os.environ.get('GITHUB_REPOSITORY') != REPO or os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        raise RuntimeError('Use the manual publication workflow in the project repository')
    run_id = int(os.environ['NATIVE_RUN_ID'])
    version = json.loads((ROOT / 'tools/desktop/package.json').read_text())['version']
    tag = os.environ['RELEASE_TAG']
    if tag != 'v' + version:
        raise ValueError('Release tag does not match this source version')
    release = next(r for r in api('/releases?per_page=100') if r['tag_name'] == tag)
    if not release['draft'] or not release['prerelease']:
        raise ValueError('Only a draft prerelease may receive attachments')
    run = api(f'/actions/runs/{run_id}')
    if run['conclusion'] != 'success' or run['head_sha'] != release['target_commitish'] or run['path'] != '.github/workflows/desktop-posix.yml':
        raise ValueError('Native build is not the successful release commit')
    artifacts = api(f'/actions/runs/{run_id}/artifacts')['artifacts']
    targets = ('darwin-arm64', 'darwin-x64', 'linux-x64')
    expected = {f'UTdrSpriteLibrary-{t}-candidate' for t in targets}
    if {a['name'] for a in artifacts} != expected or any(a['expired'] for a in artifacts):
        raise ValueError('Native artifacts missing or expired')
    work = ROOT / 'releases/native-attachments'
    work.mkdir(parents=True, exist_ok=False)
    for target in targets:
        name = f'UTdrSpriteLibrary-{target}-candidate'
        subprocess.run(['gh', 'run', 'download', str(run_id), '--name', name, '--dir', str(work / target)], check=True, timeout=600)
        suffix = 'tar.gz' if target == 'linux-x64' else 'zip'
        filename = f'UTdrSpriteLibrary-{version}-{target}-candidate.{suffix}'
        files = [p for p in (work / target).rglob('*') if p.is_file()]
        if len(files) != 1 or files[0].name != filename:
            raise ValueError('Unexpected archive')
        file = files[0]
        if suffix == 'zip':
            with zipfile.ZipFile(file, metadata_encoding='utf-8') as z:
                if z.testzip() is not None:
                    raise ValueError('Corrupt ZIP')
                names = z.namelist()
                notes = [n for n in names if n.count('/') == 3 and '/Contents/Resources/' in n and n.endswith('.txt') and not n.startswith('__MACOSX/')]
                notice = ''.join(z.read(n).decode('utf-8', errors='replace') for n in notes)
        else:
            with tarfile.open(file, 'r:gz') as z:
                names = z.getnames()
                notes = [m for m in z.getmembers() if m.name.count('/') == 1 and m.name.endswith('/使用说明.txt')]
                notice = ''.join(z.extractfile(m).read().decode('utf-8') for m in notes)
        if '未在对应机器上人工实测' not in notice or not any(n.endswith('/backend/utdr') for n in names) or not any(n.endswith('/docs/CLI.md') for n in names):
            raise ValueError('CLI or platform notice missing')
        rid = release['id']
        prior = next((a for a in api(f'/releases/{rid}/assets') if a['name'] == filename), None)
        if prior is None:
            subprocess.run(['gh', 'release', 'upload', tag, str(file)], check=True, timeout=600)
        asset = next(a for a in api(f'/releases/{rid}/assets') if a['name'] == filename)
        if asset['state'] != 'uploaded' or asset['size'] != file.stat().st_size or asset.get('digest') != digest(file):
            raise ValueError('Uploaded asset differs from tested archive')
        print('Verified attachment: ' + filename, flush=True)
    print('Native attachments ready; release remains a draft.', flush=True)


if __name__ == '__main__':
    main()
