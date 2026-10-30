// Run only against a fresh package with test ZIPs, before restoring user settings.
const {_electron}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const root=path.resolve(process.argv[2]),work=fs.mkdtempSync(path.resolve('releases/runtime-check-'));
 const env={...process.env};delete env.ELECTRON_RUN_AS_NODE;
 assert.deepEqual(fs.readdirSync(path.join(root,'locales')).sort(),['en-GB.pak','en-US.pak','zh-CN.pak','zh-TW.pak']);
 assert(!fs.readdirSync(path.join(root,'backend/_internal/PIL')).some(n=>n.startsWith('_avif')));
 const results=[];
 for(const lang of ['zh-CN','zh-TW','en-US','en-GB','fr','ja']){
  const app=await _electron.launch({executablePath:path.join(root,'SpriteLibrary.exe'),args:['--lang='+lang],env});
  try{
   const p=await app.firstWindow(),errors=[];p.on('pageerror',e=>errors.push(e.message));
   await p.waitForFunction(()=>document.querySelector('.card'));
   await p.locator('.game-title').evaluate(i=>i.decode());
   const locale=await app.evaluate(({app,Menu})=>({locale:app.getLocale(),copy:Menu.buildFromTemplate([{role:'copy'}]).items[0].label}));
   assert(locale.copy.length>0);if(['fr','ja'].includes(lang))assert(['zh-CN','zh-TW','en-US','en-GB'].includes(locale.locale));
   await p.locator('.card .open').first().click();await p.waitForFunction(()=>document.querySelector('#name').textContent!=='加载中');
   await p.waitForFunction(()=>document.querySelector('.drag-controls').textContent.includes('可拖动预览图'));
   if(lang==='zh-CN'){
    const output=path.join(work,'drag-target');
    for(const format of ['png','png-all','gif','apng','mov']){
     const prepared=await p.evaluate(async({format,output})=>window.spriteDesktop.prepare({id:active.id,format,scale:2.5,fps:3.75,frame:0,output}),{format,output});
     assert(prepared.token);assert(prepared.count>=1);
    }
    await p.screenshot({path:path.join(work,'detail.png')});
   }
   assert.deepEqual(errors,[]);results.push({requested:lang,...locale});
  }finally{await app.close()}
 }
 fs.writeFileSync(path.join(work,'results.json'),JSON.stringify(results,null,2));console.log('PASS packaged locales, fallback labels, PNG/GIF/APNG/MOV drag preparation:',work);console.log(results);
})().catch(e=>{console.error(e);process.exitCode=1});
