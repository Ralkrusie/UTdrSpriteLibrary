"""User/automation CLI. No web server, browser or Electron is required."""
import argparse
from contextlib import contextmanager
from datetime import datetime
import json
import os
from pathlib import Path
import signal
import sqlite3
import sys
import tempfile
import uuid
import zipfile

from encoder import settings
from export_files import named_entries, signature, find_duplicate
from export_service import export_batch, label
from import_game import extract
from library import LibraryStore, make_package
from preferences import Preferences

VERSION = '0.3.0'
CONTRACT = 1
ROOT = Path(__file__).resolve().parents[2] if not getattr(sys, 'frozen', False) else Path(sys.executable).resolve().parent
EXIT_CODES = {0: 'success', 1: 'internal_error', 2: 'invalid_argument', 3: 'not_found',
              4: 'conflict', 5: 'io_error', 6: 'export_failed', 130: 'cancelled'}


class CliError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code, self.details = code, details


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise CliError(2, message)


def parser():
    common = Parser(add_help=False)
    common.add_argument('--json', action='store_true', default=argparse.SUPPRESS,
                        help='Emit one UTF-8 JSON result (including errors) on stdout')
    common.add_argument('--data', type=Path, default=argparse.SUPPRESS,
                        help='Data directory; overrides UTDR_DATA_DIR and the platform default')
    root = Parser(prog='utdr', description='UT/DR sprite management and export, for people and automation.', parents=[common])
    commands = root.add_subparsers(dest='command', required=True, parser_class=Parser)

    def command(parent, name, help):
        return parent.add_parser(name, help=help, description=help, parents=[common])

    def group(name, help):
        return command(commands, name, help).add_subparsers(dest='action', required=True, parser_class=Parser)

    def package(p):
        p.add_argument('--package', required=True, help='Full package ID from packages list/import')

    def filters(p):
        p.add_argument('--query', default='', help='Case-insensitive substring of resource name')
        p.add_argument('--chapter', type=int, help='Filter by chapter number')
        p.add_argument('--multi-frame', action='store_true', help='Only animations with at least two frames')
        p.add_argument('--favorites', action='store_true', help='Only favorites; preserve catalog order')

    def selection(p):
        package(p)
        select = p.add_mutually_exclusive_group(required=True)
        select.add_argument('--id', action='append', help='Variant ID or package:variant ID; repeat for multiple sprites')
        select.add_argument('--ids-file', help='UTF-8 JSON array of IDs; - reads stdin')
        select.add_argument('--all', action='store_true', help='Explicitly select all matching sprites')
        filters(p)

    def options(p):
        p.add_argument('--format', choices=['png', 'gif', 'apng', 'mov'], help='Default: apng; PNG exports all frames unless --frame is set')
        p.add_argument('--scale', type=float, help='0.25–20, default 5; fractional values allowed')
        p.add_argument('--fps', type=float, help='0.1–120, default 3.75')

    command(commands, 'version', 'Show application and CLI contract versions')
    command(commands, 'schema', 'Describe commands, arguments, limits and exit codes for AI tools')
    command(commands, 'paths', 'Show resolved data and runtime paths without creating directories')
    packages = group('packages', 'List, import and manage immutable ZIP packages')
    command(packages, 'list', 'List installed packages and load errors')
    p = command(packages, 'info', 'Show package metadata'); package(p)
    p = command(packages, 'import', 'Validate and import a ZIP (idempotent)')
    p.add_argument('path', type=Path)
    p = command(packages, 'edit', 'Edit name/version/language without changing the source ZIP'); package(p)
    for field in ('name', 'version', 'language'):
        p.add_argument('--' + field, help='New value; version/language may be empty')
    p = command(packages, 'export', 'Save a ZIP with current metadata; never overwrite'); package(p)
    p.add_argument('--output', type=Path, required=True, help='Destination ZIP filename')
    p = command(packages, 'remove', 'Remove the managed ZIP only; keep settings and exports'); package(p)
    p.add_argument('--yes', action='store_true', help='Required explicit deletion confirmation')
    p = command(packages, 'create', 'Windows only: read game data and import a new package')
    p.add_argument('--game', type=Path, required=True, help='Game directory (never written)')
    p.add_argument('--kind', choices=['UT', 'DR'], required=True)
    p.add_argument('--name', required=True)
    p.add_argument('--version', default='')
    p.add_argument('--language', default='')
    p.add_argument('--extractor', type=Path, help='SpriteExtractor.exe or UndertaleModCli.exe; default bundled extractor')
    sprites = group('sprites', 'Search sprites or inspect their frames')
    p = command(sprites, 'list', 'Return a page of matching sprites'); package(p); filters(p)
    p.add_argument('--limit', type=int, default=50, help='1–1000, default 50')
    p.add_argument('--offset', type=int, default=0, help='Zero-based offset, default 0')
    p = command(sprites, 'info', 'Show a sprite and its package-relative frame paths'); package(p)
    p.add_argument('--id', required=True)
    favorites = group('favorites', 'Set favorites explicitly (no ambiguous toggle)')
    for action in ('add', 'remove'):
        p = command(favorites, action, action.capitalize() + ' favorites'); selection(p)
    presets = group('presets', 'Manage named export presets shared with the desktop')
    command(presets, 'list', 'List presets; no default preset is created')
    p = command(presets, 'save', 'Create a preset or replace one by ID'); options(p)
    p.add_argument('--name', required=True)
    p.add_argument('--id', help='Existing preset ID to update; omitted creates a new preset')
    p = command(presets, 'remove', 'Delete a preset')
    p.add_argument('--id', required=True)
    p.add_argument('--yes', action='store_true', help='Required explicit deletion confirmation')
    p = command(commands, 'export', 'Synchronously export sprites; exit after files and manifest are written')
    selection(p); options(p)
    p.add_argument('--preset', help='Exact preset ID; cannot combine with format/scale/fps overrides')
    p.add_argument('--frame', type=int, help='Zero-based frame, PNG only; omitted exports all PNG frames')
    p.add_argument('--original', action='store_true', help='Copy original PNG bytes; incompatible with encoding options')
    p.add_argument('--output', type=Path, help='Output base directory; does not change the saved desktop setting')
    p.add_argument('--dry-run', action='store_true', help='Validate selection/options and report duplicates without writing exports')
    p.add_argument('--allow-duplicate', action='store_true', help='Export again into a new directory when identical output exists')
    return root


