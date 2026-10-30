"""Explicit real-game read-only import check against a built desktop backend."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'animation'))
from import_game import discover
from library import sha

p=argparse.ArgumentParser();p.add_argument('--backend',type=Path,required=True);p.add_argument('--game',type=Path,required=True);p.add_argument('--kind',choices=['UT','DR'],required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2]
work=Path(tempfile.mkdtemp(prefix='frozen-game-import-',dir=root/'releases'))
inputs={str(file):sha(file) for _,file in discover(a.game,a.kind)}
ready=work/'ready.json'
env=dict(os.environ);env['PATH']=str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32')
process=subprocess.Popen([str(a.backend.resolve()/'UTdrSpriteBackend.exe'),'--data',str(work/'data'),'--port','0','--ready-file',str(ready),'--parent-pid',str(os.getpid())],env=env,creationflags=subprocess.CREATE_NO_WINDOW)
try:
    for _ in range(300):
        if ready.exists():break
        assert process.poll() is None,'Backend exited'
        time.sleep(.1)
    info=json.loads(ready.read_text());assert 'url' in info,info
    base=info['url'].rstrip('/')
    def api(route,body=None):
        r=urllib.request.Request(base+route,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(r,timeout=60) as response:return json.load(response)
    assert api('/api/libraries')['umt'],'Bundled UMT missing'
    job=api('/api/library/import',{'mode':'game','game':a.kind,'path':str(a.game.resolve()),'name':a.kind+' 本机素材','version':'','language':'版本及补丁未确认'})
    prior=''
    for _ in range(1800):
        status=api('/api/job/'+job['id'])
        if status['current']!=prior:
            prior=status['current'];print(prior,flush=True)
        if status['state'] not in ('queued','running'):break
        time.sleep(.5)
    assert status['state']=='done' and status['success']==1,status
    pid=status['package_id'];catalog=api('/api/catalog?package='+pid)
    assert len(catalog)>100
    assert {str(file):sha(file) for _,file in discover(a.game,a.kind)}==inputs
    variant=next(v for v in catalog if v['complete'] and 2<=v['count']<=8 and v['width']<=100 and v['height']<=100)
    result=api('/api/export',{'ids':[variant['id']],'options':{'format':'mov','scale':5,'fps':3.75},'output_dir':str(work/'exports')})
    for _ in range(300):
        export=api('/api/job/'+result['id'])
        if export['state'] not in ('queued','running'):break
        time.sleep(.1)
    assert export['state']=='done' and export['success']==1 and not export['errors'],export
    report={'game':a.kind,'package_id':pid,'sprites':len(catalog),'inputs_unchanged':True,'inputs':inputs,'mov':export['folder'],'package':str(work/'data/packages'/(pid+'.zip'))}
    (work/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)
finally:
    process.terminate();process.wait(timeout=15)
