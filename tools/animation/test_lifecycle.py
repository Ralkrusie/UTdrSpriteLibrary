import ctypes
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from ctypes import wintypes
from lifecycle import bind_to_parent

ROOT=Path(__file__).resolve().parents[2]
if len(sys.argv)>1 and sys.argv[1]=='--owner':
    bind_to_parent(int(sys.argv[2]))
    child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(300)'],creationflags=subprocess.CREATE_NO_WINDOW)
    Path(sys.argv[3]).write_text(str(child.pid))
    time.sleep(300)
    sys.exit()
if len(sys.argv)>1 and sys.argv[1]=='--parent':
    child=subprocess.Popen([sys.executable,__file__,'--owner',str(os.getpid()),sys.argv[2]],creationflags=subprocess.CREATE_NO_WINDOW)
    Path(sys.argv[2]+'.owner').write_text(str(child.pid))
    time.sleep(300)
    sys.exit()

def running(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return False
    code=wintypes.DWORD()
    kernel.GetExitCodeProcess(handle,ctypes.byref(code));kernel.CloseHandle(handle)
    return code.value==259

work=Path(tempfile.mkdtemp(prefix='lifecycle-',dir=ROOT/'releases'))
parents=[]
try:
    for n in range(2):
        marker=work/str(n)
        parents.append(subprocess.Popen([sys.executable,__file__,'--parent',str(marker)],creationflags=subprocess.CREATE_NO_WINDOW))
    for _ in range(100):
        if all((work/str(n)).exists() for n in range(2)):break
        time.sleep(.1)
    owners=[int((work/(str(n)+'.owner')).read_text()) for n in range(2)]
    children=[int((work/str(n)).read_text()) for n in range(2)]
    assert all(running(pid) for pid in owners+children)
    parents[0].terminate();parents[0].wait()
    for _ in range(100):
        if not running(owners[0]) and not running(children[0]):break
        time.sleep(.1)
    assert not running(owners[0]) and not running(children[0]),'Orphaned descendant'
    assert running(owners[1]) and running(children[1]),'Another instance was terminated'
    print('PASS: parent exit kills owned backend and child, preserving another instance')
finally:
    for p in parents:
        if p.poll() is None:p.terminate();p.wait()
