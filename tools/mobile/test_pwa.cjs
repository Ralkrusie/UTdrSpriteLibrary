// Run against a built PWA on localhost, with generated non-game fixtures.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const http=require('node:http'),fs=require('node:fs');
 const root=path.resolve(process.argv[2]||'releases/mobile-pwa-20261030-v2');
 const server=http.createServer((req,res)=>{
  const url=decodeURIComponent(req.url.split('?')[0]),file=path.join(root,url==='/'?'index.html':url);
  if(!file.startsWith(root+path.sep)){res.writeHead(403);res.end();return}
  try{res.setHeader('Content-Type',({'.html':'text/html','.js':'text/javascript','.css':'text/css','.webmanifest':'application/manifest+json','.png':'image/png'})[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file))}catch{res.writeHead(404);res.end()}
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({executablePath:process.env.PWA_BROWSER||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const context=await browser.newContext({viewport:{width:390,height:844}});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto('http://127.0.0.1:'+server.address().port+'/');
  await page.waitForFunction(()=>document.querySelector('#offline-status').textContent.includes('已就绪'));
  await page.locator('#open-help').click();assert(await page.locator('#help').isVisible());assert.equal(await page.locator('#help a').count(),4);await page.locator('#close-help').click();assert(!(await page.locator('#help').isVisible()));
  // Full verification must still reject damaged PNG payloads after read batching.
  const stored=[...fs.readFileSync('releases/mobile-pwa-test/stored.zip')];
  const corrupted=await page.evaluate(async bytes=>{
   const data=new Uint8Array(bytes);
   const marker=data.findIndex((v,i)=>v===137&&data[i+1]===80&&data[i+2]===78&&data[i+3]===71);
   if(marker<0)throw Error('Missing fixture PNG');data[marker+32]^=1;
   const {SpriteArchive}=await import('./archive.js');const archive=await SpriteArchive.open(new Blob([data]));
   try{await archive.verify(()=>{});return {rejected:false}}catch(e){return {rejected:e.message.includes('校验失败'),released:archive.blocks===null}}
  },stored);
  assert.deepEqual(corrupted,{rejected:true,released:true});
  await page.locator('#pack-input').setInputFiles('releases/mobile-pwa-test/sample.zip');
  await page.locator('.card').waitFor();await page.waitForFunction(()=>!document.querySelector('#import-pack').disabled);
  assert.equal(await page.locator('#chapter option').count(),3);
  await page.locator('.star').first().click();assert.equal(await page.locator('.card.favorite').count(),1);
  await page.locator('#pack-input').setInputFiles('releases/mobile-pwa-test/stored.zip');
  await page.waitForFunction(()=>document.querySelector('#pack-status').textContent.includes('已导入'));
  assert.equal(await page.locator('#packs option').count(),1);
  await page.locator('#pack-input').setInputFiles('releases/mobile-pwa-test/bad.zip');
  await page.waitForFunction(()=>document.querySelector('#pack-status').textContent.includes('无效'));
  assert.equal(await page.locator('.card').count(),1);
  await page.locator('.thumb').click();await page.waitForFunction(()=>!document.querySelector('#export').disabled);
  await page.locator('#scale').selectOption('custom');await page.locator('#custom-scale').fill('2.5');await page.locator('#custom-scale').blur();
  assert.equal(await page.locator('#copy').count(),0);
  assert.equal(await page.locator('#close').textContent(),'返回');
  // Footer stays at the lower right while detail content scrolls, in both orientations.
  for(const viewport of [{width:390,height:780},{width:780,height:390}]){
   await page.setViewportSize(viewport);
   const before=await page.locator('#close').boundingBox();
   await page.locator('#detail .detail-body').evaluate(e=>e.scrollTop=e.scrollHeight);
   const after=await page.locator('#close').boundingBox(),dialog=await page.locator('#detail').boundingBox();
   assert.deepEqual(after,before);assert(after.x>dialog.x+dialog.width/2);
   assert(after.y+after.height<=viewport.height);assert(after.y>dialog.y+dialog.height-100);
   await page.locator('#detail .detail-body').evaluate(e=>e.scrollTop=0);
  }
  await page.setViewportSize({width:390,height:844});
  const previewBefore=await page.locator('#canvas').boundingBox();await page.locator('#custom-scale').fill('20');await page.locator('#custom-scale').blur();assert.deepEqual(await page.locator('#canvas').boundingBox(),previewBefore);await page.locator('#custom-scale').fill('2.5');await page.locator('#custom-scale').blur();
  for(const format of ['png','apng','gif','png-all']){
   await page.locator('#format').selectOption(format);await page.locator('#export').click();await page.locator('.save-file').waitFor();
   const download=page.waitForEvent('download');await page.locator('.save-file').click();const file=await download;
   await file.saveAs(path.resolve('releases/mobile-pwa-test',format+'-'+file.suggestedFilename()));
   await page.locator('#job-close').click();await page.waitForFunction(()=>!document.querySelector('#job').open);
  }
  await page.locator('#close').click();await page.waitForFunction(()=>!document.querySelector('#detail').open);
  await context.setOffline(true);await page.reload();await page.locator('.card.favorite').waitFor();
  await page.locator('.thumb').click();await page.waitForFunction(()=>!document.querySelector('#export').disabled);
  assert.equal(await page.locator('#custom-scale').inputValue(),'2.5');
  for(const width of [320,390,768]){await page.setViewportSize({width,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert(await page.locator('#detail').evaluate(e=>e.scrollWidth<=e.clientWidth));await page.waitForFunction(()=>{const c=document.querySelector('#canvas').getBoundingClientRect(),s=document.querySelector('.stage').getBoundingClientRect();return c.width<=s.width&&c.height<=s.height});}
  await page.screenshot({path:'releases/mobile-pwa-test/detail.png'});
  await page.locator('#close').click();await page.waitForFunction(()=>!document.querySelector('#detail').open);
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:'releases/mobile-pwa-test/browse.png',fullPage:true});
  assert.deepEqual(errors,[]);
  await context.setOffline(false);
  const native=await context.newPage();native.on('pageerror',e=>console.error('Native page error:',e.message));
  await native.addInitScript(()=>{
   window.nativeFiles=[];let current;
   window.AndroidExports={begin(name){current={name,parts:[]};return 'test'},append(id,data){current.parts.push(atob(data));return true},finish(id,action){nativeFiles.push({...current,action,bytes:current.parts.join('')});return true}};
  });
  await native.goto('http://127.0.0.1:'+server.address().port+'/');
  await native.waitForFunction(()=>!document.querySelector('body > footer'));assert.equal(await native.locator('body > footer').count(),0);
  await native.locator('.thumb').click();await native.waitForFunction(()=>!document.querySelector('#export').disabled);
  await native.locator('#format').selectOption('gif');await native.locator('#export').click();await native.locator('.save-file').waitFor();
  await native.locator('.save-file').click();await native.waitForFunction(()=>nativeFiles.length===1);
  await native.getByRole('button',{name:'分享文件',exact:true}).click();await native.waitForFunction(()=>nativeFiles.length===2);
  const files=await native.evaluate(()=>nativeFiles.map(f=>({action:f.action,header:f.bytes.slice(1,4)})));
  assert.deepEqual(files.map(f=>f.action),['save','share']);assert.equal(files[0].header,'IF8');
  console.log('PASS: import/duplicate/reject, favorites, auto-fit, exports, offline restore, 320–768px layout; Android JS bridge contract (mock, not device)');
 }catch(e){console.error('Page status:',await page.locator('#detail-status').textContent(), 'Errors:',errors);throw e}finally{await browser.close();server.close()}
})().catch(e=>{console.error(e);process.exit(1)});
