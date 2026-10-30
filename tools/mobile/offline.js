// Read only the central directory and requested files; never unpack the whole ZIP.
let offlineArchive=null;
class SpriteArchive {
 constructor(file,entries){this.file=file;this.entries=entries}
 static async open(file){
  if(file.size>512*1024*1024)throw Error('素材包过大，请选择随工具提供的素材包.zip');
  const tail=new Uint8Array(await file.slice(Math.max(0,file.size-65557)).arrayBuffer());
  const view=new DataView(tail.buffer);let end=-1;
  for(let i=tail.length-22;i>=0;i--)if(view.getUint32(i,true)===0x06054b50&&i+22+view.getUint16(i+20,true)===tail.length){end=i;break}
  if(end<0)throw Error('不是完整的 ZIP 文件');
  const count=view.getUint16(end+10,true),length=view.getUint32(end+12,true),offset=view.getUint32(end+16,true);
  if(view.getUint16(end+4,true)||view.getUint16(end+6,true)||count>60000||length>16000000||offset+length>file.size-tail.length+end)throw Error('不支持此素材包结构');
  const bytes=new Uint8Array(await file.slice(offset,offset+length).arrayBuffer()),dv=new DataView(bytes.buffer),entries=new Map();let p=0;
  for(let n=0;n<count;n++){
   if(p+46>bytes.length||dv.getUint32(p,true)!==0x02014b50)throw Error('素材包目录损坏');
   const names=dv.getUint16(p+28,true),extra=dv.getUint16(p+30,true),comment=dv.getUint16(p+32,true),size=dv.getUint32(p+24,true),packed=dv.getUint32(p+20,true),start=dv.getUint32(p+42,true);
   if(p+46+names+extra+comment>bytes.length||dv.getUint16(p+10,true)!==0||dv.getUint16(p+8,true)&1||size!==packed||size>16000000||start+30+packed>offset)throw Error('请使用原始素材包，不要重新压缩');
   const name=new TextDecoder().decode(bytes.subarray(p+46,p+46+names));
   if(entries.has(name))throw Error('素材包存在重复文件');entries.set(name,{size,start,crc:dv.getUint32(p+16,true)});p+=46+names+extra+comment;
  }
  const archive=new SpriteArchive(file,entries),meta=await archive.json('offline-pack.json');
  if(meta.format!=='deltarune-sprites-offline'||meta.version!==1)throw Error('不是本工具的素材包');
  return archive;
 }
 async bytes(name){
  const e=this.entries.get(name);if(!e)throw Error('素材包缺少文件：'+name);
  const h=new DataView(await this.file.slice(e.start,e.start+30).arrayBuffer());
  if(h.byteLength!==30||h.getUint32(0,true)!==0x04034b50)throw Error('素材文件头损坏');
  const start=e.start+30+h.getUint16(26,true)+h.getUint16(28,true);
  const data=new Uint8Array(await this.file.slice(start,start+e.size).arrayBuffer());
  if(data.length!==e.size||crc(data)!==e.crc)throw Error('素材校验失败：'+name);return data;
 }
 async json(name){return JSON.parse(new TextDecoder().decode(await this.bytes(name)))}
 async image(name){return URL.createObjectURL(new Blob([await this.bytes(name)],{type:'image/png'}))}
}
async function offlineThumbnail(img,path){
 try{const url=await offlineArchive.image(path);if(!img.isConnected){URL.revokeObjectURL(url);return}img.onload=img.onerror=()=>URL.revokeObjectURL(url);img.src=url}catch(e){img.alt='图片读取失败';img.title=e.message}
}
function mountOffline(){
 filter();
 $('status').textContent='请先选择素材包';$('retry').hidden=true;
 $('choose-pack').onclick=()=>{$('pack-input').value='';$('pack-input').click()};
 $('pack-input').onchange=async event=>{
  const file=event.target.files[0];if(!file)return;
  $('pack-input').disabled=true;$('pack-status').textContent='正在读取素材目录…';pause();generation++;active=null;images=[];all=[];shards.clear();selected.clear();filter();
  try{const archive=await SpriteArchive.open(file);const index=await archive.json('data/index.json');if(!Array.isArray(index)||!index.every(v=>typeof v.name==='string'&&Array.isArray(v.chapters)&&typeof v.shard==='string'))throw Error('素材目录格式错误');offlineArchive=archive;all=index;filter();$('choose-pack').textContent='更换素材包';$('pack-status').textContent=`已载入 ${file.name} · ${all.length.toLocaleString()} 个变体`;}
  catch(e){offlineArchive=null;$('pack-status').textContent=e.message;$('status').textContent='请重新选择素材包'}
  finally{$('pack-input').disabled=false;event.target.value=''}
 };
}
