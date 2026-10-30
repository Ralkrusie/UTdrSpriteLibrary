"""UT/DR package format v1. ZIPs are immutable; user data lives elsewhere."""
import copy
import hashlib
import io
import json
import re
import shutil
import threading
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from PIL import Image


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def image_name(name):
    if not isinstance(name, str) or not re.fullmatch(r'images/[A-Za-z0-9_./-]+\.png', name):
        raise ValueError('无效图片路径')
    if '..' in PurePosixPath(name).parts or str(PurePosixPath(name)) != name:
        raise ValueError('无效图片路径')
    return name


def open_image(source, name):
    if isinstance(source, Package):
        return Image.open(io.BytesIO(source.read(name)))
    file = (Path(source) / image_name(name)).resolve()
    if not file.is_relative_to((Path(source) / 'images').resolve()):
        raise ValueError('无效图片路径')
    return Image.open(file)


class Package:
    def __init__(self, path, verify=False, cancel=lambda: False):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.zip = zipfile.ZipFile(path)
        try:
            infos = self.zip.infolist()
            names = {i.filename for i in infos}
            if len(names) != len(infos) or len(names) > 250000:
                raise ValueError('ZIP 存在重复条目或条目过多')
            for i in infos:
                if i.filename not in ('manifest.json', 'catalog.json'):
                    image_name(i.filename)
                limit = 64 * 1024 * 1024 if i.filename == 'catalog.json' else 16 * 1024 * 1024
                if i.file_size > limit or i.flag_bits & 1:
                    raise ValueError('ZIP 条目过大或已加密')
            if sum(i.file_size for i in infos) > 8 * 1024**3:
                raise ValueError('素材包超过 8 GiB')
            self.metadata = json.loads(self.zip.read('manifest.json'))
            m = self.metadata
            if m.get('format') != 'UTdrSpriteLibrary' or m.get('schema') != 1 or m.get('game') not in ('UT', 'DR'):
                raise ValueError('不是支持的 UT／DR 素材包（格式版本 1）')
            for key in ('name', 'version', 'language'):
                if not isinstance(m.get(key), str) or len(m[key]) > 500:
                    raise ValueError('素材包信息不完整')
            if not m['name'].strip() or not isinstance(m.get('sources'), list):
                raise ValueError('素材包缺少名称或来源摘要')
            for source in m['sources']:
                if not isinstance(source.get('file'), str) or not re.fullmatch('[0-9a-f]{64}', source.get('sha256', '')):
                    raise ValueError('无效来源摘要')
            catalog = json.loads(self.zip.read('catalog.json'))
            self.variants = {}
            refs = {}
            for group in catalog['items']:
                if group['kind'] != 'sprite':
                    continue
                for v in group['variants']:
                    if not re.fullmatch('[0-9a-f]{64}', v['id']) or v['id'] in self.variants:
                        raise ValueError('素材条目标识无效或重复')
                    if not isinstance(v['name'], str) or not isinstance(v['chapters'], list):
                        raise ValueError('素材条目信息无效')
                    if any(type(ch) is not int or ch < 1 for ch in v['chapters']):
                        raise ValueError('章节无效')
                    if len(v['frames']) > 10000:
                        raise ValueError('素材帧数过多')
                    for f in v['frames']:
                        if 'image' in f:
                            name = image_name(f['image'])
                            if name not in names:
                                raise ValueError('素材包缺帧：' + name)
                            if any(type(f.get(k)) is not int or not 1 <= f[k] <= 32768 for k in ('width', 'height')):
                                raise ValueError('帧尺寸无效')
                            shape = (f['width'], f['height'])
                            if name in refs and refs[name] != shape:
                                raise ValueError('帧尺寸记录冲突')
                            refs[name] = shape
                    self.variants[v['id']] = v
            if not self.variants:
                raise ValueError('素材包没有精灵条目')
            digest = hashlib.sha256()
            if verify:
                for name in sorted(names):
                    if cancel():raise InterruptedError('已取消导入')
                    digest.update(name.encode() + b'\0')
                    data = self.zip.read(name)
                    digest.update(hashlib.sha256(data).digest())
                    if name in refs:
                        with Image.open(io.BytesIO(data)) as im:
                            if im.format != 'PNG' or im.size != refs[name]:
                                raise ValueError('PNG 尺寸与索引不一致')
                            im.verify()
            self.id = digest.hexdigest() if verify else self.path.stem
        except BaseException:
            self.zip.close()
            raise

    def read(self, name):
        image_name(name)
        with self.lock:
            return self.zip.read(name)

    def close(self):
        self.zip.close()


