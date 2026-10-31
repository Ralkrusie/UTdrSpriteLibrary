// Exercise the IPC boundary without starting Electron or invoking OS drag actions.
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const handlers=new Map(),sent=new Map();
const electron={app:{getPath:()=>require('node:os').tmpdir(),whenReady:()=>({then:()=>{}}),on:()=>{}},BrowserWindow:function(){},ipcMain:{handle:(n,f)=>handlers.set(n,f),on:(n,f)=>sent.set(n,f)},nativeImage:{},dialog:{},shell:{}};
const context=vm.createContext({require:n=>n==='electron'?electron:require(n),__dirname:__dirname,console,Buffer,process:Object.assign(Object.create(process),{resourcesPath:require('node:path').resolve(__dirname,'..')}),setTimeout,clearTimeout,fetch,URL});
vm.runInContext(fs.readFileSync(__dirname+'/main.cjs','utf8'),context);
assert.throws(()=>handlers.get('sprite:prepare')({sender:{}},{}),/Invalid caller/);
vm.runInContext("win={webContents:{mainFrame:{url:'http://127.0.0.1:8930/'}}};base='http://127.0.0.1:8930';",context);
const event=vm.runInContext('({sender:win.webContents,senderFrame:win.webContents.mainFrame})',context);
(async()=>{
 const opened=[];electron.shell.openExternal=async url=>opened.push(url);
 const external=handlers.get('sprite:open-external');
 assert.throws(()=>external({sender:{}},'https://github.com/Ralkrusie/UTdrSpriteLibrary/releases'),/Invalid caller/);
 for(const url of ['file:///C:/Windows','https://example.com','https://afdian.com/a/ralkrusie?other=1'])assert.throws(()=>external(event,url),/无效外部链接/);
 await external(event,'https://afdian.com/a/ralkrusie');assert.deepEqual(opened,['https://afdian.com/a/ralkrusie']);
 for(const request of [{id:'x',format:'invalid',scale:5,fps:3.75,output:'x'},{id:'x',format:'png',scale:5,fps:3.75,frame:-1,output:'x'},{id:'x',format:'gif',scale:Infinity,fps:3.75,output:'x'}]){
  await assert.rejects(handlers.get('sprite:prepare')(event,request));
 }
 const other={sender:event.sender,senderFrame:{url:'http://127.0.0.1:8930/'}};
 for(const scale of [.249,20.001,NaN])await assert.rejects(handlers.get('sprite:prepare')(event,{id:'x',format:'gif',scale,fps:3.75,output:'x'}));
 assert.throws(()=>handlers.get('sprite:prepare')(other,{}),/Invalid caller/);
 console.log('IPC checks passed: invalid sender/subframe/options rejected');
})();
