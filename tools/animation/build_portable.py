"""Build a self-contained backend on the target operating system."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True, help='New build directory')
    parser.add_argument('--ffmpeg', type=Path, required=True, help='Directory produced by tools/ffmpeg/build.py')
    args = parser.parse_args()
    ffmpeg = args.ffmpeg.resolve()
    ffmpeg_profile = json.loads((ffmpeg / 'build-profile.json').read_text(encoding='utf-8'))
    binary = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
    recipe = ROOT / 'tools/ffmpeg' / ('build.py' if sys.platform == 'win32' else 'build_posix.py')
    if sys.platform != 'win32' and (ffmpeg_profile.get('platform') != sys.platform or ffmpeg_profile.get('machine') != platform.machine()):
        raise ValueError('FFmpeg target does not match this build host')
    if hashlib.sha256((ffmpeg / binary).read_bytes()).hexdigest() != ffmpeg_profile['ffmpeg_sha256']:
        raise ValueError('FFmpeg binary checksum mismatch')
    if ffmpeg_profile['build_script_sha256'] != hashlib.sha256(recipe.read_bytes()).hexdigest():
        raise ValueError('FFmpeg was built using a different build recipe')
    heart = ROOT / 'assets/ui/spr_dodgeheart_0.png'
    if not heart.is_file() or hashlib.sha256(heart.read_bytes()).hexdigest() != 'cf2e8376574f1ccd958063bafd59267a2829e8790783a9d5a029cdb348a2c377':
        raise ValueError('UI heart dependency missing or changed; see docs/BUILD.md')
    title = ROOT / 'assets/ui/fnt-main-title.svg'
    if not title.is_file() or hashlib.sha256(title.read_bytes()).hexdigest() != '2de9648dedb58a4b56bc74cbb49bd59eab4a2b94bcddfb6f9f5e8f9006679387':
        raise ValueError('fnt_main title dependency missing or changed')
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', *(['--windowed'] if sys.platform == 'win32' else []),
        '--name', 'UTdrSpriteBackend', '--distpath', str(output),
        # We copy the encoder executable below. The imageio hook would bundle it again.
        '--exclude-module', 'imageio_ffmpeg',
        # Game packages use PNG; AVIF is not an input or export format.
        '--exclude-module', 'PIL.AvifImagePlugin', '--exclude-module', 'PIL._avif',
        '--workpath', str(output / '_build'), '--specpath', str(output / '_build'),
        '--add-data', f'{UI / "index.html"}{os.pathsep}.', '--add-data', f'{UI / "app.js"}{os.pathsep}.',
        '--add-data', f'{UI / "style.css"}{os.pathsep}.',
        '--add-data', f'{heart}{os.pathsep}ui-assets',
        '--add-data', f'{title}{os.pathsep}ui-assets',
        '--add-data', f'{UI / "library-ui.js"}{os.pathsep}.',
        '--add-data', f'{ROOT / "tools/desktop/drag-ui.js"}{os.pathsep}.',
        '--add-data', f'{ROOT / "tools/export.csx"}{os.pathsep}.', str(UI / 'server.py'),
    ], check=True)
    package = output / 'UTdrSpriteBackend'
    shutil.copy2(ffmpeg / binary, package / '_internal' / binary)
    (package / '使用说明.txt').write_text('UTdr Sprite Library 后端组件。请通过桌面版启动。\n素材 ZIP、个人设置和导出均由桌面版分开保存。\n', encoding='utf-8-sig')
    licenses = package / 'licenses'
    licenses.mkdir()
    shutil.copytree(UI / 'licenses', licenses, dirs_exist_ok=True)
    if sys.platform != 'win32':
        notice = (licenses / 'FFmpeg-SOURCE.txt').read_text(encoding='utf-8')
        notice = notice.replace('tools/ffmpeg/build.py', 'tools/ffmpeg/build_posix.py').replace('MSVC static build', 'Native Clang/GCC static FFmpeg build')
        (licenses / 'FFmpeg-SOURCE.txt').write_text(notice, encoding='utf-8')
    for file in ('build-profile.json', 'config.h', 'config_components.h', 'compiler-version.txt', 'build-tools.txt', 'version.txt', 'license-build.txt'):
        shutil.copy2(ffmpeg / file, licenses / ('FFmpeg-' + file))
    for name in ('Pillow', 'PyInstaller'):
        dist = importlib.metadata.distribution(name)
        for file in dist.files or []:
            if 'license' in file.name.lower() or 'copying' in file.name.lower():
                source = Path(dist.locate_file(file))
                if source.is_file():shutil.copy2(source, licenses / (name + '-' + file.name))
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if python_license.exists():shutil.copy2(python_license, licenses / 'Python-LICENSE.txt')
    for component in ('tcl8.6', 'tk8.6'):
        license_file = Path(sys.base_prefix) / 'tcl' / component / 'license.terms'
        if license_file.exists():shutil.copy2(license_file, licenses / (component + '-license.terms'))
    (package / 'THIRD_PARTY.txt').write_text(
        'Runtime: CPython, Pillow, Tcl/Tk, PyInstaller bootloader. License texts are in licenses/.\n'
        'DELTARUNE sprites and other game assets belong to their respective rights holders.\n', encoding='utf-8')
    (output / 'build-info.json').write_text(json.dumps({
        'python': sys.version.split()[0], 'Pillow': importlib.metadata.version('Pillow'),
        'PyInstaller': importlib.metadata.version('PyInstaller'), 'package': str(package),
    }, indent=2), encoding='utf-8')
    print(f'Portable package: {package}', flush=True)


if __name__ == '__main__':
    main()