def default_data():
    override = os.environ.get('UTDR_DATA_DIR')
    if override:
        path = Path(override).expanduser()
        if not path.is_absolute():
            raise CliError(2, 'UTDR_DATA_DIR must be an absolute path')
        return path.resolve()
    if not getattr(sys, 'frozen', False):
        return ROOT / 'data'
    if sys.platform == 'win32':
        return ROOT.parent / 'data' if ROOT.name == 'backend' else ROOT / 'data'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/UTdrSpriteLibrary'
    return Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'UTdrSpriteLibrary'


def describe(p):
    result = {'description': p.description, 'arguments': [], 'commands': {}}
    for a in p._actions:
        if isinstance(a, argparse._SubParsersAction):
            result['commands'] = {name: describe(sub) for name, sub in a.choices.items()}
        elif a.dest != 'help':
            result['arguments'].append({'name': a.dest, 'flags': a.option_strings,
                'required': a.required, 'help': a.help, 'choices': list(a.choices) if a.choices is not None else None,
                'default': None if a.default == argparse.SUPPRESS else a.default,
                'type': getattr(a.type, '__name__', 'boolean' if isinstance(a, argparse._StoreTrueAction) else 'string'),
                'repeatable': isinstance(a, argparse._AppendAction)})
    result['mutually_exclusive'] = [{'required': group.required, 'arguments': [a.dest for a in group._group_actions]}
                                    for group in p._mutually_exclusive_groups]
    return result


