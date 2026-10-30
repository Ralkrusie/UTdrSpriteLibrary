#!/bin/bash
set -e
cd "$(dirname "$0")"
trap 'echo; echo "启动未完成。请保留上面的错误信息。"; read -r -p "按回车关闭…"' ERR
if ! command -v python3 >/dev/null 2>&1; then
  echo "请先从 https://www.python.org/downloads/macos/ 安装 Python 3.10 或更新版本。"
  read -r -p "按回车关闭…"
  exit 1
fi
python3 -c 'import sys; assert sys.version_info >= (3,10), "需要 Python 3.10 或更新版本"'
if [ ! -x .runtime/bin/python ]; then
  python3 -m venv .runtime
fi
if ! .runtime/bin/python -c 'import PIL; assert PIL.__version__ == "12.3.0"' 2>/dev/null; then
  echo "首次启动：安装 Pillow（需要联网，仅安装到此文件夹的 .runtime）。"
  .runtime/bin/python -m pip install 'Pillow==12.3.0'
fi
.runtime/bin/python tools/animation/server.py --open --auto-port
