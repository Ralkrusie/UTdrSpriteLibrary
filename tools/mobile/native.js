export const isAndroid=!!window.AndroidExports;
let transferring=false;
export async function nativeExport(blob,name,action){
 if(transferring)throw Error('请等待当前文件处理完成');
 transferring=true;
 try{
  if(blob.size>80*1024*1024)throw Error('文件过大，请减少本批内容');
  const token=AndroidExports.begin(name);
  for(let offset=0;offset<blob.size;offset+=49152){
   const bytes=new Uint8Array(await blob.slice(offset,offset+49152).arrayBuffer());
   let binary='';for(const byte of bytes)binary+=String.fromCharCode(byte);
   if(!AndroidExports.append(token,btoa(binary)))throw Error('文件写入失败');
  }
  if(!AndroidExports.finish(token,action))throw Error('无法完成操作');
 }finally{transferring=false}
}