@contextmanager
def library(data):
    prefs = Preferences(data)
    store = LibraryStore(data / 'packages', prefs)
    try:
        yield store, prefs
    finally:
        store.close()


def resolve_id(store, pid, key):
    full = key if ':' in key else pid + ':' + key
    if full.split(':', 1)[0] != pid:
        raise CliError(2, 'All sprite IDs must belong to --package')
    try:
        return full, store.resolve(full)
    except (KeyError, ValueError):
        raise CliError(3, 'Sprite not found', {'id': key}) from None


def filtered(store, args):
    if args.chapter is not None and args.chapter < 1:
        raise CliError(2, '--chapter must be positive')
    return [v for v in store.summaries(args.package)
            if args.query.casefold() in v['name'].casefold()
            and (args.chapter is None or args.chapter in v['chapters'])
            and (not args.multi_frame or v['count'] > 1)
            and (not args.favorites or v['favorite'])]


def select(store, args):
    if not args.all and (args.query or args.chapter is not None or args.multi_frame or args.favorites):
        raise CliError(2, 'Filters require --all; explicit IDs are never silently filtered')
    if args.all:
        keys = [v['id'] for v in filtered(store, args)]
    elif args.ids_file:
        content = sys.stdin.read() if args.ids_file == '-' else Path(args.ids_file).read_text(encoding='utf-8-sig')
        keys = json.loads(content)
        if not isinstance(keys, list) or any(not isinstance(k, str) for k in keys):
            raise CliError(2, '--ids-file must contain a JSON array of ID strings')
    else:
        keys = args.id
    if not keys:
        raise CliError(3, 'No matching sprites')
    return list(dict.fromkeys(resolve_id(store, args.package, key)[0] for key in keys))


def preset(prefs, key):
    matches = [p for p in prefs.get('presets', []) if p['id'] == key]
    if not matches:
        raise CliError(3, 'Preset not found', {'id': key})
    return matches[0]


def export_options(args, prefs):
    overrides = {k: getattr(args, k) for k in ('format', 'scale', 'fps') if getattr(args, k) is not None}
    if getattr(args, 'original', False):
        if overrides or args.preset or args.frame is not None:
            raise CliError(2, '--original cannot be combined with encoding options, --frame or --preset')
        return {'format': 'png', 'scale': 1, 'fps': 3.75, 'original': True}
    if getattr(args, 'preset', None):
        if overrides:
            raise CliError(2, '--preset cannot be combined with --format, --scale or --fps')
        source = preset(prefs, args.preset)
        overrides = {k: source[k] for k in ('format', 'scale', 'fps') if k in source}
    values = {'format': 'apng', 'scale': 5, 'fps': 3.75} | overrides
    settings({}, values)
    if getattr(args, 'frame', None) is not None:
        if values['format'] != 'png' or args.frame < 0:
            raise CliError(2, '--frame requires --format png and a nonnegative index')
        values['frame_index'] = args.frame
    return values


def output_base(data, path):
    result = Path(path).expanduser().resolve()
    if any(result.is_relative_to(data / name) for name in ('packages', 'personal', 'cache', 'library')):
        raise CliError(2, 'Output must be separate from packages, personal settings and cache')
    return result


def validate_entries(entries, options):
    for _, v in entries:
        frames = v['frames']
        index = options.get('frame_index')
        if index is not None:
            if index >= len(frames):
                raise CliError(2, 'Frame index out of range', {'id': v['id'], 'frames': len(frames)})
            frames = [frames[index]]
        if not frames or any('image' not in f for f in frames):
            raise CliError(2, 'Sprite has missing bitmap frames', {'id': v['id']})
        if options.get('original'):
            continue
        if options['format'] != 'png' and len(frames) < 2:
            raise CliError(2, 'Animation export needs at least two frames; use PNG or --multi-frame', {'id': v['id']})
        scale = options['scale']
        sizes = [(max(1, round(f['width'] * scale)), max(1, round(f['height'] * scale))) for f in frames]
        pixels = (max(w for w, _ in sizes) * max(h for _, h in sizes) * len(frames)
                  if options['format'] != 'png' else max(w * h for w, h in sizes))
        if pixels > 40_000_000:
            raise CliError(2, 'Export exceeds 40 million frame-pixels; reduce scale', {'id': v['id']})


