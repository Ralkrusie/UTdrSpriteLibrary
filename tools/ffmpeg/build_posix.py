"""Native macOS/Linux FFmpeg build using the same minimal codecs as Windows."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile
from build import ROOT, SOURCE_SHA256, OPTIONS, digest


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--jobs', type=int, default=min(os.cpu_count() or 2, 8))
    a = p.parse_args()
    if sys.platform not in ('darwin', 'linux') or platform.machine() not in ('arm64', 'aarch64', 'x86_64'):
        p.error('Run natively on macOS or Linux, x64 or arm64')
    if not 1 <= a.jobs <= 64:
        p.error('jobs must be between 1 and 64')
    archive = ROOT / 'vendor/release-sources/FFmpeg-n7.1.zip'
    if digest(archive) != SOURCE_SHA256:
        raise ValueError('FFmpeg source checksum mismatch')
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        if any('..' in Path(n).parts or not n.startswith('FFmpeg-n7.1/') for n in z.namelist()):
            raise ValueError('Invalid source archive path')
        z.extractall(out / 'source')
        for entry in z.infolist():
            mode = entry.external_attr >> 16
            if mode and not entry.is_dir():
                (out / 'source' / entry.filename).chmod(mode & 0o777)
    source = out / 'source/FFmpeg-n7.1'
    (source / 'VERSION').write_text('7.1-utdr1\n', encoding='utf-8')
    build = out / 'build'
    build.mkdir()
    options = [o for o in OPTIONS if not o.startswith(('--toolchain=', '--arch='))]
    options += ['--cc=clang' if sys.platform == 'darwin' else '--cc=cc']
    with (out / 'build.log').open('w') as log:
        subprocess.run(['sh', str(source / 'configure'), *options], cwd=build, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['make', f'-j{a.jobs}', 'ffmpeg'], cwd=build, stdout=log, stderr=subprocess.STDOUT, check=True)
    package = out / 'ffmpeg-minimal'
    package.mkdir()
    shutil.copy2(build / 'ffmpeg', package / 'ffmpeg')
    for name in ('COPYING.LGPLv2.1', 'LICENSE.md'):
        shutil.copy2(source / name, package / name)
    for name in ('config.h', 'config_components.h'):
        shutil.copy2(build / name, package / name)
    for name, command in {
        'compiler-version.txt': ['clang' if sys.platform == 'darwin' else 'cc', '--version'],
        'build-tools.txt': ['make', '--version'],
        'version.txt': [str(package / 'ffmpeg'), '-version'],
        'license-build.txt': [str(package / 'ffmpeg'), '-L'],
    }.items():
        result = subprocess.check_output(command, text=True, stderr=subprocess.STDOUT)
        (package / name).write_text(result, encoding='utf-8')
    profile = {'platform': sys.platform, 'machine': platform.machine(),
               'version': '7.1', 'license': 'LGPL-2.1-or-later', 'configure': options,
               'source_archive': archive.name, 'source_sha256': SOURCE_SHA256,
               'generated_source_files': {'VERSION': '7.1-utdr1\n'},
               'build_script_sha256': digest(Path(__file__)),
               'ffmpeg_sha256': digest(package / 'ffmpeg')}
    (package / 'build-profile.json').write_text(json.dumps(profile, indent=2), encoding='utf-8')
    print(package)


if __name__ == '__main__':
    main()
