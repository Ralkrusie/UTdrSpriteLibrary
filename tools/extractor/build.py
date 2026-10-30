"""Compile our read-only extraction script; omit the interactive CLI and Roslyn at runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--dotnet', default='dotnet')
    parser.add_argument('--library', type=Path, required=True, help='UndertaleModLib directory built by build_upstream.py')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    umt = ROOT / 'vendor/umt/0.9.2.0'
    archive = ROOT / 'vendor/umt/cli-download.zip'
    if digest(archive) != 'e7573e45d107be34f81f955c6e4afc3c7c8f2628e5a6f307a871e3825b3dfb40':
        raise ValueError('UMT source archive checksum mismatch')
    with zipfile.ZipFile(archive) as zipped:
        for file in umt.glob('*.dll'):
            if file.read_bytes() != zipped.read(file.name):
                raise ValueError('UMT source binary differs from verified archive: '+file.name)
    source_library = args.library.resolve()
    provenance = json.loads((source_library/'source-build.json').read_text(encoding='utf-8'))
    if provenance['build_script_sha256'] != digest(HERE/'build_upstream.py'):
        raise ValueError('Upstream library build recipe differs')
    references = out/'references'
    references.mkdir()
    for file in umt.glob('*.dll'):
        shutil.copy2(file, references/file.name)
    for name in ('UndertaleModLib.dll', 'Underanalyzer.dll'):
        if digest(source_library/name) != provenance['files'][name]:
            raise ValueError('Source-built library checksum mismatch: '+name)
        shutil.copy2(source_library/name, references/name)
    script = ROOT / 'tools/export.csx'
    source = script.read_text(encoding='utf-8-sig').replace('EnsureDataLoaded();',
        'using var stream = File.OpenRead(args[0]);\n'
        'using var Data = UndertaleModLib.UndertaleIO.Read(stream, (message, important) => Console.WriteLine(message));')
    source = source.replace('ScriptMessage(', 'Console.WriteLine(')
    generated = out / 'Program.cs'
    generated.write_text(source, encoding='utf-8')
    env = dict(os.environ, DOTNET_CLI_HOME=str(ROOT/'vendor/dotnet-home'), NUGET_PACKAGES=str(ROOT/'vendor/nuget'),
               DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
    package = out / 'SpriteExtractor'
    with (out/'publish.log').open('w', encoding='utf-8') as log:
        subprocess.run([args.dotnet, 'publish', str(HERE/'SpriteExtractor.csproj'), '-c', 'Release',
                        '-o', str(package), '-p:ExportSource='+str(generated), '-p:UmtDir='+str(references)], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    # Roslyn's native symbol reader and XML documentation are copied by SDK reference
    # discovery, but are not used by the compiled, non-scripting extraction entry point.
    for file in package.glob('*.xml'):
        file.unlink()
    (package/'Microsoft.DiaSymReader.Native.amd64.dll').unlink(missing_ok=True)
    # The output contains the same image extraction implementation, precompiled once.
    for file in ('LICENSE.txt',):
        shutil.copy2(umt/file, package/file)
    licenses = package/'licenses'
    shutil.copytree(ROOT/'tools/animation/licenses', licenses)
    shutil.copytree(ROOT/'licenses/third-party', licenses, dirs_exist_ok=True)
    shutil.copy2(source_library/'source-build.json', package/'upstream-source-build.json')
    runtime = ROOT/'vendor/nuget/microsoft.netcore.app.runtime.win-x64/10.0.10'
    for file in ('LICENSE.TXT', 'THIRD-PARTY-NOTICES.TXT'):
        shutil.copy2(runtime/file, licenses/('.NET-'+file))
    profile = {'umt': '0.9.2.0', 'dotnet': '10.0.10', 'source_script_sha256': digest(script),
               'source_library_sha256': digest(references/'UndertaleModLib.dll'),
               'files': {file.name: digest(file) for file in package.glob('*') if file.is_file()},
               'bytes': sum(file.stat().st_size for file in package.rglob('*') if file.is_file())}
    (package/'build-profile.json').write_text(json.dumps(profile, indent=2), encoding='utf-8')
    print(json.dumps({'package': str(package), 'bytes': profile['bytes']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