def create_package(store, args, data):
    if sys.platform != 'win32':
        raise CliError(2, 'Game extraction is currently Windows-only; use packages import with a ZIP')
    game = args.game.expanduser().resolve()
    if data.is_relative_to(game):
        raise CliError(2, 'Data directory must be outside the game directory')
    if not args.name.strip() or len(args.name.strip()) > 120 or max(len(args.version), len(args.language)) > 500:
        raise CliError(2, 'Name must be 1–120 characters; version/language at most 500')
    bundled = ROOT / 'extractor/SpriteExtractor.exe'
    if not bundled.is_file():
        bundled = ROOT / ('umt/UndertaleModCli.exe' if getattr(sys, 'frozen', False) else 'vendor/umt/0.9.2.0/UndertaleModCli.exe')
    tool = (args.extractor or bundled).expanduser().resolve()
    if not tool.is_file():
        raise CliError(3, 'Extractor not found; specify --extractor')
    cache = data / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cli-import-', dir=cache) as temp:
        work = Path(temp)
        evidence = extract(game, tool, work / 'extracted', args.kind, args.version,
                           progress=lambda message: print(message, file=sys.stderr, flush=True))
        metadata = {'game': args.kind, 'name': args.name.strip(), 'version': args.version, 'language': args.language,
            'sources': [{'file': Path(p).parent.name + '/' + Path(p).name, 'sha256': digest} for p, digest in evidence['inputs'].items()],
            'extractor': {k: evidence[k] for k in ('umt_sha256', 'export_script_sha256', 'extractor_sha256', 'umt_library_sha256') if k in evidence}}
        source = make_package(work / 'extracted', work / 'package.zip', metadata)
        pid, duplicate = store.import_zip(source)
    return {'package': store.metadata(pid) | {'id': pid}, 'duplicate': duplicate}


