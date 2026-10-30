// Run on the target desktop (under Xvfb on Linux), against a native candidate.
const {_electron}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const root=path.resolve(process.argv[2]);
 const work=fs.mkdtempSync(path.resolve('releases/native-ui-'));
 const data=path.join(work,'用户 data');
 const executablePath=process.platform==='darwin'?path.join(root,'UTdrSpriteLibrary.app/Contents/MacOS/Electron'):path.join(root,'SpriteLibrary');
 const env={...process.env,UTDR_DATA_DIR:data};delete env.ELECTRON_RUN_AS_NODE;
 const app=await _electron.launch({executablePath,env});
 let backendPid;
 try{
  const page=await app.firstWindow(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.waitForFunction(()=>document.querySelector('#library-summary')?.textContent==='导入素材包以开始');
  await page.locator('.game-title').evaluate(i=>i.decode());
  const state=await page.evaluate(async()=>({libraries:await(await fetch('/api/libraries')).json(),settings:await(await fetch('/api/settings')).json()}));
  assert.deepEqual(state.libraries.packages,[]);assert.deepEqual(state.settings.presets,[]);
  assert.equal(state.libraries.game_import,false);
  await page.locator('#manage-library').click();
  assert(await page.locator('#import-mode option[value=game]').isDisabled());
  assert(await page.locator('#start-import').isEnabled());
  await page.locator('#close-library').click();
  for(const width of [1250,640,360]){
   await page.setViewportSize({width,height:900});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  }
  // Obtain the backend PID from its process tree, without requiring renderer IPC.
  backendPid=await app.evaluate(async()=>{
   const {execFileSync}=require('node:child_process');
   const lines=execFileSync('ps',['-axo','pid=,ppid=,comm='],{encoding:'utf8'}).trim().split('\n');
   return lines.map(l=>l.trim().split(/\s+/)).filter(p=>+p[1]===process.pid&&p.slice(2).join(' ').includes('UTdrSpriteBackend')).map(p=>+p[0]);
  });
  assert(backendPid.length>0);assert.deepEqual(errors,[]);
  assert(fs.existsSync(path.join(data,'personal')));
 }finally{await app.close()}
 for(let n=0;n<50;n++){
  if(backendPid.every(pid=>{try{process.kill(pid,0);return false}catch{return true}}))break;
  await new Promise(r=>setTimeout(r,100));
 }
 for(const pid of backendPid)assert.throws(()=>process.kill(pid,0));
 assert(!fs.existsSync(path.join(root,'data')));
 console.log('PASS native startup, ZIP-only import, UI layout, user directory and backend exit');
})().catch(e=>{console.error(e);process.exitCode=1});
