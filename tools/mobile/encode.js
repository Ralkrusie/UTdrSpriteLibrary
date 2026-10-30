// PNG bytes are produced by canvas; APNG preserves those lossless RGBA frames.
const table=Uint32Array.from({length:256},(_,n)=>{for(let k=0;k<8;k++)n=n&1?0xedb88320^(n>>>1):n>>>1;return n>>>0});
export function crc(bytes){let c=0xffffffff;for(const b of bytes)c=table[(c^b)&255]^(c>>>8);return(c^0xffffffff)>>>0}
const ascii=s=>new TextEncoder().encode(s);
function chunk(name,data){const type=ascii(name),out=new Uint8Array(data.length+12),v=new DataView(out.buffer);v.setUint32(0,data.length);out.set(type,4);out.set(data,8);v.setUint32(out.length-4,crc(out.subarray(4,-4)));return out}
export function apng(frames,fps){
 if(!frames.length||!Number.isFinite(fps)||fps<.1||fps>120)throw Error('FPS 范围为 0.1–120');
 const parts=[frames[0].slice(0,8)];let seq=0;
 const chunks=bytes=>{let list=[];for(let p=8;p<bytes.length;){const n=new DataView(bytes.buffer,bytes.byteOffset+p,4).getUint32(0);list.push([new TextDecoder().decode(bytes.subarray(p+4,p+8)),bytes.slice(p+8,p+8+n)]);p+=12+n}return list};
 const first=chunks(frames[0]),ihdr=first.find(c=>c[0]==='IHDR')[1];parts.push(chunk('IHDR',ihdr));
 const actl=new Uint8Array(8);new DataView(actl.buffer).setUint32(0,frames.length);parts.push(chunk('acTL',actl));
 for(let i=0;i<frames.length;i++){
  const ctl=new Uint8Array(26),v=new DataView(ctl.buffer);v.setUint32(0,seq++);ctl.set(ihdr.slice(0,8),4);v.setUint16(20,Math.round(1000/fps));v.setUint16(22,1000);parts.push(chunk('fcTL',ctl));
  for(const [name,data] of chunks(frames[i]))if(name==='IDAT'){if(!i)parts.push(chunk('IDAT',data));else{const fd=new Uint8Array(data.length+4);new DataView(fd.buffer).setUint32(0,seq++);fd.set(data,4);parts.push(chunk('fdAT',fd))}}
 }
 parts.push(chunk('IEND',new Uint8Array()));return new Blob(parts,{type:'image/png'});
}
export async function zip(files){
 const body=[],directory=[];let offset=0,size=0;
 for(const file of files){const data=new Uint8Array(await file.blob.arrayBuffer()),name=ascii(file.name),sum=crc(data);
  const h=new Uint8Array(30+name.length),v=new DataView(h.buffer);v.setUint32(0,0x04034b50,true);v.setUint16(4,20,true);v.setUint16(6,0x800,true);v.setUint32(14,sum,true);v.setUint32(18,data.length,true);v.setUint32(22,data.length,true);v.setUint16(26,name.length,true);h.set(name,30);body.push(h,data);
  const c=new Uint8Array(46+name.length),d=new DataView(c.buffer);d.setUint32(0,0x02014b50,true);d.setUint16(4,20,true);d.setUint16(6,20,true);d.setUint16(8,0x800,true);d.setUint32(16,sum,true);d.setUint32(20,data.length,true);d.setUint32(24,data.length,true);d.setUint16(28,name.length,true);d.setUint32(42,offset,true);c.set(name,46);directory.push(c);size+=c.length;offset+=h.length+data.length;
 }
 const end=new Uint8Array(22),v=new DataView(end.buffer);v.setUint32(0,0x06054b50,true);v.setUint16(8,files.length,true);v.setUint16(10,files.length,true);v.setUint32(12,size,true);v.setUint32(16,offset,true);return new Blob([...body,...directory,end],{type:'application/zip'});
}
