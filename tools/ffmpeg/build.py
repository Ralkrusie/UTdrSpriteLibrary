"""Build the fixed FFmpeg source with MSVC, without third-party codec libraries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA256 = '201fe5427412e0a0a0304a545f2aceb7e95e2ef1c26a7e486d3106fd156ed812'
OPTIONS = [
    '--toolchain=msvc', '--arch=x86_64', '--disable-everything', '--disable-autodetect',
    '--disable-network', '--disable-doc', '--disable-debug', '--disable-asm',
    '--disable-ffplay', '--disable-ffprobe', '--disable-avdevice', '--disable-postproc',
    '--disable-shared', '--enable-static', '--enable-small',
    '--enable-protocol=file,pipe', '--enable-demuxer=rawvideo,mov',
    '--enable-decoder=rawvideo,qtrle', '--enable-encoder=qtrle,rawvideo',
    '--enable-muxer=mov,rawvideo', '--enable-filter=buffer,buffersink,format,scale,null',
]


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def posix(path):
    value = path.resolve().as_posix()
    if len(value) < 3 or value[1:3] != ':/':
        raise ValueError('A local Windows drive path is required')
    return '/' + value[0].lower() + value[2:]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--msys2', type=Path, required=True)
    parser.add_argument('--vcvars', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=8)
    args = parser.parse_args()
    archive = ROOT / 'vendor/release-sources/FFmpeg-n7.1.zip'
    if digest(archive) != SOURCE_SHA256:
        raise ValueError('FFmpeg source archive checksum mismatch')
    bash = args.msys2.resolve() / 'usr/bin/bash.exe'
    vcvars = args.vcvars.resolve()
    out = args.out.resolve()
    for path in (bash, vcvars, out):
        if any(c in str(path) for c in '%!&|<>^"\r\n'):
            raise ValueError('Unsupported command-script path')
    if not bash.is_file() or not vcvars.is_file() or not 1 <= args.jobs <= 64:
        raise ValueError('Missing build tools or invalid job count')
    out.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as zipped:
        if any('..' in Path(n).parts or not n.startswith('FFmpeg-n7.1/') for n in zipped.namelist()):
            raise ValueError('Invalid FFmpeg archive path')
        zipped.extractall(out / 'source')
    source = out / 'source/FFmpeg-n7.1'
    # GitHub snapshots lack VERSION; avoid picking up the enclosing app's Git hash.
    (source / 'VERSION').write_text('7.1-utdr1\n', encoding='utf-8')
    build = out / 'build'
    build.mkdir()
    shell = out / 'build.sh'
    shell.write_text('set -eu\nexport PATH="/usr/bin:$PATH"\n'
                     + 'cd ' + shlex.quote(posix(build)) + '\n'
                     + shlex.quote(posix(source / 'configure')) + ' ' + shlex.join(OPTIONS) + '\n'
                     + f'make -j{args.jobs} ffmpeg.exe\n'
                     + 'cl.exe 2>&1 | head -n 3 > compiler-version.txt\n'
                     + 'pacman -Q > build-tools.txt\n', encoding='utf-8', newline='\n')
    cmd = out / 'build.cmd'
    cmd.write_text('@echo off\ncall "' + str(vcvars) + '" >nul\n'
                   + 'if errorlevel 1 exit /b 1\n'
                   + '"' + str(bash) + '" --noprofile --norc "' + posix(shell) + '"\n'
                   + 'exit /b %errorlevel%\n', encoding='utf-8')
    with (out / 'build.log').open('w', encoding='utf-8') as log:
        subprocess.run([os.environ.get('COMSPEC', 'cmd.exe'), '/d', '/c', str(cmd)],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    package = out / 'ffmpeg-minimal'
    package.mkdir()
    shutil.copy2(build / 'ffmpeg.exe', package / 'ffmpeg.exe')
    for file in ('COPYING.LGPLv2.1', 'LICENSE.md'):
        shutil.copy2(source / file, package / file)
    for file in ('config.h', 'config_components.h', 'compiler-version.txt', 'build-tools.txt'):
        shutil.copy2(build / file, package / file)
    version = subprocess.check_output([str(package / 'ffmpeg.exe'), '-version'], text=True)
    license_text = subprocess.check_output([str(package / 'ffmpeg.exe'), '-L'], text=True)
    if 'enable-gpl' in version or 'enable-nonfree' in version:
        raise ValueError('Unexpected FFmpeg license configuration')
    (package / 'version.txt').write_text(version, encoding='utf-8')
    (package / 'license-build.txt').write_text(license_text, encoding='utf-8')
    profile = {'version': '7.1', 'license': 'LGPL-2.1-or-later',
               'source_archive': archive.name, 'source_sha256': SOURCE_SHA256,
               'build_script_sha256': digest(Path(__file__)), 'configure': OPTIONS,
               'generated_source_files': {'VERSION': '7.1-utdr1\n'},
               'ffmpeg_sha256': digest(package / 'ffmpeg.exe'),
               'bytes': (package / 'ffmpeg.exe').stat().st_size}
    (package / 'build-profile.json').write_text(json.dumps(profile, indent=2), encoding='utf-8')
    print(json.dumps({'directory': str(package), **profile}, indent=2))


if __name__ == '__main__':
    main()
