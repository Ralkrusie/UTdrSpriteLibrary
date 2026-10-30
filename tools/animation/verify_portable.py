"""Validate a newly built backend with Python/FFmpeg removed from its PATH."""
import argparse
import subprocess
import sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--backend',type=Path,required=True);a=p.parse_args()
subprocess.run([sys.executable,str(Path(__file__).with_name('test_library.py')),'--backend',str(a.backend.resolve()/'UTdrSpriteBackend.exe')],check=True)
