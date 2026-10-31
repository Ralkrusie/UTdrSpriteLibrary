"""Keep the self-contained CLI runtime; omit unrelated bundled scripts and dev docs."""
import json
import shutil
from pathlib import Path


def copy_umt(source, destination):
    source, destination = Path(source), Path(destination)
    if not (source / 'UndertaleModCli.exe').is_file():
        raise ValueError('UTMT CLI missing')
    destination.mkdir(parents=True, exist_ok=False)
    kept = removed = 0
    excluded = []
    for file in source.rglob('*'):
        if not file.is_file():
            continue
        relative = file.relative_to(source)
        # Scripts include image fixtures, editors and game modifiers, none invoked by export.csx.
        # Keep all runtime assemblies, native binaries, GameSpecificData and license notices.
        if relative.parts[0] == 'Scripts' or file.suffix.lower() in ('.xml', '.pdb'):
            removed += file.stat().st_size
            excluded.append(relative.as_posix())
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
        kept += file.stat().st_size
    report = {'kept_bytes': kept, 'excluded_bytes': removed, 'excluded': excluded}
    (destination / 'sprite-runtime-profile.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    print(copy_umt(args.source,args.out))
