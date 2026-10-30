const assert=require('node:assert/strict'),path=require('node:path');
const {layout,picker}=require('./platform.cjs');
const root=path.resolve('releases/test-layout'),appData=path.join(root,'用户配置');
for(const platform of ['win32','darwin','linux']){
 const resourcesPath=platform==='darwin'?path.join(root,'工具.app/Contents/Resources'):path.join(root,'resources');
 const appDir=path.join(resourcesPath,'app');
 const result=layout({platform,appDir,resourcesPath,appData});
 assert.equal(result.backend,path.join(platform==='darwin'?resourcesPath:root,'backend'));
 assert.equal(result.executable,path.join(result.backend,'UTdrSpriteBackend'+(platform==='win32'?'.exe':'')));
 assert.equal(result.data,platform==='win32'?path.join(root,'data'):path.join(appData,'UTdrSpriteLibrary'));
 assert(!picker('game',platform).properties.includes('createDirectory'));
 assert.equal(picker('game',platform).properties.includes('treatPackageAsDirectory'),platform==='darwin');
 assert.equal(!!picker('umt',platform).filters,platform==='win32');
 assert.deepEqual(picker('package',platform).filters[0].extensions,['zip']);
 assert.equal(layout({platform,appDir,resourcesPath,appData,dataDir:root}).data,root);
 assert.throws(()=>layout({platform,appDir,resourcesPath,appData,dataDir:'relative'}),/absolute/);
}
console.log('PASS desktop platform layout, portable data and native file pickers');
