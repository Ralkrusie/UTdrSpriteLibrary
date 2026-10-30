const {app,BrowserWindow,ipcMain,nativeImage,dialog,shell}=require('electron');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {layout,picker}=require('./platform.cjs');
const session=fs.mkdtempSync(path.join(require('node:os').tmpdir(),'utdr-session-'));
const temporary=path.join(session,'drag');fs.mkdirSync(temporary);
function clearTemporary(){for(const entry of fs.readdirSync(temporary))fs.rmSync(path.join(temporary,entry),{recursive:true,force:true});ready.clear();cache.clear()}
const locations=layout({appDir:__dirname,resourcesPath:process.resourcesPath,appData:process.platform==='win32'?null:app.getPath('appData'),dataDir:process.env.UTDR_DATA_DIR});
const {root,backend}=locations,dataRoot=locations.data;
let child,win,base='',closing=false,queue=Promise.resolve();
if(app.setPath){fs.mkdirSync(path.join(dataRoot,'personal','electron'),{recursive:true});app.setPath('userData',path.join(dataRoot,'personal','electron'))}
const ready=new Map(),cache=new Map();
function log(message){fs.appendFileSync(path.join(session,'desktop.log'),new Date().toISOString()+' '+message+'\n')}
function trusted(event){if(!win||event.sender!==win.webContents||event.senderFrame!==win.webContents.mainFrame||new URL(event.senderFrame.url).origin!==base)throw Error('Invalid caller')}
async function api(route,data){const response=await fetch(base+route,data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{});const value=await response.json();if(!response.ok)throw Error(value.error||response.statusText);return value}
async function prepare(request){
 const {id,format,scale,fps,frame,output}=request||{};
 if(typeof id!=='string'||!['png','png-all','gif','apng','mov'].includes(format)||!Number.isFinite(scale)||scale<.25||scale>20||!Number.isFinite(fps)||fps<.1||fps>120||typeof output!=='string')throw Error('参数无效');
 if(format==='png'&&(!Number.isInteger(frame)||frame<0))throw Error('帧序无效');
 const options={format:format==='png-all'?'png':format,scale,fps,...(format==='png'?{frame_index:frame}:{})};
 const key=JSON.stringify([id,options,output]);
 if(cache.has(key)){const previous=ready.get(cache.get(key));if(previous&&previous.files.every(file=>fs.existsSync(file)))return {token:cache.get(key),name:path.basename(previous.files[0]),count:previous.files.length}}
 clearTemporary();
 const variant=await api('/api/variant/'+encodeURIComponent(id));
 const job=await api('/api/export',{ids:[id],options,output_dir:temporary,remember_output:false});
 let result;
 for(let i=0;i<1200;i++){
  if(closing)throw Error('窗口已关闭');
  result=await api('/api/job/'+job.id);
  if(!['queued','running'].includes(result.state))break;
  await new Promise(resolve=>setTimeout(resolve,100));
 }
 if(result.state!=='done'||result.success!==1||result.errors)throw Error(result.current||'准备文件失败，请重试');
 const manifest=JSON.parse(fs.readFileSync(path.join(result.folder,'manifest.json'),'utf8'));
 const record=manifest.records[0];
 const files=(record.files?record.files.map(entry=>entry.file):[record.file]).map(name=>path.resolve(result.folder,name));
 if(!files.length||files.some(file=>path.dirname(file)!==path.resolve(result.folder)||!fs.existsSync(file)))throw Error('导出文件不存在');
 const thumbnail=variant.frames[format==='png'?frame:0].image;
 const response=await fetch(base+'/'+thumbnail);if(!response.ok)throw Error('无效预览路径');
 const icon=nativeImage.createFromBuffer(Buffer.from(await response.arrayBuffer())).resize({width:64,quality:'good'});
 const destination=await api('/api/validate-output',{output_dir:output});
 const token=crypto.randomUUID();ready.set(token,{files,icon,output:destination.output_dir,saved:false,manifest,category:result.category});cache.set(key,token);
 return {token,name:path.basename(files[0]),count:files.length};
}
ipcMain.handle('sprite:prepare',(event,request)=>{trusted(event);const task=queue.then(()=>prepare(request));queue=task.catch(()=>{});return task});
function persist(item){
 if(item.saved)return;
 const destination=path.resolve(item.output),library=path.resolve(dataRoot,'packages');
 if(!path.isAbsolute(item.output)||destination===library||destination.startsWith(library+path.sep))throw Error('无效保存路径');
 const category=path.join(destination,item.category,'drag');fs.mkdirSync(category,{recursive:true});
 // A repeated drag reuses an intact identical export instead of creating another copy.
 if(item.manifest.signature&&item.manifest.file_hashes){
  for(const entry of fs.readdirSync(category,{withFileTypes:true})){
   if(!entry.isDirectory())continue;
   const prior=path.join(category,entry.name);
   try{
    const manifest=JSON.parse(fs.readFileSync(path.join(prior,'manifest.json'),'utf8'));
    const hashes=manifest.file_hashes||{};
    if(manifest.signature!==item.manifest.signature||!Object.keys(hashes).length||manifest.cancelled||manifest.errors?.length)continue;
    // Content may match an older build whose export filenames used a different convention.
    if(JSON.stringify(Object.keys(hashes).sort())!==JSON.stringify(Object.keys(item.manifest.file_hashes).sort()))continue;
    if(!Object.entries(hashes).every(([name,digest])=>path.basename(name)===name&&crypto.createHash('sha256').update(fs.readFileSync(path.join(prior,name))).digest('hex')===digest))continue;
    item.files=Object.keys(hashes).map(name=>path.join(prior,name));item.saved=true;return;
   }catch{}
  }
 }
 const folder=fs.mkdtempSync(path.join(category,'drag-'));
 const files=item.files.map(file=>{const target=path.join(folder,path.basename(file));fs.copyFileSync(file,target);return target});
 fs.writeFileSync(path.join(folder,'manifest.json'),JSON.stringify(item.manifest));
 item.files=files;item.saved=true;
}
ipcMain.on('sprite:drag',(event,token)=>{try{trusted(event);const item=ready.get(token);if(!item||!item.files.every(file=>fs.existsSync(file)))return;persist(item);event.sender.startDrag({file:item.files[0],files:item.files,icon:item.icon});event.sender.send('sprite:saved',token)}catch(e){log('drag error '+e.message);event.sender.send('sprite:drag-error',e.message)}});
ipcMain.handle('sprite:reveal',(event,token)=>{trusted(event);const item=ready.get(token);if(item?.saved)shell.showItemInFolder(item.files[0])});
ipcMain.handle('sprite:pick',async(event,kind)=>{trusted(event);if(!['output','package','game','umt'].includes(kind))throw Error('无效选择类型');const result=await dialog.showOpenDialog(win,picker(kind));return result.canceled?'':result.filePaths[0]});
ipcMain.handle('sprite:export-package',async(event,id)=>{
 trusted(event);
 if(typeof id!=='string')throw Error('无效素材包');
 const destination=await api('/api/library/export-path',{id});
 const result=await dialog.showSaveDialog(win,{title:'导出素材包',defaultPath:destination.file,filters:[{name:'ZIP 素材包',extensions:['zip']}],properties:['showOverwriteConfirmation','createDirectory']});
 if(result.canceled||!result.filePath)return {cancelled:true};
 return api('/api/library/save',{id,path:result.filePath});
});
function startBackend(){return new Promise((resolve,reject)=>{
 const readyFile=path.join(session,'ready.json');
 child=spawn(locations.executable,['--port','8930','--auto-port','--data',dataRoot,'--cache',path.join(session,'import'),'--parent-pid',String(process.pid),'--ready-file',readyFile],{cwd:backend,windowsHide:true,stdio:'ignore'});
 let finished=false;const started=Date.now();
 function check(){if(finished)return;try{if(fs.existsSync(readyFile)){const info=JSON.parse(fs.readFileSync(readyFile,'utf8'));if(info.error)throw Error(info.error);base=new URL(info.url).origin;finished=true;resolve();return}if(Date.now()-started>30000)throw Error('本地服务启动超时');setTimeout(check,100)}catch(e){finished=true;reject(e)}}
 child.on('error',error=>{finished=true;reject(error)});
 child.on('exit',code=>{finished=true;if(!base)reject(Error('本地服务退出：'+code));else if(!closing){dialog.showErrorBox('服务已停止','请关闭后重新启动。');app.quit()}});
 check();
})}
app.whenReady().then(async()=>{
 try{await startBackend();
  win=new BrowserWindow({width:1250,height:900,title:'UTdrSpriteLibrary',backgroundColor:'#050506',autoHideMenuBar:true,webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true}});
  win.on('page-title-updated',event=>event.preventDefault());
  win.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  win.webContents.on('will-navigate',(event,url)=>{if(new URL(url).origin!==base)event.preventDefault()});
  win.webContents.session.setPermissionRequestHandler((_web,_permission,callback)=>callback(false));
  await win.loadURL(base+'/');
 }catch(e){log(e.stack||e.message);dialog.showErrorBox('启动失败',e.message);app.quit()}
});
app.on('window-all-closed',()=>app.quit());
app.on('before-quit',event=>{
 if(closing)return;closing=true;
 const cleanup=()=>{try{fs.rmSync(session,{recursive:true,force:true,maxRetries:10,retryDelay:100})}catch(error){console.error(error.message)}};
 if(child&&child.exitCode===null){event.preventDefault();child.once('exit',()=>{cleanup();app.quit()});child.kill()}
 else cleanup();
});
