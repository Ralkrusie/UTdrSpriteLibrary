# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

ui = Path(SPECPATH)
root = ui.parents[1]
datas = [(str(ui / name), '.') for name in ('index.html', 'app.js', 'style.css', 'library-ui.js')]
datas += [(str(root / 'assets/ui' / name), 'ui-assets') for name in ('spr_dodgeheart_0.png', 'fnt-main-title.svg')]
datas += [(str(root / 'tools/desktop/drag-ui.js'), '.'), (str(root / 'tools/export.csx'), '.')]
a = Analysis([str(ui / 'backend_entry.py')], pathex=[str(ui)], datas=datas,
             excludes=['imageio_ffmpeg', 'PIL.AvifImagePlugin', 'PIL._avif'])
pyz = PYZ(a.pure)
backend = EXE(pyz, a.scripts, [], exclude_binaries=True, name='UTdrSpriteBackend',
              console=sys.platform != 'win32', upx=False)
cli = EXE(pyz, a.scripts, [], exclude_binaries=True, name='utdr', console=True, upx=False)
coll = COLLECT(backend, cli, a.binaries, a.datas, name='UTdrSpriteBackend', upx=False)
