"""Personal data is separate from immutable packages and exported files."""
import json
import sqlite3
import threading
from pathlib import Path

class Preferences:
    def __init__(self, root):
        self.root = Path(root).resolve()
        personal = self.root / 'personal'
        personal.mkdir(parents=True, exist_ok=True)
        self.file = personal / 'settings.sqlite3'
        self.lock = threading.RLock()
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')

    def connect(self):
        return sqlite3.connect(self.file, timeout=10)

    def get(self, key, default=None):
        with self.connect() as db:
            row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(value, ensure_ascii=False)))
        return value

    def favorite(self, key, enabled):
        self.favorites([key], enabled)

    def favorites(self, keys, enabled):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT value FROM settings WHERE key='favorites'").fetchone()
            items = set(json.loads(row[0]) if row else [])
            items.update(keys) if enabled else items.difference_update(keys)
            db.execute("INSERT OR REPLACE INTO settings VALUES ('favorites',?)", (json.dumps(sorted(items)),))

    @property
    def output_dir(self):
        return self.get('output_dir', str(self.root / 'exports'))

    def set_output(self, value, remember=True):
        path = Path(value).expanduser()
        if not str(value).strip() or not path.is_absolute():
            raise ValueError('请输入完整的文件夹路径')
        path = path.resolve()
        if any(path.is_relative_to(self.root / name) for name in ('packages', 'personal', 'cache', 'library')):
            raise ValueError('请选择素材、缓存与个人设置以外的导出位置')
        path.mkdir(parents=True, exist_ok=True)
        if remember:
            self.set('output_dir', str(path))
        return str(path)