def run(args, root):
    if args.command == 'version':
        return {'version': VERSION, 'cli_schema': CONTRACT, 'platform': sys.platform}
    if args.command == 'schema':
        return {'cli_schema': CONTRACT, 'commands': describe(root)['commands'],
                'global_arguments': describe(root)['arguments'], 'exit_codes': EXIT_CODES,
                'limits': {'scale': [0.25, 20], 'fps': [0.1, 120], 'page_size': [1, 1000], 'frame_index_base': 0},
                'result': {'schema_version': 1, 'ok': 'boolean', 'command': 'string', 'data': 'success payload',
                           'error': {'code': 'stable string', 'message': 'human readable', 'details': 'optional object'}},
                'notes': ['Commands never prompt or open a GUI.', '--json works before or after subcommands.',
                          'Use IDs, not display names. Filters require --all for mutations/exports.',
                          '--help is text; use schema --json for machine discovery.',
                          'Game extraction is Windows-only. --dry-run validates but does not encode files.']}
    data = args.data.expanduser().resolve() if hasattr(args, 'data') else default_data()
    if args.command == 'paths':
        return {'data': str(data), 'runtime': str(ROOT), 'packages': str(data / 'packages'), 'game_import': sys.platform == 'win32'}
    # Check before Preferences/LibraryStore create any directories inside a game.
    if args.command == 'packages' and args.action == 'create' and data.is_relative_to(args.game.expanduser().resolve()):
        raise CliError(2, 'Data directory must be outside the game directory')
    with library(data) as (store, prefs):
        if hasattr(args, 'package') and args.package not in store.packages:
            raise CliError(3, 'Package not found', {'id': args.package, 'load_errors': store.errors})
        if args.command == 'packages':
            if args.action == 'list':
                return {'packages': store.list(), 'load_errors': store.errors, 'data_dir': str(data)}
            if args.action == 'import':
                try:
                    pid, duplicate = store.import_zip(args.path.expanduser().resolve())
                except (KeyError, TypeError, zipfile.BadZipFile) as error:
                    raise CliError(2, 'Invalid package: ' + str(error)) from None
                return {'package': store.metadata(pid) | {'id': pid}, 'duplicate': duplicate}
            if args.action == 'create':
                return create_package(store, args, data)
            if args.action == 'info':
                return next(p for p in store.list() if p['id'] == args.package)
            if args.action == 'edit':
                values = {k: getattr(args, k) for k in ('name', 'version', 'language') if getattr(args, k) is not None}
                if not values:
                    raise CliError(2, 'Supply at least one of --name, --version, --language')
                store.edit_metadata(args.package, values)
                return store.metadata(args.package) | {'id': args.package}
            if args.action == 'export':
                out = args.output.expanduser().resolve()
                if out.suffix.lower() != '.zip':
                    raise CliError(2, '--output must end in .zip')
                output_base(data, out.parent).mkdir(parents=True, exist_ok=True)
                store.export_package(args.package, out)
                return {'file': str(out)}
            if not args.yes:
                raise CliError(4, 'Deletion requires --yes; exports and personal settings will be kept')
            try:
                store.remove(args.package)
            except ValueError as error:
                raise CliError(4, str(error)) from None
            return {'removed': args.package}
        if args.command == 'sprites':
            if args.action == 'info':
                key, (_, variant) = resolve_id(store, args.package, args.id)
                return variant | {'id': key, 'package_id': args.package, 'favorite': key in prefs.get('favorites', [])}
            if not 1 <= args.limit <= 1000 or args.offset < 0:
                raise CliError(2, '--limit must be 1–1000; --offset must be nonnegative')
            items = filtered(store, args)
            end = args.offset + args.limit
            return {'items': items[args.offset:end], 'total': len(items), 'offset': args.offset,
                    'limit': args.limit, 'next_offset': end if end < len(items) else None}
        if args.command == 'favorites':
            keys = select(store, args)
            prefs.favorites(keys, args.action == 'add')
            return {'ids': keys, 'favorite': args.action == 'add', 'count': len(keys)}
        if args.command == 'presets':
            items = prefs.get('presets', [])
            if args.action == 'list':
                return {'presets': items}
            if args.action == 'remove':
                preset(prefs, args.id)
                if not args.yes:
                    raise CliError(4, 'Deletion requires --yes')
                prefs.set('presets', [p for p in items if p['id'] != args.id])
                return {'removed': args.id}
            values = export_options(args, prefs)
            if not args.name.strip() or len(args.name.strip()) > 120:
                raise CliError(2, 'Preset name must be 1–120 characters')
            if args.id:
                current = preset(prefs, args.id)
                values = {k: (getattr(args, k) if getattr(args, k) is not None else current.get(k, values[k]))
                          for k in ('format', 'scale', 'fps')}
                settings({}, values)
            elif len(items) >= 200:
                raise CliError(2, 'At most 200 presets')
            result = values | {'name': args.name.strip(), 'id': args.id or uuid.uuid4().hex}
            prefs.set('presets', [result if p['id'] == args.id else p for p in items] if args.id else items + [result])
            return result
        if args.command == 'export':
            keys = select(store, args)
            entries = named_entries([store.resolve(k) for k in keys])
            options = export_options(args, prefs)
            validate_entries(entries, options)
            destination = output_base(data, args.output if args.output is not None else prefs.output_dir)
            category = destination / (label(store.metadata(args.package)['name']) + '_' + args.package[:12])
            fingerprint = signature(entries, options)
            duplicate = find_duplicate(category, fingerprint)
            plan = {'ids': keys, 'count': len(keys), 'options': options, 'output_base': str(destination), 'duplicate': duplicate}
            if args.dry_run:
                return plan | {'dry_run': True}
            if duplicate and not args.allow_duplicate:
                raise CliError(4, 'Identical export already exists; use its files or pass --allow-duplicate', duplicate)
            folder = category / 'normal' / (datetime.now().strftime('%Y%m%d-%H%M%S') + '_' + uuid.uuid4().hex[:12])
            manifest = export_batch(store, entries, options, folder, fingerprint)
            result = {'folder': str(folder), 'manifest': str(folder / 'manifest.json'),
                      'success': len(manifest['records']), 'failed': len(manifest['errors']),
                      'files': [str(folder / name) for name in manifest['file_hashes']], 'errors': manifest['errors']}
            if manifest['cancelled']:
                raise CliError(130, 'Export cancelled; completed files are retained', result)
            if manifest['errors']:
                raise CliError(6, 'Some exports failed; completed files are retained', result)
            return result
    raise CliError(2, 'Unknown command')


