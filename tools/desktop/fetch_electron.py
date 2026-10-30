"""Fetch a fixed native Electron archive and verify its official SHA-256."""
import hashlib
from pathlib import Path
import platform
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
VERSION = '45.1.0'


def target():
    if sys.platform not in ('darwin', 'linux'):
        raise ValueError('This entry point is for native macOS/Linux builds')
    arch = {'x86_64': 'x64', 'arm64': 'arm64', 'aarch64': 'arm64'}.get(platform.machine())
    if not arch:
        raise ValueError('Unsupported architecture')
    return sys.platform, arch


def main():
    system, arch = target()
    folder = ROOT / 'vendor/electron' / f'{system}-{arch}'
    folder.mkdir(parents=True, exist_ok=True)
    name = f'electron-v{VERSION}-{system}-{arch}.zip'
    base = f'https://github.com/electron/electron/releases/download/v{VERSION}/'
    with urllib.request.urlopen(base + 'SHASUMS256.txt', timeout=60) as response:
        checksums = response.read()
    wanted = next(line.split()[0] for line in checksums.decode().splitlines() if line.split()[-1].lstrip('*') == name)
    destination = folder / name
    if not destination.exists() or hashlib.sha256(destination.read_bytes()).hexdigest() != wanted:
        part = destination.with_suffix('.part')
        with urllib.request.urlopen(base + name, timeout=120) as response, part.open('wb') as stream:
            while block := response.read(1024 * 1024):
                stream.write(block)
        if hashlib.sha256(part.read_bytes()).hexdigest() != wanted:
            raise ValueError('Electron checksum mismatch')
        part.replace(destination)
    (folder / 'SHASUMS256.txt').write_bytes(checksums)
    print(destination)


if __name__ == '__main__':
    main()
