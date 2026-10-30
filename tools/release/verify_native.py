"""Match the signed UMT Magick.Native DLL to its upstream native release."""
import hashlib
import json
from pathlib import Path
import zipfile
import pefile

ROOT = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalized(data):
    pe = pefile.PE(data=data)
    security = pe.OPTIONAL_HEADER.DATA_DIRECTORY[4]
    result = bytearray(data[:security.VirtualAddress] if security.Size else data)
    checksum = pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum')
    result[checksum:checksum+4] = b'\0' * 4
    offset = security.get_file_offset()
    result[offset:offset+8] = b'\0' * 8
    return bytes(result)


def main():
    artifact = ROOT/'vendor/release-sources/windows-Q8-x64.zip'
    with zipfile.ZipFile(artifact) as zipped:
        upstream = zipped.read('Magick.Native-Q8-x64.dll')
        notice = zipped.read('NOTICE.txt')
    bundled = (ROOT/'vendor/umt/0.9.2.0/Magick.Native-Q8-x64.dll').read_bytes()
    if normalized(upstream) != normalized(bundled):
        raise ValueError('Native code differs beyond PE signing/checksum fields')
    output = ROOT/'licenses/third-party'
    output.mkdir(parents=True, exist_ok=True)
    (output/'Magick.Native-NOTICE.txt').write_bytes(notice)
    report = {'component': 'Magick.Native Q8 x64', 'release': '2026.727.1945',
              'url': 'https://github.com/dlemstra/Magick.Native/releases/download/2026.727.1945/windows-Q8-x64.zip',
              'native_source_commit': '1187ae6ead3c4ac8b3020cfd8a98b9990697eec6',
              'imagemagick_source_commit': '360eda553586e389c9c725fc49df94f209a8a3c7',
              'dependencies_release': '2026.07.27.0556',
              'archive_sha256': sha(artifact.read_bytes()), 'unsigned_sha256': sha(upstream),
              'bundled_sha256': sha(bundled), 'notice_sha256': sha(notice),
              'normalized_pe_sha256': sha(normalized(bundled)),
              'comparison': 'All PE bytes match after excluding signature certificate, security directory and checksum'}
    (output/'Magick.Native-provenance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('PASS: Magick.Native fixed upstream build matches signed bundle; complete upstream notice retained.')


if __name__ == '__main__':
    main()
