"""Assemble native ZIP-library editions. Run on the target OS and architecture."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import tarfile
import zipfile
from fetch_electron import ROOT, VERSION, target

HERE = Path(__file__).resolve().parent
RECORDS = {'Magick.Native-provenance.json', 'FFmpeg-build-profile.json'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--backend', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    system, arch = target()
    source = a.backend.resolve()
    for file in source.rglob('*'):
        relative = file.relative_to(source)
        if {'data', 'library', 'personal', 'exports'}.intersection(relative.parts):
            raise ValueError('Backend contains user data: ' + str(relative))
        if file.suffix in ('.db', '.sqlite', '.sqlite3', '.win'):
            raise ValueError('Backend contains unexpected data: ' + str(relative))
        if file.is_symlink() and not file.resolve().is_relative_to(source):
            raise ValueError('Backend symlink escapes its package: ' + str(relative))
    for name in ('UTdrSpriteBackend', 'utdr', '_internal/ffmpeg', 'licenses'):
        if not (source / name).exists():
            raise ValueError('Native backend missing ' + name)
    # Executing these also rejects a foreign-architecture or Windows backend.
    subprocess.run([str(source / 'UTdrSpriteBackend'), '--help'], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([str(source / '_internal/ffmpeg'), '-version'], check=True, stdout=subprocess.DEVNULL)
    name = f'electron-v{VERSION}-{system}-{arch}.zip'
    vendor = ROOT / 'vendor/electron' / f'{system}-{arch}'
    archive = vendor / name
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    if not any(line.split()[0] == sha and line.split()[-1].lstrip('*') == name for line in (vendor / 'SHASUMS256.txt').read_text().splitlines()):
        raise ValueError('Electron checksum mismatch')
    with zipfile.ZipFile(archive) as z:
        if any(Path(n).is_absolute() or '..' in Path(n).parts for n in z.namelist()):
            raise ValueError('Invalid Electron archive path')
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    # unzip preserves the official bundle's symlinks and executable permissions.
    subprocess.run(['unzip', '-q', str(archive), '-d', str(out)], check=True)
    version = json.loads((HERE / 'package.json').read_text())['version']
    if system == 'darwin':
        bundle = out / 'UTdrSpriteLibrary.app'
        (out / 'Electron.app').rename(bundle)
        resources = bundle / 'Contents/Resources'
        plist = bundle / 'Contents/Info.plist'
        info = plistlib.loads(plist.read_bytes())
        info.update(CFBundleIdentifier='io.github.ralkrusie.utdrspritelibrary',
                    CFBundleName='UTdrSpriteLibrary', CFBundleDisplayName='UTdrSpriteLibrary',
                    CFBundleShortVersionString=version.split('-')[0], CFBundleVersion=version.split('-')[0])
        info['CFBundleIconFile'] = 'app-icon.icns'
        shutil.copy2(ROOT / 'assets/ui/app-icon.icns', resources / 'app-icon.icns')
        plist.write_bytes(plistlib.dumps(info))
        payload = resources
    else:
        (out / 'electron').rename(out / 'SpriteLibrary')
        resources = out / 'resources'
        payload = out
    app = resources / 'app'
    app.mkdir(parents=True)
    for name in ('main.cjs', 'preload.cjs', 'platform.cjs', 'package.json'):
        shutil.copy2(HERE / name, app / name)
    shutil.copy2(ROOT / 'assets/ui/app-icon.png', app / 'app-icon.png')
    shutil.copytree(source, payload / 'backend', symlinks=True, ignore=shutil.ignore_patterns(*RECORDS, 'build-info.json'))
    launcher = payload / 'utdr'
    launcher.write_text('#!/bin/sh\nexec "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/backend/utdr" "$@"\n', encoding='utf-8', newline='\n')
    launcher.chmod(0o755)
    probe = subprocess.run([str(launcher), 'version', '--json'], check=True, capture_output=True, text=True, encoding='utf-8')
    if json.loads(probe.stdout).get('ok') is not True:
        raise ValueError('CLI launcher check failed')
    # Keep the upstream MIT grant separately before installing the project license.
    shutil.copy2(out / 'LICENSE', payload / 'Electron-LICENSE')
    if payload != out:
        shutil.copy2(out / 'LICENSES.chromium.html', payload / 'LICENSES.chromium.html')
    for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md', 'ASSET_NOTICE.md'):
        shutil.copy2(ROOT / name, payload / name)
    shutil.copytree(ROOT / 'licenses', payload / 'licenses', ignore=shutil.ignore_patterns(*RECORDS))
    (payload / 'docs').mkdir()
    for name in ('BUILD.md', 'NATIVE_SOURCES.md', 'CLI.md'):
        shutil.copy2(ROOT / 'docs' / name, payload / 'docs' / name)
    (payload / '使用说明.txt').write_text(
        'UTdrSpriteLibrary · macOS / Linux 候选版\n\n'
        'macOS／Linux 版本未在对应机器上人工实测；CI 自动检查不等同于实机使用验证。\n'
        '导入桌面版制作的 ZIP 素材包即可浏览、预览和导出。无需安装 Python 或 FFmpeg。\n'
        '此包暂不内置游戏提取器。素材包、收藏与设置存放在系统用户配置目录中。\n'
        'macOS：~/Library/Application Support/UTdrSpriteLibrary\n'
        'Linux：${XDG_CONFIG_HOME:-~/.config}/UTdrSpriteLibrary\n'
        '默认导出在该目录的 exports 中，也可在软件内选择其他位置。\n'
        '不附带游戏素材包。macOS 当前仅作本地 ad-hoc 签名，未公证。\n', encoding='utf-8')
    filename = f'UTdrSpriteLibrary-{version}-{system}-{arch}-candidate'
    if system == 'darwin':
        # Development signing only; this is not Developer ID signing/notarization.
        subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(bundle)], check=True)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(bundle)], check=True)
        packed = out.parent / (filename + '.zip')
        if packed.exists():
            raise FileExistsError(packed)
        subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(bundle), str(packed)], check=True)
    else:
        packed = out.parent / (filename + '.tar.gz')
        if packed.exists():
            raise FileExistsError(packed)
        with tarfile.open(packed, 'w:gz') as tar:
            tar.add(out, arcname=filename)
    print(packed)


if __name__ == '__main__':
    main()
