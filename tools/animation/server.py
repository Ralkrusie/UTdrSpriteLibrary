"""Local-only UT/DR package browser and queued exporter."""
import argparse
import json
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import threading
import uuid
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from encoder import encode, encode_png, export_filename, settings
from export_files import named_entries, signature, file_hashes, find_duplicate
from import_game import extract
from library import LibraryStore, make_package, sha
from lifecycle import bind_to_parent
from preferences import Preferences

FROZEN = getattr(sys, 'frozen', False)
ROOT = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parents[2]
UI = Path(__file__).resolve().parent


def open_folder(folder):
    if sys.platform == 'win32':
        os.startfile(str(folder))
    else:
        subprocess.run(['/usr/bin/open' if sys.platform == 'darwin' else 'xdg-open', str(folder)], check=True)


def label(value):
    return re.sub(r'[^\w.-]', '_', value)[:70].strip('.') or 'library'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=ROOT / 'data')
    parser.add_argument('--library', type=Path, default=ROOT / 'library', help='Optional legacy migration source')
    parser.add_argument('--port', type=int, default=8896)
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--auto-port', action='store_true')
    parser.add_argument('--ready-file', type=Path)
    parser.add_argument('--cache', type=Path, help='Instance-owned temporary working directory')
    parser.add_argument('--parent-pid', type=int)
    args = parser.parse_args()
    bind_to_parent(args.parent_pid)
    if FROZEN and len(sys.argv) == 1:
        args.open = True
        args.auto_port = True
    data = args.data.resolve()
    prefs = Preferences(data)
    store = LibraryStore(data / 'packages', prefs)
    cache = args.cache.resolve() if args.cache else data / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    jobs = {}
    lock = threading.RLock()
    pool = ThreadPoolExecutor(max_workers=1)
    bundled_umt = ROOT / 'umt' / 'UndertaleModCli.exe'
    if not FROZEN:
        bundled_umt = ROOT / 'vendor' / 'umt' / '0.9.2.0' / 'UndertaleModCli.exe'
    dedicated = ROOT / 'extractor' / 'SpriteExtractor.exe'
    if dedicated.is_file():
        bundled_umt = dedicated

    def busy():
        return any(j['state'] in ('queued', 'running') for j in jobs.values())

    def info():
        packages = store.list()
        selected = prefs.get('selected', '')
        if selected not in store.packages:
            selected = packages[0]['id'] if packages else ''
        return {'packages': packages, 'selected': selected, 'errors': store.errors,
                'legacy': (args.library / 'catalog.json').is_file(),
                'umt': str(bundled_umt) if bundled_umt.is_file() else ''}

    def new_job(kind):
        if busy():
            raise ValueError('已有任务，请等待完成或取消')
        jid = uuid.uuid4().hex
        jobs[jid] = {'id': jid, 'kind': kind, 'state': 'queued', 'cancel': False,
                     'done': 0, 'total': 1, 'success': 0, 'errors': 0, 'current': ''}
        return jobs[jid]

    def guarded(job, action):
        job['state'] = 'running'
        try:
            action()
            job['state'] = 'cancelled' if job['cancel'] else 'done'
        except InterruptedError:
            job.update(state='cancelled', current='已取消')
        except Exception as error:
            job.update(state='failed', errors=1, current=str(error))

    def import_package(job, body):
        def progress(message):
            job['current'] = message
        with tempfile.TemporaryDirectory(prefix='import-', dir=cache) as temp:
            work = Path(temp)
            mode = body.get('mode', 'zip')
            if mode == 'zip':
                source = Path(body['path']).resolve()
            else:
                kind = body.get('game')
                name = str(body.get('name', '')).strip()
                if kind not in ('UT', 'DR') or not name:
                    raise ValueError('请选择游戏并填写素材包名称')
                version = str(body.get('version', '')).strip()
                language = str(body.get('language', '')).strip()
                if mode == 'game':
                    game = Path(body['path']).resolve()
                    if data.is_relative_to(game):
                        raise ValueError('游戏目录与工具数据目录必须分开')
                    umt = Path(body.get('umt') or bundled_umt).resolve()
                    if not umt.is_file():
                        raise ValueError('请指定 SpriteExtractor.exe 或 UndertaleModCli.exe')
                    extracted = work / 'extracted'
                    evidence = extract(game, umt, extracted, kind, version, progress, lambda: job['cancel'])
                elif mode == 'legacy':
                    extracted = args.library.resolve()
                    evidence = json.loads((extracted / 'provenance.json').read_text(encoding='utf-8')) if (extracted / 'provenance.json').exists() else {'inputs': {}}
                else:
                    raise ValueError('无效导入方式')
                sources = [{'file': Path(p).parent.name + '/' + Path(p).name, 'sha256': digest} for p, digest in evidence['inputs'].items()]
                source = make_package(extracted, work / 'package.zip', {'game': kind, 'name': name,
                    'version': version, 'language': language, 'sources': sources,
                    'extractor': {k: evidence[k] for k in ('umt_sha256', 'export_script_sha256', 'extractor_sha256', 'umt_library_sha256') if k in evidence}}, cancel=lambda: job['cancel'])
            if job['cancel']:
                raise InterruptedError()
            progress('正在校验并导入素材包…')
            with lock:
                pid, duplicate = store.import_zip(source, cancel=lambda: job['cancel'])
                prefs.set('selected', pid)
            job.update(done=1, success=1, package_id=pid, current='素材包已存在' if duplicate else '已导入')

    def export(job, entries, options):
        folder = Path(job['folder'])
        folder.mkdir(parents=True, exist_ok=False)
        records, failures = [], []
        for package, v in entries:
            if job['cancel']:
                break
            job['current'] = v['name']
            try:
                if options.get('original'):
                    files = []
                    for i, f in enumerate(v['frames']):
                        if job['cancel']:
                            raise InterruptedError()
                        if 'image' not in f:
                            raise ValueError('素材帧不完整')
                        name = export_filename(v, options) + f'_{i:04d}.png'
                        (folder / name).write_bytes(package.read(f['image']))
                        files.append({'file': name, 'frame': i, 'size': [f['width'], f['height']]})
                    record = {'name': v['name'], 'variant': v['id'], 'format': 'png', 'original': True, 'files': files}
                elif options['format'] == 'png':
                    record = encode_png(package, v, folder, options, lambda: job['cancel'])
                else:
                    out = folder / (export_filename(v, options) + {'gif': '.gif', 'mov': '.mov', 'apng': '.png'}[options['format']])
                    record = encode(package, v, out, options, lambda: job['cancel']) | {'file': out.name}
                records.append(record | {'package_id': package.id, 'chapters': v['chapters']})
            except InterruptedError:
                break
            except Exception as error:
                failures.append({'name': v['name'], 'variant': v['id'], 'error': str(error)})
            job.update(done=job['done'] + 1, success=len(records), errors=len(failures))
        package = entries[0][0]
        manifest = {'package': store.metadata(package.id) | {'id': package.id},
                    'options': options, 'records': records, 'errors': failures, 'cancelled': job['cancel']}
        manifest.update(signature=job['signature'], file_hashes=file_hashes(folder, records))
        (folder / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        job['current'] = '；'.join(f['error'] for f in failures[:3])
        if options.get('original') and not failures and not job['cancel'] and options.get('open', True):
            open_folder(folder)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def bytes(self, content, mime, status=200):
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            try:
                self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def reply(self, obj, status=200):
            self.bytes(json.dumps(obj, ensure_ascii=False).encode(), 'application/json; charset=utf-8', status)

        def safe(self):
            host, origin = self.headers.get('Host', ''), self.headers.get('Origin')
            return host in (f'127.0.0.1:{args.port}', f'localhost:{args.port}') and (not origin or origin == f'http://{host}')

        def do_GET(self):
            if not self.safe():
                return self.reply({'error': 'Invalid origin'}, 403)
            url = urlparse(self.path)
            path = unquote(url.path)
            try:
                if path == '/api/libraries':
                    with lock:
                        return self.reply(info())
                if path == '/api/catalog':
                    pid = parse_qs(url.query).get('package', [prefs.get('selected', '')])[0]
                    with lock:
                        return self.reply(store.summaries(pid))
                if path == '/api/settings':
                    return self.reply({'output_dir': prefs.output_dir, 'presets': prefs.get('presets', []), 'card_width': prefs.get('card_width', 230), 'view_options': prefs.get('view_options', {})})
                if path.startswith('/api/variant/'):
                    with lock:
                        package, v = store.resolve(path.rsplit('/', 1)[-1])
                        return self.reply(store.public_variant(package.id, v))
                if path.startswith('/api/job/'):
                    return self.reply(dict(jobs[path.rsplit('/', 1)[-1]]))
                if path.startswith('/images/'):
                    _, _, pid, relative = path.split('/', 3)
                    with lock:
                        return self.bytes(store.packages[pid].read('images/' + relative), 'image/png')
                if path == '/ui-title.svg':
                    file = UI / 'ui-assets/fnt-main-title.svg' if FROZEN else ROOT / 'assets/ui/fnt-main-title.svg'
                    return self.bytes(file.read_bytes(), 'image/svg+xml')
                if path == '/ui-heart.png':
                    file = UI / 'ui-assets/spr_dodgeheart_0.png' if FROZEN else ROOT / 'assets/ui/spr_dodgeheart_0.png'
                    return self.bytes(file.read_bytes(), 'image/png')
                if path in ('/', '/app.js', '/style.css', '/drag-ui.js', '/library-ui.js'):
                    file = UI / ('index.html' if path == '/' else path[1:])
                    if not file.exists() and path == '/drag-ui.js':
                        file = UI.parent / 'desktop' / 'drag-ui.js'
                    return self.bytes(file.read_bytes(), mimetypes.guess_type(file.name)[0] or 'text/plain')
                return self.reply({'error': 'Not found'}, 404)
            except (ValueError, KeyError, OSError) as error:
                return self.reply({'error': str(error)}, 404)

        def do_POST(self):
            if not self.safe():
                return self.reply({'error': 'Invalid origin'}, 403)
            try:
                n = int(self.headers.get('Content-Length', '0'))
                if not 0 < n <= 5_000_000:
                    raise ValueError('Invalid request length')
                body = json.loads(self.rfile.read(n))
                route = self.path
                if route == '/api/validate-output':
                    return self.reply({'output_dir': prefs.set_output(body['output_dir'], False)})
                if route == '/api/settings':
                    if 'view_options' in body:
                        views = body['view_options']
                        if not isinstance(views, dict) or set(views) - {'batch', 'detail'}:
                            raise ValueError('Invalid view settings')
                        for key, value in views.items():
                            if not isinstance(value, dict) or value.get('format') not in ('png', 'png-all', 'gif', 'apng', 'mov'):
                                raise ValueError('Invalid export settings')
                            settings({}, dict(value, format='png' if value['format']=='png-all' else value['format']))
                        prefs.set('view_options', prefs.get('view_options', {}) | views)
                    if 'card_width' in body:
                        width = body['card_width']
                        if type(width) is not int or not 180 <= width <= 360:
                            raise ValueError('卡片宽度范围为 180–360 px')
                        prefs.set('card_width', width)
                    if 'output_dir' in body:
                        prefs.set_output(body['output_dir'])
                    if 'presets' in body:
                        presets = body['presets']
                        if not isinstance(presets, list) or len(presets) > 200:
                            raise ValueError('预设数量无效')
                        for p in presets:
                            settings({}, p)
                            if not isinstance(p.get('id'), str) or not str(p.get('name', '')).strip():
                                raise ValueError('预设名称无效')
                        prefs.set('presets', presets)
                    return self.reply({'output_dir': prefs.output_dir, 'presets': prefs.get('presets', []), 'card_width': prefs.get('card_width', 230), 'view_options': prefs.get('view_options', {})})
                if route == '/api/favorite':
                    with lock:
                        ids = body.get('ids', [body.get('id')])
                        if not isinstance(ids, list) or not ids:
                            raise ValueError('请选择素材')
                        for key in ids:
                            store.resolve(key)
                        prefs.favorites(ids, bool(body['enabled']))
                    return self.reply({'ok': True})
                if route in ('/api/library/select', '/api/library/rename', '/api/library/metadata', '/api/library/delete'):
                    with lock:
                        pid = body['id']
                        if pid not in store.packages:
                            raise ValueError('素材包不存在')
                        if route.endswith('/select'):
                            prefs.set('selected', pid)
                        elif route.endswith(('/rename', '/metadata')):
                            store.edit_metadata(pid, body)
                        else:
                            if busy():
                                raise ValueError('任务完成后才能删除素材包')
                            store.remove(pid)
                        return self.reply(info())
                if route == '/api/library/import':
                    with lock:
                        job = new_job('import')
                        pool.submit(guarded, job, lambda: import_package(job, body))
                    return self.reply({'id': job['id']})
                if route in ('/api/library/export-path', '/api/library/save'):
                    with lock:
                        pid = body['id']
                        metadata = store.metadata(pid)
                        destination = Path(prefs.output_dir)
                        folder = destination / (label(metadata['name']) + '_' + pid[:12])
                        if route.endswith('/export-path'):
                            folder.mkdir(parents=True, exist_ok=True)
                            return self.reply({'file': str(folder / (label(metadata['name']) + '.zip'))})
                        out = Path(body['path']).expanduser()
                        if not out.is_absolute():
                            raise ValueError('请选择完整的导出文件路径')
                        if out.suffix.lower() != '.zip':
                            out = out.with_name(out.name + '.zip')
                        prefs.set_output(str(out.parent), remember=False)
                        store.export_package(pid, out)
                    return self.reply({'file': str(out)})
                if route == '/api/open-export':
                    job = jobs.get(body.get('id'))
                    if body.get('id') and not job:
                        raise ValueError('找不到此导出记录')
                    folder = Path(job['folder'] if job else prefs.output_dir)
                    folder.mkdir(parents=True, exist_ok=True)
                    open_folder(folder)
                    return self.reply({'folder': str(folder)})
                if route in ('/api/export', '/api/open-folder'):
                    with lock:
                        ids = list(dict.fromkeys(body['ids'] if route == '/api/export' else [body['id']]))
                        if not ids:
                            raise ValueError('请勾选素材')
                        entries = named_entries([store.resolve(key) for key in ids])
                        package = entries[0][0]
                        if any(p.id != package.id for p, _ in entries):
                            raise ValueError('一次导出请选择同一素材包')
                        options = body['options'] if route == '/api/export' else {'format': 'png', 'scale': 1, 'fps': 3.75, 'original': True}
                        for _, v in entries:
                            settings(v, options)
                        destination = Path(prefs.set_output(body.get('output_dir', prefs.output_dir), body.get('remember_output', True) is not False))
                        category = label(store.metadata(package.id)['name']) + '_' + package.id[:12]
                        fingerprint = signature(entries, options)
                        if body.get('allow_duplicate') is not True:
                            duplicate = find_duplicate(destination / category, fingerprint)
                            if duplicate:
                                return self.reply({'duplicate': duplicate})
                        job = new_job('export')
                        folder = destination / category / 'normal' / (datetime.now().strftime('%Y%m%d-%H%M%S') + '_' + job['id'][:12])
                        job.update(total=len(ids), folder=str(folder), category=category, options=options, ids=ids, signature=fingerprint)
                        pool.submit(guarded, job, lambda: export(job, entries, options))
                    return self.reply({'id': job['id']})
                if route == '/api/cancel':
                    jobs[body['id']]['cancel'] = True
                    return self.reply({'ok': True})
                return self.reply({'error': 'Not found'}, 404)
            except (ValueError, KeyError, TypeError, OSError) as error:
                return self.reply({'error': str(error)}, 400)

    class LocalServer(ThreadingHTTPServer):
        allow_reuse_address = False
    for attempt in range(20 if args.auto_port else 1):
        try:
            server = LocalServer(('127.0.0.1', args.port), Handler)
            args.port = server.server_address[1]
            break
        except OSError:
            if not args.auto_port or attempt == 19:
                raise
            args.port += 1
    url = f'http://127.0.0.1:{args.port}/'
    if args.ready_file:
        temp = args.ready_file.with_suffix('.tmp')
        temp.write_text(json.dumps({'url': url, 'pid': os.getpid()}), encoding='utf-8')
        temp.replace(args.ready_file)
    if sys.stdout:
        print('Animation library: ' + url, flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for job in jobs.values():
            job['cancel'] = True
        server.server_close()
        pool.shutdown(wait=True)
        store.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        if '--ready-file' in sys.argv:
            Path(sys.argv[sys.argv.index('--ready-file') + 1]).write_text(json.dumps({'error': str(error)}), encoding='utf-8')
            sys.exit(1)
        raise
