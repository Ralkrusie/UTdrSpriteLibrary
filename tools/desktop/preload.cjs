const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('spriteDesktop',Object.freeze({
 openExternal:url=>ipcRenderer.invoke('sprite:open-external',url),
 onSaved:callback=>ipcRenderer.on('sprite:saved',(_event,token)=>callback(token)),
 onError:callback=>ipcRenderer.on('sprite:drag-error',(_event,message)=>callback(message)),
 exportPackage:id=>ipcRenderer.invoke('sprite:export-package',id),
 pick:kind=>ipcRenderer.invoke('sprite:pick',kind),
 prepare:request=>ipcRenderer.invoke('sprite:prepare',request),
 drag:token=>ipcRenderer.send('sprite:drag',token),
 reveal:token=>ipcRenderer.invoke('sprite:reveal',token)
}));
