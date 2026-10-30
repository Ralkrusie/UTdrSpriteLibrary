"""Assemble the Windows desktop using the verified Electron ZIP and existing frozen backend."""
import argparse
import hashlib
import shutil
import subprocess
import zipfile
import json
from umt_runtime import copy_umt
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--backend',type=Path,required=True);p.add_argument('--all-locales',action='store_true',help='Include every Electron locale instead of Chinese and English');extract=p.add_mutually_exclusive_group();extract.add_argument('--umt',type=Path,help='Optional independently obtained UMT runtime directory');extract.add_argument('--extractor',type=Path,help='Dedicated extractor built from current export.csx');args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
 runtime=ROOT/'vendor/electron/electron-verified.zip'
 digest=hashlib.sha256(runtime.read_bytes()).hexdigest()
 if not any(line.split()[0]==digest and line.split()[-1].lstrip('*')=='electron-v45.1.0-win32-x64.zip' for line in (ROOT/'vendor/electron/SHASUMS256.txt').read_text().splitlines()):raise ValueError('Electron 官方校验不通过')
 locales={'zh-CN.pak','zh-TW.pak','en-US.pak','en-GB.pak'}
 omitted=[]
 with zipfile.ZipFile(runtime) as z:
  for entry in z.infolist():
   if not args.all_locales and entry.filename.startswith('locales/') and entry.filename.endswith('.pak') and Path(entry.filename).name not in locales:
    omitted.append({'file':entry.filename,'bytes':entry.file_size});continue
   z.extract(entry,out)
 (out/'packaging-profile.json').write_text(json.dumps({'electron_sha256':digest,'all_locales':args.all_locales,'omitted_locales':omitted,'omitted_bytes':sum(item['bytes'] for item in omitted)},indent=2),encoding='utf-8')
 (out/'electron.exe').rename(out/'SpriteLibrary.exe')
 # Preserve Electron's MIT grant separately from our GPL license.
 (out/'LICENSE').rename(out/'Electron-LICENSE')
 for name in ('LICENSE','THIRD_PARTY_NOTICES.md','ASSET_NOTICE.md'):
  shutil.copy2(ROOT/name,out/name)
 shutil.copytree(ROOT/'licenses',out/'licenses')
 (out/'docs').mkdir()
 for name in ('BUILD.md','NATIVE_SOURCES.md','CLI.md'):
  shutil.copy2(ROOT/'docs'/name,out/'docs'/name)
 app=out/'resources/app';app.mkdir(parents=True)
 for name in ('main.cjs','preload.cjs','platform.cjs','package.json'):shutil.copy2(HERE/name,app/name)
 (out/'utdr.cmd').write_text('@echo off\n"%~dp0backend\\utdr.exe" %*\nexit /b %errorlevel%\n',encoding='utf-8')
 backend=out/'backend';backend.mkdir()
 source=args.backend.resolve()
 for name in ('UTdrSpriteBackend.exe','utdr.exe','THIRD_PARTY.txt'):shutil.copy2(source/name,backend/name)
 for name in ('_internal','licenses'):shutil.copytree(source/name,backend/name)
 probe=subprocess.run([str(backend/'utdr.exe'),'version','--json'],check=True,capture_output=True,text=True,encoding='utf-8')
 if json.loads(probe.stdout).get('ok') is not True:raise ValueError('CLI launcher check failed')
 shutil.copytree(ROOT/'tools/animation/licenses',backend/'licenses',dirs_exist_ok=True)
 if args.umt:
  umt=args.umt.resolve()
  if not (umt/'UndertaleModCli.exe').is_file():raise ValueError('UMT CLI missing')
  report=copy_umt(umt,backend/'umt')
  print('UMT runtime: kept',report['kept_bytes'],'bytes; omitted',report['excluded_bytes'],'bytes')
 if args.extractor:
  source=args.extractor.resolve()
  if not (source/'SpriteExtractor.exe').is_file() or not (source/'build-profile.json').is_file():raise ValueError('Dedicated extractor build missing')
  profile=json.loads((source/'build-profile.json').read_text(encoding='utf-8'))
  if profile['source_script_sha256']!=hashlib.sha256((ROOT/'tools/export.csx').read_bytes()).hexdigest():raise ValueError('Extractor was built from a different extraction script')
  for name,digest in profile['files'].items():
   if Path(name).name!=name or hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise ValueError('Extractor file checksum mismatch: '+name)
  shutil.copytree(source,backend/'extractor')
 (out/'使用说明.txt').write_text('UTdrSpriteLibrary · Windows x64 测试版\n\n完整解压到可写目录后双击 SpriteLibrary.exe。无需 Python 或 FFmpeg。\n在“管理素材包”中导入 ZIP；也可指定游戏目录，只读提取并制作素材包。未知版本可留空。\n素材包保存在 data/packages，个人设置保存在 data/personal，默认导出位于 data/exports。不要单独移动后端或运行依赖。\n收藏对应当前素材包的原始条目。删除素材包会保留导出与个人设置。\n预览只使用临时缓存；开始拖拽时保存文件，取消拖拽仍保留。MOV 为 qtrle 无损透明单轮动画，接收软件的兼容性需实际确认。\n不附带游戏素材包；界面资源说明见 ASSET_NOTICE.md。许可文件位于根目录、licenses 与 backend/licenses。\n测试版下载与反馈：https://github.com/Ralkrusie/UTdrSpriteLibrary/releases\n',encoding='utf-8-sig')
 print(out,flush=True)
if __name__=='__main__':main()
