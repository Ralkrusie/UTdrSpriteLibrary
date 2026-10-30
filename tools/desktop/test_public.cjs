// Test an isolated copy: the supplied public runtime remains untouched.
const {_electron}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const original=path.resolve(process.argv[2]);
 assert(!fs.existsSync(path.join(original,'data')),'Public runtime contains data');
 const work=fs.mkdtempSync(path.resolve('releases/public-check-')),root=path.join(work,'runtime');
 fs.cpSync(original,root,{recursive:true});
 const env={...process.env};delete env.ELECTRON_RUN_AS_NODE;
 const app=await _electron.launch({executablePath:path.join(root,'SpriteLibrary.exe'),env});
 try{
  const page=await app.firstWindow(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.waitForFunction(()=>document.querySelector('#library-summary')?.textContent==='导入素材包以开始');
  await page.locator('.game-title').evaluate(image=>image.decode());
  const state=await page.evaluate(async()=>({
   libraries:await (await fetch('/api/libraries')).json(),
   settings:await (await fetch('/api/settings')).json(),
   title:await (await fetch('/ui-title.svg')).text(),
   heart:(await fetch('/ui-heart.png')).status,
  }));
  assert.deepEqual(state.libraries.packages,[]);assert.deepEqual(state.libraries.errors,[]);
  assert.deepEqual(state.settings.presets,[]);assert.equal(state.heart,200);
  assert(!state.title.includes('<image'));assert(!state.title.includes('base64'));
  assert(state.libraries.umt.endsWith('SpriteExtractor.exe'));assert(fs.existsSync(state.libraries.umt));
  assert.equal(await page.locator('#library').isDisabled(),true);
  await page.locator('#manage-library').click();
  assert.equal(await page.locator('#start-import').isEnabled(),true);
  await page.locator('#import-mode').selectOption('game');
  assert.equal(await page.locator('#start-import').textContent(),'制作素材包');
  await page.locator('#close-library').click();
  // Optional original title reference stays local and is never included in the public package.
  if(process.argv[3]){
   const reference=fs.readFileSync(path.resolve(process.argv[3]),'utf8');
   const equal=await page.evaluate(async({reference,current})=>{
    async function pixels(svg){
     const image=new Image();image.src='data:image/svg+xml;base64,'+btoa(svg);await image.decode();
     const canvas=document.createElement('canvas');canvas.width=357;canvas.height=48;
     const context=canvas.getContext('2d');context.imageSmoothingEnabled=false;context.drawImage(image,0,0,357,48);
     return context.getImageData(0,0,357,48).data;
    }
    const a=await pixels(reference),b=await pixels(current);return a.every((value,index)=>value===b[index]);
   },{reference,current:state.title});
   assert(equal,'Visible title pixels differ');
  }
  for(const width of [1250,640,360]){
   await page.setViewportSize({width,height:900});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:path.join(work,`empty-${width}.png`)});
  }
  assert.deepEqual(errors,[]);assert(!fs.existsSync(path.join(original,'data')));
  fs.writeFileSync(path.join(work,'result.json'),JSON.stringify({empty_start:true,no_default_presets:true,embedded_extractor:true,title_pixels_match:!!process.argv[3],errors},null,2));
  console.log('PASS empty public startup, UI assets, import controls, responsive layout:',work);
 }finally{await app.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
