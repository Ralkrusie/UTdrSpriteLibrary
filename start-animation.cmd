@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Create .venv and install requirements-build.txt first. See README.md.
  pause
  exit /b 1
)
.venv\Scripts\python tools\animation\server.py --open --auto-port
if errorlevel 1 pause
