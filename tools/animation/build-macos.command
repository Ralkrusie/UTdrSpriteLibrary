#!/bin/bash
set -e
cd "$(dirname "$0")"
trap 'echo; echo "构建未完成，请保留错误信息。"; read -r -p "按回车关闭…"' ERR
python3 -c 'import sys; assert sys.platform == "darwin" and sys.version_info >= (3,10), "请在 Mac 上使用 Python 3.10+"'
if [ ! -x .build-env/bin/python ]; then python3 -m venv .build-env; fi
.build-env/bin/python -m pip install 'Pillow==12.3.0' 'PyInstaller==6.16.0'
.build-env/bin/python tools/animation/build_macos.py --out "releases/mac-$(date +%Y%m%d-%H%M%S)"
read -r -p "构建完成，按回车关闭…"
