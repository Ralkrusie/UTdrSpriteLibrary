// GIF89a: exact per-frame palettes up to 255 opaque colors, RGB cube fallback.
// Literal LZW blocks reset before the 9-bit dictionary grows: bounded memory.
export function gif(frames,width,height,fps){
 if(!frames.length||!Number.isFinite(fps)||fps<.1||fps>120)throw Error('GIF 参数无效');
 const parts=[],u16=n=>[n&255,n>>8&255],text=s=>Array.from(s,c=>c.charCodeAt(0));
 parts.push(new Uint8Array([...text('GIF89a'),...u16(width),...u16(height),0x80,0,0,0,0,0,0,0,0,0x21,0xff,11,...text('NETSCAPE2.0'),3,1,0,0,0]));
 for(let f=0;f<frames.length;f++){
  const rgba=frames[f],colors=new Map();
  for(let p=0;p<rgba.length;p+=4)if(rgba[p+3]>=128){const rgb=rgba[p]<<16|rgba[p+1]<<8|rgba[p+2];if(!colors.has(rgb))colors.set(rgb,colors.size+1);if(colors.size>255)break}
  const palette=new Uint8Array(768),indices=new Uint8Array(width*height),exact=colors.size<=255;
  if(exact){for(const [rgb,i] of colors){palette[i*3]=rgb>>16;palette[i*3+1]=rgb>>8;palette[i*3+2]=rgb}}
  else for(let r=0;r<6;r++)for(let g=0;g<6;g++)for(let b=0;b<6;b++){const i=1+r*36+g*6+b;palette.set([r*51,g*51,b*51],i*3)}
  for(let i=0,p=0;i<indices.length;i++,p+=4)if(rgba[p+3]>=128)indices[i]=exact?colors.get(rgba[p]<<16|rgba[p+1]<<8|rgba[p+2]):1+Math.round(rgba[p]/51)*36+Math.round(rgba[p+1]/51)*6+Math.round(rgba[p+2]/51);
  const delay=Math.max(1,Math.round((f+1)*100/fps)-Math.round(f*100/fps));
  parts.push(new Uint8Array([0x21,0xf9,4,9,...u16(delay),0,0,0x2c,0,0,0,0,...u16(width),...u16(height),0x87]),palette);
  const bytes=new Uint8Array(Math.ceil((indices.length+Math.ceil(indices.length/200)+1)*9/8));let used=0,bits=0,acc=0;const code=n=>{acc|=n<<bits;bits+=9;while(bits>=8){bytes[used++]=acc&255;acc>>>=8;bits-=8}};
  for(let p=0;p<indices.length;p+=200){code(256);for(let i=p;i<Math.min(p+200,indices.length);i++)code(indices[i])}code(257);if(bits)bytes[used++]=acc&255;
  const blocks=new Uint8Array(2+used+Math.ceil(used/255));blocks[0]=8;let at=1;for(let p=0;p<used;p+=255){const n=Math.min(255,used-p);blocks[at++]=n;blocks.set(bytes.subarray(p,p+n),at);at+=n}parts.push(blocks);
 }
 parts.push(new Uint8Array([0x3b]));return new Blob(parts,{type:'image/gif'});
}
