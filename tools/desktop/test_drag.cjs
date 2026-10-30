const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const dir=fs.mkdtempSync(path.join(path.resolve(__dirname,'../../releases'),'sprite-drag-test-'));let calls=0,lastBody,dragged;
const handlers=new Map(),events=new Map(),lifecycle=new Map();
const electron={app:{whenReady:()=>({then:()=>{}}),on:(n,f)=>lifecycle.set(n,f)},ipcMain:{handle:(n,f)=>handlers.set(n,f),on:(n,f)=>events.set(n,f)},nativeImage:{createFromBuffer:()=>({resize:()=>({})})},shell:{}};
const context=vm.createContext({require:n=>n==='electron'?electron:require(n),__dirname,console,URL,Buffer,process,setTimeout,clearTimeout,fetch:async()=>({ok:true,arrayBuffer:async()=>new ArrayBuffer(0)})});
vm.runInContext(fs.readFileSync(__dirname+'/main.cjs','utf8'),context);
context.fakeApi=async(route,body)=>{
 if(route.startsWith('/api/variant'))return {frames:[{image:'images/test.png'},{image:'images/test.png'}]};
 if(route==='/api/validate-output')return {output_dir:body.output_dir};
 if(route==='/api/export'){
  calls++;lastBody=body;assert.equal(body.remember_output,false);assert.notEqual(body.output_dir,dir);
  const folder=path.join(body.output_dir,'Test-package','job'+calls);fs.mkdirSync(folder,{recursive:true});
  const names=body.options.format==='png'?['frame0.png','frame1.png']:['animation.png'];
  names.forEach(name=>fs.writeFileSync(path.join(folder,name),'test image bytes'));
  fs.writeFileSync(path.join(folder,'manifest.json'),JSON.stringify({signature:JSON.stringify(body.options),file_hashes:Object.fromEntries(names.map(name=>[name,require('node:crypto').createHash('sha256').update('test image bytes').digest('hex')])),records:[body.options.format==='png'?{files:names.map(file=>({file}))}:{file:names[0]}]}));
  return {id:folder};
 }
 return {state:'done',success:1,errors:0,category:'Test-package',folder:route.slice('/api/job/'.length)};
};
vm.runInContext("api=fakeApi;win={webContents:{mainFrame:{url:'http://127.0.0.1:8930/'}}};base='http://127.0.0.1:8930'",context);
const event=vm.runInContext('({sender:win.webContents,senderFrame:win.webContents.mainFrame})',context);
event.sender.startDrag=item=>{dragged=item};event.sender.send=()=>{};
(async()=>{try{
 const prepare=handlers.get('sprite:prepare');
 const request={id:'test',format:'mov',scale:5,fps:3.75,output:dir};
 const a=await prepare(event,request);assert.equal(fs.readdirSync(dir).length,0);
 const b=await prepare(event,{...request,format:'png-all'});assert.equal(b.count,2);assert.equal(fs.readdirSync(dir).length,0);
 assert.equal(vm.runInContext('ready.size',context),1);
 events.get('sprite:drag')(event,b.token);assert.equal(dragged.files.length,2);assert.ok(dragged.files.every(f=>fs.existsSync(f)&&f.startsWith(path.join(dir,'Test-package','drag'))));
 const saved=dragged.files.slice();events.get('sprite:drag')(event,b.token);assert.equal(fs.readdirSync(dir).length,1);
 const c=await prepare(event,request);
 context.tokenForTest=c.token;const legacy=JSON.parse(vm.runInContext('JSON.stringify(ready.get(tokenForTest).manifest)',context));
 const legacyFolder=path.join(dir,'Test-package','drag','000-legacy');fs.mkdirSync(legacyFolder);
 legacy.file_hashes={'old-name.png':Object.values(legacy.file_hashes)[0]};fs.writeFileSync(path.join(legacyFolder,'old-name.png'),'test image bytes');
 fs.writeFileSync(path.join(legacyFolder,'manifest.json'),JSON.stringify(legacy));
 events.get('sprite:drag')(event,c.token);assert.equal(dragged.files.length,1);assert.equal(path.basename(dragged.files[0]),'animation.png');
 const again=await prepare(event,{...request,format:'png-all'});events.get('sprite:drag')(event,again.token);assert.deepEqual(dragged.files,saved);
 lifecycle.get('before-quit')({preventDefault(){}});assert.ok(saved.every(f=>fs.existsSync(f)));assert.equal(fs.existsSync(vm.runInContext('temporary',context)),false);
 console.log('PASS: preview creates no output; APNG and PNG-all drag payloads; repeat drag reuse; cache cleanup preserves saved files');
 }finally{console.log('Test outputs retained:',dir)}})().catch(e=>{console.error(e);process.exitCode=1});
