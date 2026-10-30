"""Build UndertaleModLib and its pinned submodule from the collected sources."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
UMT_COMMIT = '03c7048438347799e0717b6e57a9358d000472e0'
UA_COMMIT = '4ff50a866b4c1a7acee8cebe6a56d6a48709b453'


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def extract(archive, prefix, destination):
    with zipfile.ZipFile(archive) as zipped:
        for name in zipped.namelist():
            if not name.startswith(prefix) or '..' in Path(name).parts:
                raise ValueError('Invalid source archive path')
            relative = name[len(prefix):]
            if not relative or name.endswith('/'):
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zipped.read(name))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    archives = ROOT / 'vendor/release-sources'
    source = out / 'source/UndertaleModTool'
    umt = archives / 'UndertaleModTool-0.9.2.0.zip'
    ua = archives / 'Underanalyzer-4ff50a8.zip'
    manifest = {item['file']: item for item in json.loads((archives/'manifest.json').read_text())}
    for archive in (umt, ua):
        if digest(archive) != manifest[archive.name]['sha256']:
            raise ValueError('Source checksum mismatch')
    extract(umt, 'UndertaleModTool-' + UMT_COMMIT + '/', source)
    extract(ua, 'Underanalyzer-' + UA_COMMIT + '/', source / 'Underanalyzer')
    project = source / 'UndertaleModLib/UndertaleModLib.csproj'
    # This sole upstream edit records the actual snapshot, instead of the parent repository's HEAD.
    before = project.read_text(encoding='utf-8-sig')
    after, count = re.subn(r'<Target Name="PreBuild".*?</Target>',
                          '<Target Name="PreBuild" BeforeTargets="PreBuildEvent">'
                          '<WriteLinesToFile File="$(ProjectDir)/gitversion.txt" Lines="'
                          + UMT_COMMIT + ';source-snapshot" Overwrite="true" /></Target>',
                          before, flags=re.S)
    if count != 1:
        raise ValueError('Unexpected upstream version target')
    project.write_text(after, encoding='utf-8')
    package = out / 'UndertaleModLib'
    env = dict(os.environ, DOTNET_CLI_HOME=str(ROOT/'vendor/dotnet-home'),
               NUGET_PACKAGES=str(ROOT/'vendor/nuget'), DOTNET_CLI_TELEMETRY_OPTOUT='1')
    with (out/'build.log').open('w', encoding='utf-8') as log:
        subprocess.run(['dotnet', 'build', str(project), '-c', 'Release', '-f', 'net10.0',
                        '-o', str(package), '-p:GeneratePackageOnBuild=false',
                        '-p:CopyLocalLockFileAssemblies=true'],
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    shutil.copy2(source/'LICENSE.txt', package/'LICENSE.txt')
    profile = {'umt': UMT_COMMIT, 'underanalyzer': UA_COMMIT,
               'source_archives': {p.name: digest(p) for p in (umt, ua)},
               'build_script_sha256': digest(Path(__file__)),
               'modification': 'Replace PreBuild Git probing with fixed source-snapshot provenance only',
               'files': {p.relative_to(package).as_posix(): digest(p) for p in package.rglob('*') if p.is_file()}}
    (package/'source-build.json').write_text(json.dumps(profile, indent=2), encoding='utf-8')
    print(package)


if __name__ == '__main__':
    main()
