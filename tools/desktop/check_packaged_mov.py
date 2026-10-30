"""Compatibility command: exercise every format, including MOV, in the frozen backend."""
import argparse
import subprocess
import sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--backend',type=Path,required=True);a=p.parse_args()
subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'animation/test_library.py'),'--backend',str(a.backend.resolve()/'UTdrSpriteBackend.exe')],check=True)
