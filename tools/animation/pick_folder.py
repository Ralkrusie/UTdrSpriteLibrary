"""Run the native folder chooser in its own UI process/thread."""
import json
import sys
import subprocess

def main(initialdir):
    if sys.platform == 'darwin':
        script = '''on run argv
try
set chosen to choose folder with prompt "选择动画导出文件夹" default location (POSIX file (item 1 of argv))
return POSIX path of chosen
on error number -128
return ""
end try
end run'''
        result = subprocess.run(['/usr/bin/osascript', '-e', script, initialdir], capture_output=True, text=True, check=True)
        print(json.dumps({'folder': result.stdout.rstrip('\r\n')}, ensure_ascii=True))
        return
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    try:
        folder = filedialog.askdirectory(parent=root, title='选择动画导出文件夹', initialdir=initialdir)
        print(json.dumps({'folder': folder}, ensure_ascii=True))
    finally:
        root.destroy()

if __name__ == '__main__':
    main(sys.argv[1])
