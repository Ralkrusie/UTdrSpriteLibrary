const path=require('node:path');

function layout({platform=process.platform,appDir,resourcesPath,appData,dataDir}){
 if(dataDir&&!path.isAbsolute(dataDir))throw Error('UTDR_DATA_DIR must be an absolute path');
 const root=path.resolve(appDir,'../..');
 const backend=platform==='darwin'?path.join(resourcesPath,'backend'):path.join(root,'backend');
 const data=dataDir||(platform==='win32'?path.join(root,'data'):path.join(appData,'UTdrSpriteLibrary'));
 return {root,backend,data,executable:path.join(backend,'UTdrSpriteBackend'+(platform==='win32'?'.exe':''))};
}

function picker(kind,platform=process.platform){
 if(kind==='output')return {properties:['openDirectory','createDirectory']};
 if(kind==='game')return {properties:['openDirectory',...(platform==='darwin'?['treatPackageAsDirectory']:[])]};
 if(kind==='package')return {properties:['openFile'],filters:[{name:'ZIP 素材包',extensions:['zip']}]};
 return {properties:['openFile'],...(platform==='win32'?{filters:[{name:'UTMT CLI',extensions:['exe']}]}:{})};
}

module.exports={layout,picker};
