"""Run on macOS: build a native, folder-based distribution for this Python's architecture."""
import argparse
import importlib.metadata
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
UI=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if sys.platform!='darwin':p.error('必须在 macOS 上构建，不能从 Windows 交叉打包。')
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--console','--name','DeltaruneSpriteLibrary','--distpath',str(out),'--workpath',str(out/'_build'),'--specpath',str(out/'_build')]
    for name in ('index.html','app.js','style.css'):command+=['--add-data',str(UI/name)+':.']
    subprocess.run(command+[str(UI/'server.py')],check=True)
    package=out/'DeltaruneSpriteLibrary';library=package/'library';library.mkdir()
    for name in ('catalog.json','named-index.json'):shutil.copy2(ROOT/'library'/name,library/name)
    shutil.copytree(ROOT/'library/images',library/'images')
    launcher=package/'启动.command'
    launcher.write_text('#!/bin/bash\ncd "$(dirname "$0")"\n./DeltaruneSpriteLibrary\nstatus=$?\nif [ "$status" -ne 0 ]; then read -r -p "启动失败，按回车关闭…"; fi\n',encoding='utf-8')
    launcher.chmod(0o755)
    licenses=package/'licenses';licenses.mkdir()
    for name in ('Pillow','PyInstaller'):
        dist=importlib.metadata.distribution(name)
        for f in dist.files or []:
            if 'license' in f.name.lower() or 'copying' in f.name.lower():
                path=Path(dist.locate_file(f))
                if path.is_file():shutil.copy2(path,licenses/(name+'-'+f.name))
    for path in (Path(sys.base_prefix)/'LICENSE.txt',Path(sys.base_prefix)/'Resources/LICENSE.txt'):
        if path.is_file():shutil.copy2(path,licenses/'Python-LICENSE.txt');break
    (package/'使用说明.txt').write_text('macOS 原生文件夹版（未签名、未公证）。完整解压到可写目录，双击“启动.command”。无需安装 Python 或 Pillow。保留终端窗口，Ctrl+C 停止服务。\n本包架构：'+platform.machine()+'；构建系统：macOS '+platform.mac_ver()[0]+'。需在目标 Mac 验证。\n游戏素材归原权利人；运行组件许可位于 licenses。\n',encoding='utf-8')
    archive=out/('DeltaruneSpriteLibrary-macOS-'+platform.machine()+'.zip')
    subprocess.run(['/usr/bin/ditto','-c','-k','--keepParent',str(package),str(archive)],check=True)
    print('Built: '+str(archive),flush=True)

if __name__=='__main__':main()