def make_package(source, out, metadata, cancel=lambda: False):
    source, out = Path(source), Path(out)
    catalog = json.loads((source / 'catalog.json').read_text(encoding='utf-8'))
    names = sorted({image_name(f['image']) for g in catalog['items'] for v in g['variants'] for f in v['frames'] if 'image' in f})
    with zipfile.ZipFile(out, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        z.writestr('manifest.json', json.dumps({'format': 'UTdrSpriteLibrary', 'schema': 1, **metadata}, ensure_ascii=False))
        z.writestr('catalog.json', json.dumps(catalog, ensure_ascii=False, separators=(',', ':')))
        for name in names:
            if cancel():raise InterruptedError('已取消导入')
            file = (source / name).resolve()
            if not file.is_relative_to((source / 'images').resolve()):
                raise ValueError('图片位于素材目录以外')
            z.write(file, name)
    return out


class LibraryStore:
    def __init__(self, root, prefs):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.prefs = prefs
        self.packages = {}
        self.errors = []
        for file in self.root.glob('*.zip'):
            try:
                if not re.fullmatch('[0-9a-f]{64}', file.stem):
                    continue
                self.packages[file.stem] = Package(file)
            except Exception as error:
                self.errors.append(file.name + ': ' + str(error))

    def import_zip(self, source, cancel=lambda: False):
        temp = self.root / ('.import-' + uuid.uuid4().hex)
        try:
            shutil.copyfile(source, temp)
            package = Package(temp, verify=True, cancel=cancel)
            pid = package.id
            package.close()
            if pid in self.packages:
                return pid, True
            if cancel():raise InterruptedError('已取消导入')
            target = self.root / (pid + '.zip')
            try:
                temp.rename(target)
            except FileExistsError:
                pass
            self.packages[pid] = Package(target)
            return pid, False
        finally:
            temp.unlink(missing_ok=True)

    def metadata(self, pid):
        p = self.packages[pid]
        return p.metadata | {'name': self.prefs.get('name:' + pid, p.metadata['name'])} | self.prefs.get('metadata:' + pid, {})

    def edit_metadata(self, pid, values):
        metadata = self.metadata(pid)
        for key, limit in (('name', 120), ('version', 500), ('language', 500)):
            value = values.get(key, metadata[key])
            if not isinstance(value, str) or len(value.strip()) > limit or (key == 'name' and not value.strip()):
                raise ValueError('名称不能为空，名称最多 120 字，版本及语言说明最多 500 字')
            metadata[key] = value.strip()
        self.prefs.set('metadata:' + pid, {k: metadata[k] for k in ('name', 'version', 'language')})

    def export_package(self, pid, out):
        p = self.packages[pid]
        out = Path(out)
        # Exclusive creation preserves existing exports and the managed source ZIP.
        with out.open('xb') as stream:
            try:
                with zipfile.ZipFile(stream, 'w') as dest, p.lock:
                    for entry in p.zip.infolist():
                        data = (json.dumps(self.metadata(pid), ensure_ascii=False).encode('utf-8')
                                if entry.filename == 'manifest.json' else p.zip.read(entry.filename))
                        dest.writestr(copy.copy(entry), data)
            except BaseException:
                stream.close()
                out.unlink(missing_ok=True)
                raise

    def list(self):
        return [self.metadata(pid) | {'id': pid,
                'count': len(p.variants), 'chapters': sorted({ch for v in p.variants.values() for ch in v['chapters']})}
                for pid, p in self.packages.items()]

    def remove(self, pid):
        p = self.packages[pid]
        p.close()
        try:
            p.path.unlink()
        except OSError:
            self.packages[pid] = Package(p.path)
            raise ValueError('素材包正被其他实例使用，请关闭该实例后重试')
        del self.packages[pid]

    def resolve(self, key):
        pid, vid = key.split(':', 1)
        p = self.packages[pid]
        return p, p.variants[vid]

    def public_variant(self, pid, v):
        return v | {'id': pid + ':' + v['id'], 'package_id': pid,
                    'frames': [f | ({'image': f'images/{pid}/' + f['image'][7:]} if 'image' in f else {}) for f in v['frames']]}

    def summaries(self, pid):
        p = self.packages.get(pid)
        if p is None:
            return []
        favorites = set(self.prefs.get('favorites', []))
        return [{k: v.get(k) for k in ('name', 'chapters', 'width', 'height', 'speed', 'speed_type')} |
                {'id': pid + ':' + v['id'], 'count': len(v['frames']),
                 'favorite': pid + ':' + v['id'] in favorites,
                 'complete': bool(v['frames']) and all('image' in f for f in v['frames']),
                 'thumbnail': next((f'images/{pid}/' + f['image'][7:] for f in v['frames'] if 'image' in f), None)}
                for v in p.variants.values()]

    def close(self):
        for p in self.packages.values():
            p.close()
