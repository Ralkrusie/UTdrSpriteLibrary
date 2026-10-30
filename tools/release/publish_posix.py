"""Publish the explicitly approved, successful native build without rebuilding it."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import urllib.error
import urllib.request
import zipfile

REPO = 'Ralkrusie/UTdrSpriteLibrary'
RUN = 41050720356
COMMIT = '4df3fff2daa58dcccf67d9d6cda9d1eb5d25d3ab'
TAG = 'v0.3.0-rc2-posix.1'
ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'releases/posix-publication'
EXPECTED = {f'UTdrSpriteLibrary-{target}-candidate' for target in ('linux-x64', 'darwin-x64', 'darwin-arm64')}
BODY = '''macOS／Linux 首次预发布版 · UT／DR 精灵素材管理与导出。

**macOS／Linux 版本未在对应机器上人工实测。** 已通过对应平台的 CI 构建、后端导出与桌面启动自动检查；这不等同于人工实机使用验证。

### 下载

- Apple Silicon Mac：`darwin-arm64-candidate.zip`
- Intel Mac：`darwin-x64-candidate.zip`
- Linux x64：`linux-x64-candidate.tar.gz`（Ubuntu 22.04 构建基线）

解压后，macOS 打开 `UTdrSpriteLibrary.app`；Linux 运行 `SpriteLibrary`。保留完整目录，无需安装 Python 或 FFmpeg。

### 当前范围

- 导入已有 ZIP 素材包，支持浏览、搜索、收藏、动画预览和 PNG／GIF／APNG／MOV 导出。
- **暂不支持从游戏制作素材包。** 可先在 Windows 版制作，再复制 ZIP 到本机导入。
- macOS 仅作开发用 ad-hoc 签名，尚未进行 Developer ID 签名和 Apple 公证，系统可能拦截启动。
- 外部软件接收拖拽、不同 Linux 桌面环境及下载后的安装体验尚待人工验证。
- 不附带游戏素材包或个人数据。

Windows 用户请继续使用 [Windows 预发布版](https://github.com/Ralkrusie/UTdrSpriteLibrary/releases/tag/v0.3.0-rc2)。

`source.zip` 与 `FFmpeg-n7.1.zip` 是对应项目源码和 FFmpeg 上游源码，普通使用无需下载。

---

macOS / Linux prerelease. **Not manually tested on corresponding machines.** Native CI build, backend export and desktop startup checks passed; these do not replace hands-on testing.

Import existing sprite ZIP packages; game extraction is not available on these platforms yet. macOS builds are ad-hoc signed only, without Developer ID signing or notarization. Linux builds use Ubuntu 22.04 as their baseline. No game asset packs or personal data are included.
'''


def api(path):
    request = urllib.request.Request('https://api.github.com/repos/' + REPO + path,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json', 'User-Agent': 'UTdrSpriteLibrary-release'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def find_release():
    releases = [r for r in api('/releases?per_page=100') if r['tag_name'] == TAG]
    if len(releases) > 1:
        raise ValueError('Multiple releases use the same tag')
    return releases[0] if releases else None


def gh(*args):
    print('GitHub CLI: ' + ' '.join(args[:3]), flush=True)
    subprocess.run(['gh', *args], cwd=ROOT, check=True, timeout=600)


def digest(file):
    with file.open('rb') as stream:
        return 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    if os.environ.get('GITHUB_REPOSITORY') != REPO or os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        raise RuntimeError('Use the manually dispatched publication workflow in the project repository')
    run = api(f'/actions/runs/{RUN}')
    if run['conclusion'] != 'success' or run['head_sha'] != COMMIT:
        raise ValueError('Build is not the approved successful commit')
    artifacts = api(f'/actions/runs/{RUN}/artifacts')['artifacts']
    if {a['name'] for a in artifacts} != EXPECTED or any(a['expired'] for a in artifacts):
        raise ValueError('Expected native artifacts are missing or expired')
    WORK.mkdir(parents=True, exist_ok=False)
    for name in sorted(EXPECTED):
        print('Downloading ' + name, flush=True)
        gh('run', 'download', str(RUN), '--name', name, '--dir', str(WORK / 'artifacts' / name))
    files = sorted(p for p in (WORK / 'artifacts').rglob('*') if p.is_file())
    expected_files = {f'UTdrSpriteLibrary-0.3.0-rc2-{target}-candidate.{ext}'
                      for target, ext in (('linux-x64', 'tar.gz'), ('darwin-x64', 'zip'), ('darwin-arm64', 'zip'))}
    if {p.name for p in files} != expected_files or len(files) != 3:
        raise ValueError('Unexpected build attachments')
    for file in files:
        print('Inspecting ' + file.name, flush=True)
        if file.suffix == '.zip':
            with zipfile.ZipFile(file, metadata_encoding='utf-8') as archive:
                if archive.testzip() is not None:
                    raise ValueError('Corrupt native archive')
                notices = [n for n in archive.namelist() if n.count('/') == 3 and '/Contents/Resources/' in n and n.endswith('.txt') and not n.startswith('__MACOSX/')]
                notice = '\n'.join(archive.read(n).decode('utf-8', errors='replace') for n in notices)
        else:
            with tarfile.open(file, 'r:gz') as archive:
                notices = [m for m in archive.getmembers() if m.name.endswith('/使用说明.txt') and m.name.count('/') == 1]
                notice = archive.extractfile(notices[0]).read().decode('utf-8') if len(notices) == 1 else ''
        if '未在对应机器上人工实测' not in notice:
            raise ValueError('Missing manual-test status in ' + file.name + '; notice entries: ' + repr(notices))
    print('Preparing corresponding source archives', flush=True)
    source = WORK / 'UTdrSpriteLibrary-0.3.0-rc2-posix.1-source.zip'
    subprocess.run(['git', 'archive', '--format=zip', '--prefix=UTdrSpriteLibrary/',
                    '-o', str(source), COMMIT], cwd=ROOT, check=True)
    ffmpeg = WORK / 'FFmpeg-n7.1.zip'
    subprocess.run(['curl', '--fail', '--location', '--retry', '3',
                    'https://github.com/FFmpeg/FFmpeg/archive/refs/tags/n7.1.zip', '-o', str(ffmpeg)], check=True)
    if digest(ffmpeg) != 'sha256:201fe5427412e0a0a0304a545f2aceb7e95e2ef1c26a7e486d3106fd156ed812':
        raise ValueError('FFmpeg source mismatch')
    files += [source, ffmpeg]
    notes = WORK / 'notes.md'
    notes.write_text(BODY, encoding='utf-8')
    try:
        release = find_release()
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        release = None
    if release is not None and not release['draft']:
        raise ValueError('Release is already public; refusing to replace assets')
    if release is None:
        gh('release', 'create', TAG, '--draft', '--prerelease', '--latest=false', '--target', COMMIT,
           '--title', 'UTdrSpriteLibrary 0.3.0-rc2 · macOS / Linux 预发布版', '--notes-file', str(notes))
    else:
        if release['target_commitish'] != COMMIT:
            raise ValueError('Draft targets another commit')
    release = find_release()
    existing = {a['name']: a for a in release['assets']}
    for file in files:
        if file.name not in existing:
            gh('release', 'upload', TAG, str(file))
        else:
            if existing[file.name].get('digest') != digest(file):
                raise ValueError('Existing draft asset differs')
    release = find_release()
    expected = {p.name: (p.stat().st_size, digest(p)) for p in files}
    if {a['name'] for a in release['assets']} != set(expected):
        raise ValueError('Unexpected release attachments')
    for asset in release['assets']:
        if asset['state'] != 'uploaded' or (asset['size'], asset.get('digest')) != expected[asset['name']]:
            raise ValueError('Uploaded asset differs')
    gh('release', 'edit', TAG, '--draft=false', '--prerelease', '--latest=false')
    print('Published https://github.com/' + REPO + '/releases/tag/' + TAG)


if __name__ == '__main__':
    main()
