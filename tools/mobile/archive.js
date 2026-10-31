import {crc} from './encode.js';
const text = new TextDecoder('utf-8', {fatal:true});
const hex = bytes => Array.from(new Uint8Array(bytes), b=>b.toString(16).padStart(2,'0')).join('');
const digest = bytes => crypto.subtle.digest('SHA-256', bytes);
const validPath = name => /^(manifest\.json|catalog\.json|images\/[A-Za-z0-9_./-]+\.png)$/.test(name) && !name.split('/').some(p=>!p || p==='.' || p==='..');
export class SpriteArchive {
 constructor(file, entries, offset){Object.assign(this,{file,entries,offset})}
 static async open(file){
  if(file.size>512*1024*1024)throw Error('手机版暂支持 512 MiB 以内的素材包');
  const tail=new Uint8Array(await file.slice(Math.max(0,file.size-65557)).arrayBuffer()),view=new DataView(tail.buffer);let end=-1;
  for(let i=tail.length-22;i>=0;i--)if(view.getUint32(i,true)===0x06054b50&&i+22+view.getUint16(i+20,true)===tail.length){end=i;break}
  if(end<0)throw Error('不是完整的 ZIP 文件');
  const count=view.getUint16(end+10,true),length=view.getUint32(end+12,true),offset=view.getUint32(end+16,true);
  if(view.getUint16(end+4,true)||view.getUint16(end+6,true)||view.getUint16(end+8,true)!==count||count===65535||length>16000000||offset+length>file.size-tail.length+end)throw Error('不支持多卷或 ZIP64 素材包');
  const bytes=new Uint8Array(await file.slice(offset,offset+length).arrayBuffer()),dv=new DataView(bytes.buffer),entries=new Map();let p=0,total=0;
  for(let n=0;n<count;n++){
   if(p+46>bytes.length||dv.getUint32(p,true)!==0x02014b50)throw Error('ZIP 目录损坏');
   const names=dv.getUint16(p+28,true),extra=dv.getUint16(p+30,true),comment=dv.getUint16(p+32,true),size=dv.getUint32(p+24,true),packed=dv.getUint32(p+20,true),start=dv.getUint32(p+42,true),method=dv.getUint16(p+10,true);
   if(p+46+names+extra+comment>bytes.length)throw Error('ZIP 目录不完整');
   const name=text.decode(bytes.subarray(p+46,p+46+names));
   if(!validPath(name)||entries.has(name)||dv.getUint16(p+8,true)&1||![0,8].includes(method)||dv.getUint16(p+34,true)||start+30+packed>offset||size>(name==='catalog.json'?64:16)*1024*1024)throw Error('ZIP 路径、压缩方式或大小无效');
   total+=size;if(total>1024*1024*1024)throw Error('手机版暂支持解压后 1 GiB 以内的素材包');
   entries.set(name,{size,packed,start,method,crc:dv.getUint32(p+16,true)});p+=46+names+extra+comment;
  }
  if(p!==bytes.length)throw Error('ZIP 目录长度无效');
  const archive=new SpriteArchive(file,entries,offset),meta=await archive.json('manifest.json'),catalog=await archive.json('catalog.json');
  if(meta.format!=='UTdrSpriteLibrary'||meta.schema!==1||!['UT','DR'].includes(meta.game)||!['name','version','language'].every(k=>typeof meta[k]==='string'&&meta[k].length<=500)||!meta.name.trim()||!Array.isArray(meta.sources))throw Error('请选择桌面版导出的 v1 ZIP 素材包');
  const all=[],ids=new Set();archive.refs=new Map();
  if(!Array.isArray(catalog.items))throw Error('素材目录无效');
  for(const group of catalog.items){if(group.kind!=='sprite')continue;if(!Array.isArray(group.variants))throw Error('素材变体无效');for(const v of group.variants){
   if(!/^[a-f0-9]{64}$/.test(v.id)||ids.has(v.id)||typeof v.name!=='string'||!Array.isArray(v.chapters)||v.chapters.some(n=>!Number.isInteger(n)||n<1)||!Array.isArray(v.frames)||v.frames.length>10000||!['width','height'].every(k=>Number.isInteger(v[k])&&v[k]>0&&v[k]<=32768))throw Error('素材条目无效');
   ids.add(v.id);const frames=v.frames.map(f=>{if(!f.image)return null;if(!entries.has(f.image)||!f.image.startsWith('images/')||!['width','height'].every(k=>Number.isInteger(f[k])&&f[k]>0&&f[k]<=32768))throw Error('素材缺帧或尺寸无效');const shape=[f.width,f.height];if(archive.refs.has(f.image)&&String(archive.refs.get(f.image))!==String(shape))throw Error('帧尺寸冲突');archive.refs.set(f.image,shape);return f.image});
   all.push({...v,previewPixels:v.frames.reduce((n,f)=>n+(f.image?f.width*f.height:0),0),frames,count:frames.length,complete:!!frames.length&&frames.every(Boolean),thumbnail:frames.find(Boolean)});
  }}
  if(meta.sources.some(s=>!s||typeof s.file!=='string'||! /^[a-f0-9]{64}$/.test(s.sha256)))throw Error('来源摘要无效');
  if(!all.length)throw Error('素材包没有精灵');Object.assign(archive,{meta,all});return archive;
 }
 async read(start,end){
  if(!this.blocks)return new Uint8Array(await this.file.slice(start,end).arrayBuffer());
  const blockSize=2*1024*1024,parts=[];
  for(let position=start;position<end;){
   const index=Math.floor(position/blockSize),limit=Math.min(end,(index+1)*blockSize);
   if(!this.blocks.has(index)){
    this.blocks.set(index,this.file.slice(index*blockSize,(index+1)*blockSize).arrayBuffer());
    // Bounded read-ahead cache. Four nearby entries share the same reads.
    while(this.blocks.size>4)this.blocks.delete(this.blocks.keys().next().value);
   }
   const bytes=new Uint8Array(await this.blocks.get(index));
   parts.push(bytes.subarray(position-index*blockSize,limit-index*blockSize));position=limit;
  }
  if(parts.length===1)return parts[0];
  const result=new Uint8Array(end-start);let offset=0;for(const part of parts){result.set(part,offset);offset+=part.length}return result;
 }
 async bytes(name){
  const e=this.entries.get(name);if(!e)throw Error('缺少文件：'+name);
  const header=await this.read(e.start,e.start+30),h=new DataView(header.buffer,header.byteOffset,header.byteLength);
  if(h.byteLength!==30||h.getUint32(0,true)!==0x04034b50||h.getUint16(8,true)!==e.method||h.getUint16(6,true)&1)throw Error('ZIP 文件头无效');
  const start=e.start+30+h.getUint16(26,true)+h.getUint16(28,true);
  if(start+e.packed>this.offset||text.decode(await this.read(e.start+30,e.start+30+h.getUint16(26,true)))!==name)throw Error('ZIP 文件边界无效');
  const packed=await this.read(start,start+e.packed);let data;
  if(e.method===8){
   let ds;try{ds=new DecompressionStream('deflate-raw')}catch{throw Error('浏览器不支持 ZIP 解压，请更新 Safari／Chrome')}
   const reader=new Blob([packed]).stream().pipeThrough(ds).getReader(),parts=[];let size=0;
   try{while(true){const {value,done}=await reader.read();if(done)break;size+=value.length;if(size>e.size){await reader.cancel();throw Error('解压大小超限')}parts.push(value)}}finally{reader.releaseLock()}
   data=new Uint8Array(await new Blob(parts).arrayBuffer());
  }else data=packed;
  if(data.length!==e.size||crc(data)!==e.crc)throw Error('素材校验失败：'+name);return data;
 }
 async json(name){return JSON.parse(text.decode(await this.bytes(name)))}
 async verify(progress){
  const hashes=new Map(),names=[...this.entries.keys()].sort((a,b)=>this.entries.get(a).start-this.entries.get(b).start);let done=0,next=0,last=0,failure;
  this.blocks=new Map();
  const worker=async()=>{while(!failure&&next<names.length){const name=names[next++];try{
   const data=await this.bytes(name);
   if(name.startsWith('images/')){const d=new DataView(data.buffer,data.byteOffset,data.byteLength);if(data.length<33||d.getUint32(0)!==0x89504e47||d.getUint32(4)!==0x0d0a1a0a||d.getUint32(12)!==0x49484452)throw Error('无效 PNG');const shape=this.refs.get(name);if(shape&&(d.getUint32(16)!==shape[0]||d.getUint32(20)!==shape[1]))throw Error('PNG 尺寸不符')}
   hashes.set(name,new Uint8Array(await digest(data)));done++;
   if(performance.now()-last>100){last=performance.now();progress(done,names.length);await new Promise(r=>setTimeout(r,0))}
  }catch(error){failure=error}}};
  try{
   await Promise.all(Array.from({length:4},worker));if(failure)throw failure;
   const parts=[];for(const name of [...hashes.keys()].sort())parts.push(new TextEncoder().encode(name+'\0'),hashes.get(name));
   this.id=hex(await digest(await new Blob(parts).arrayBuffer()));progress(done,names.length);return this.id;
  }finally{this.blocks=null}
 }
 async image(name){return URL.createObjectURL(new Blob([await this.bytes(name)],{type:'image/png'}))}
}