def human_result(command, data):
    if command == 'packages list':
        print(f"{len(data['packages'])} 个素材包 · {data['data_dir']}")
        for p in data['packages']:
            print(f"{p['name']} · {p['game']} · {p['version']} · {p['count']} 个精灵\n  {p['id']}")
        for error in data['load_errors']:
            print('无法加载：' + error, file=sys.stderr)
    elif command == 'sprites list':
        print(f"匹配 {data['total']} 项 · 偏移 {data['offset']} · 本次 {len(data['items'])} 项")
        for v in data['items']:
            chapter = '/'.join(map(str, v['chapters'])) or 'UT'
            print(f"{'★' if v['favorite'] else ' '} {v['name']} · Ch {chapter} · {v['count']} 帧\n  {v['id']}")
        if data['next_offset'] is not None:
            print(f"下一页：--offset {data['next_offset']}")
    elif command == 'presets list':
        print(f"{len(data['presets'])} 个预设")
        for p in data['presets']:
            print(f"{p['name']} · {p.get('format', 'apng')} · {p.get('scale', 5)}× · {p.get('fps', 3.75)} FPS\n  {p['id']}")
    elif command == 'export' and not data.get('dry_run'):
        print(f"已导出 {data['success']} 项 · {len(data['files'])} 个文件\n{data['folder']}")
        for path in data['files']:
            print(path)
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = '--json' in argv
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    root = parser()
    name = ''
    try:
        args = root.parse_args(argv)
        name = args.command + (' ' + args.action if hasattr(args, 'action') else '')
        result = {'schema_version': CONTRACT, 'ok': True, 'command': name, 'data': run(args, root)}
        serialized = json.dumps(result, ensure_ascii=False, allow_nan=False)
        code = 0
    except (Exception, KeyboardInterrupt) as error:
        if isinstance(error, CliError):
            code, details = error.code, error.details
        else:
            code = (130 if isinstance(error, (KeyboardInterrupt, InterruptedError)) else
                    3 if isinstance(error, FileNotFoundError) else
                    4 if isinstance(error, FileExistsError) else
                    2 if isinstance(error, (ValueError, zipfile.BadZipFile)) else
                    5 if isinstance(error, (OSError, sqlite3.Error)) else 1)
            details = None
        result = {'schema_version': CONTRACT, 'ok': False, 'command': name,
                  'error': {'code': EXIT_CODES[code], 'message': str(error) or EXIT_CODES[code], 'details': details}}
        serialized = json.dumps(result, ensure_ascii=False, allow_nan=False)
    if as_json:
        print(serialized)
    elif code:
        print(f"{result['error']['code']}: {result['error']['message']}", file=sys.stderr)
        if result['error']['details'] is not None:
            print(json.dumps(result['error']['details'], ensure_ascii=False, indent=2), file=sys.stderr)
    else:
        human_result(name, result['data'])
    return code


def entry():
    def interrupt(signum, frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, interrupt)
    return main()


if __name__ == '__main__':
    sys.exit(entry())
