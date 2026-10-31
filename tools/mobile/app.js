import {isAndroid,nativeExport} from './native.js';
import {SpriteArchive} from './archive.js';
import {storage} from './storage.js';
import {apng,zip} from './encode.js';
import {gif} from './gif.js';
const $=id=>document.getElementById(id),scales=[1,2,3,4,5,6,7,8,9,10,15,20],pageSize=36;
let all=[],filtered=[],page=0,selected=new Set(),active=null,images=[],frame=0,playing=false,raf=0,epoch=0,generation=0,busy=false,cancelled=false,downloadURLs=[];
let archive=null,packId='',favorites=new Set(),settings={},packBusy=false;
const node=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e};
async function detail(v){return v}
async function loadImage(path){if(!path)throw Error('此资源存在缺失帧');const source=archive,url=await source.image(path),i=new Image();try{i.src=url;await i.decode();return i}finally{URL.revokeObjectURL(url)}}
async function thumbnail(img,path,source){try{const url=await source.image(path);if(!img.isConnected){URL.revokeObjectURL(url);return}img.onload=img.onerror=()=>URL.revokeObjectURL(url);img.src=url}catch{img.alt='图片读取失败'}}
function saveSettings(){storage('settings','put',settings,'ui').catch(()=>{$('pack-status').textContent='设置保存失败，请检查存储空间'})}
function favorite(id){favorites.has(id)?favorites.delete(id):favorites.add(id);storage('settings','put',[...favorites],'favorites:'+packId).catch(()=>{$('pack-status').textContent='收藏保存失败'});if($('favorites').checked)filter();else render();if(active)$('favorite-detail').textContent=favorites.has(active.id)?'★':'☆'}
function scaleValue(prefix=''){return +$(prefix+'scale').value || +$(prefix+'custom-scale').value}
function fps(prefix=''){const mode=$(prefix?prefix+'-speed':'speed').value;return mode==='custom'?+$(prefix?prefix+'-fps':'fps').value:+mode}
const historyKey='sprites-'+Date.now();
function showPanel(id){$(id).showModal();try{history.pushState({spritePage:historyKey,layer:id},'')}catch{}}
function closePanel(id){if(history.state?.spritePage===historyKey&&history.state.layer===id)history.back();else $(id).close()}
addEventListener('popstate',event=>{const layer=event.state?.spritePage===historyKey?event.state.layer:null;if($('job').open&&layer!=='job'){cancelled=true;$('job').close()}if($('detail').open&&!['detail','job'].includes(layer))$('detail').close()});
function pause(){playing=false;cancelAnimationFrame(raf);$('play').textContent='播放'}
function fitPreview(){
 const c=$('canvas'),stage=c.parentElement;if(!active||!c.width||!c.height)return;
 const style=getComputedStyle(stage),width=stage.clientWidth-parseFloat(style.paddingLeft)-parseFloat(style.paddingRight),height=stage.clientHeight-parseFloat(style.paddingTop)-parseFloat(style.paddingBottom);
 let ratio=Math.min(width/c.width,height/c.height);if(ratio<=0)return;
 if(ratio>=1)ratio=Math.max(1,Math.floor(ratio));
 c.style.width=Math.max(1,Math.floor(c.width*ratio))+'px';c.style.height=Math.max(1,Math.floor(c.height*ratio))+'px';
}
new ResizeObserver(fitPreview).observe($('canvas').parentElement);
function paint(){if(!active||!images.length)return;const c=$('canvas'),ctx=c.getContext('2d');ctx.clearRect(0,0,c.width,c.height);ctx.drawImage(images[frame],0,0);const scale=scaleValue();if(!Number.isFinite(scale)||scale<.25||scale>20){$('dimensions').textContent='缩放范围为 0.25–20×';return}fitPreview();$('dimensions').textContent=`${c.width} × ${c.height} px · 预览自动适应 · 导出 ${scale}×：${Math.max(1,Math.round(c.width*scale))} × ${Math.max(1,Math.round(c.height*scale))} px`;$('scrub').value=frame;$('frame').textContent=`${frame+1} / ${images.length}`}
function play(){pause();const rate=fps();if(!images.length||!Number.isFinite(rate)||rate<.1||rate>120)return;paint();playing=true;$('play').textContent='暂停';epoch=performance.now()-frame*1000/rate;const tick=t=>{if(!playing)return;const next=Math.floor(Math.max(0,t-epoch)*rate/1000)%images.length;if(next!==frame){frame=next;paint()}raf=requestAnimationFrame(tick)};raf=requestAnimationFrame(tick)}
function selection(){$('selected').textContent=selected.size+' 项';$('export-batch').disabled=!selected.size||busy}
function filter(){const q=$('search').value.trim().toLowerCase(),ch=+$('chapter').value,counts=new Map();all.forEach(v=>counts.set(v.name,(counts.get(v.name)||0)+1));filtered=all.filter(v=>(!q||v.name.toLowerCase().includes(q))&&(!ch||v.chapters.includes(ch))&&(!$('multi').checked||v.count>1)&&(!$('different').checked||counts.get(v.name)>1)&&(!$('favorites').checked||favorites.has(v.id)));page=0;render()}
function render(){const pages=Math.max(1,Math.ceil(filtered.length/pageSize));$('status').textContent=`${filtered.length.toLocaleString()} 个变体`;$('page').textContent=`${page+1} / ${pages}`;$('prev').disabled=page===0;$('next').disabled=page+1===pages;$('grid').replaceChildren();for(const v of filtered.slice(page*pageSize,(page+1)*pageSize)){const card=node('article');card.className='card'+(favorites.has(v.id)?' favorite':'');const label=node('label'),check=node('input');check.type='checkbox';check.checked=selected.has(v.id);check.disabled=!v.complete;check.setAttribute('aria-label','选择 '+v.name);check.onchange=()=>{check.checked?selected.add(v.id):selected.delete(v.id);selection()};label.append(check,node('span',`${v.chapters.length?'Ch'+v.chapters.join('/'):'UT'} · ${v.count} 帧`));const star=node('button',favorites.has(v.id)?'★':'☆');star.className='star';star.setAttribute('aria-label','收藏 '+v.name);star.setAttribute('aria-pressed',favorites.has(v.id));star.onclick=()=>favorite(v.id);const top=node('div');top.className='card-top';top.append(label,star);const button=node('button'),thumb=node('div');thumb.className='thumb';if(v.thumbnail){const img=node('img');thumbnail(img,v.thumbnail,archive);img.loading='lazy';img.alt='';thumb.append(img)}button.append(thumb,node('div',v.name));button.onclick=()=>open(v);card.append(top,button);$('grid').append(card)}selection()}
async function open(v){pause();const token=++generation;active=null;images=[];$('export').disabled=true;$('name').textContent=v.name;$('detail-status').textContent='正在读取帧…';$('canvas').width=1;$('canvas').height=1;showPanel('detail');try{const d=await detail(v);if(d.previewPixels>16000000)throw Error('此资源过大，请使用 桌面版预览');const loaded=[];for(const path of d.frames){if(token!==generation)return;loaded.push(await loadImage(path))}if(token!==generation)return;active=d;images=loaded;frame=0;$('canvas').width=images[0].naturalWidth||images[0].width;$('canvas').height=images[0].naturalHeight||images[0].height;$('favorite-detail').textContent=favorites.has(v.id)?'★':'☆';$('scrub').max=images.length-1;$('detail-status').textContent='';$('export').disabled=!d.complete;paint();play()}catch(e){if(token===generation)$('detail-status').textContent=e.message}}
function abort(){if(cancelled)throw Error('已取消')}
async function exportItems(items,format,scale,rate,current){if(busy)return;if(!Number.isFinite(scale)||scale<.25||scale>20){$('detail-status').textContent=$('status').textContent='缩放范围为 0.25–20×';return}if(!Number.isFinite(rate)||rate<.1||rate>120){$('detail-status').textContent=$('status').textContent='FPS 范围为 0.1–120';return}pause();busy=true;cancelled=false;selection();showPanel('job');$('save-all').hidden=true;$('downloads').replaceChildren();$('job-close').hidden=true;$('cancel').hidden=false;for(const url of downloadURLs)URL.revokeObjectURL(url);downloadURLs=[];
 try{
  if(items.length>50)throw Error('手机端每批最多 50 个精灵，请减少勾选');
  let pixels=0;for(const v of items){if(!v.complete)throw Error(v.name+' 存在缺失帧');if(v.previewPixels>16000000)throw Error('此资源原始帧过大，请使用桌面版');pixels+=v.width*v.height*scale*scale*(format==='png'?1:v.count);if(v.width*scale>8192||v.height*scale>8192)throw Error('尺寸过大，请降低缩放')}
  if(pixels>16000000)throw Error('本批导出超过手机处理上限，请降低缩放或减少勾选');
  const files=[];let totalBytes=0,done=0;const total=items.reduce((n,v)=>n+(format==='png'?1:v.count),0);$('progress').max=total;$('progress').value=0;
  for(const v of items){abort();const d=await detail(v),indices=format==='png'?[current]:d.frames.map((_,i)=>i),pngs=[],gifFrames=[],prefix=v.name.replace(/[<>:"/\\|?*\x00-\x1f]/g,'_')+'_'+(v.chapters.length?'Ch'+v.chapters.join('-'):'UT')+(format==='gif'||format==='apng'?'_'+rate+'fps':'')+'_'+scale+'x';const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(v.width*scale));canvas.height=Math.max(1,Math.round(v.height*scale));const ctx=canvas.getContext('2d');ctx.imageSmoothingEnabled=false;
   for(const i of indices){abort();$('job-status').textContent=`正在处理 ${++done}/${total} · ${v.name}`;const image=await loadImage(d.frames[i]);abort();ctx.clearRect(0,0,canvas.width,canvas.height);ctx.drawImage(image,0,0,canvas.width,canvas.height);if(format==='gif')gifFrames.push(ctx.getImageData(0,0,canvas.width,canvas.height).data);const blob=await new Promise(r=>canvas.toBlob(r,'image/png'));if(!blob)throw Error('浏览器无法生成此尺寸的图片');totalBytes+=blob.size;if(totalBytes>64000000)throw Error('导出文件过大，请减少本批内容');if(format==='apng')pngs.push(new Uint8Array(await blob.arrayBuffer()));else if(format!=='gif')files.push({name:prefix+'_'+String(i).padStart(4,'0')+'.png',blob});$('progress').value=done;await new Promise(r=>setTimeout(r,0))}
   if(format==='apng')files.push({name:prefix+'.png',blob:apng(pngs,rate)});if(format==='gif')files.push({name:prefix+'.gif',blob:gif(gifFrames,canvas.width,canvas.height,rate)});canvas.width=canvas.height=1;
  }
  abort();const used=new Set();for(const file of files){const original=file.name;let n=2;while(used.has(file.name))file.name=original.replace(/(\.[^.]+)$/,'_'+n+++'$1');used.add(file.name)}if(files.length>1)files.splice(0,files.length,{name:'UTdrSpriteLibrary-export.zip',blob:await zip(files)});for(const file of files){const url=URL.createObjectURL(file.blob);downloadURLs.push(url);const link=node('a','保存 '+file.name);link.href=url;link.download=file.name;link.className='save-file';if(isAndroid)link.onclick=e=>{e.preventDefault();nativeExport(file.blob,file.name,'save').catch(e=>{$('job-status').textContent=e.message})};$('downloads').append(link);const share=node('button','分享文件');const f=new File([file.blob],file.name,{type:file.blob.type});if(isAndroid||navigator.canShare?.({files:[f]})){share.onclick=()=>(isAndroid?nativeExport(file.blob,file.name,'share'):navigator.share({files:[f]})).catch(e=>{if(e.name!=='AbortError')$('job-status').textContent='分享失败，可使用保存链接'});$('downloads').append(share)}}
  $('save-all').hidden=files.length<2;$('job-status').textContent=`已生成 ${files.length} 个文件。`;

 }catch(e){$('job-status').textContent=e.message}finally{busy=false;selection();$('cancel').hidden=true;$('job-close').hidden=false}
}
for(const id of ['scale','batch-scale'])for(const n of scales){const o=node('option',n+'×');o.value=n;$(id).append(o);$(id).value='5'}
for(const prefix of ['','batch-']){const speed=$(prefix+'speed'),custom=$(prefix+'fps');speed.onchange=()=>{custom.hidden=speed.value!=='custom';if(!prefix)play()};custom.oninput=()=>{if(!prefix)play()}}
$('play').onclick=()=>playing?pause():play();$('scale').onchange=paint;$('scrub').oninput=()=>{pause();frame=+$('scrub').value;paint()};for(const [id,delta]of[['back',-1],['forward',1]])$(id).onclick=()=>{if(!images.length)return;pause();frame=(frame+delta+images.length)%images.length;paint()};$('close').onclick=()=>closePanel('detail');$('detail').oncancel=e=>{e.preventDefault();closePanel('detail')};$('detail').onclose=()=>{generation++;pause();images=[];active=null};let resumePlayback=false;document.addEventListener('visibilitychange',()=>{if(document.hidden){resumePlayback=playing;pause()}else if(resumePlayback&&$('detail').open&&!$('job').open){resumePlayback=false;play()}});
$('export').onclick=()=>active&&exportItems([active],$('format').value,scaleValue(),fps(),frame);$('export-batch').onclick=()=>exportItems(all.filter(v=>selected.has(v.id)),$('batch-format').value,scaleValue('batch-'),fps('batch'));$('cancel').onclick=()=>{cancelled=true;$('job-status').textContent='正在取消…'};$('job').oncancel=e=>{e.preventDefault();cancelled=true;closePanel('job')};$('job-close').onclick=()=>closePanel('job');$('save-all').onclick=async()=>{const links=[...$('downloads').querySelectorAll('a')];$('save-all').disabled=true;for(const link of links){if(!$('job').open)break;link.click();await new Promise(r=>setTimeout(r,350))}$('save-all').disabled=false;$('job-status').textContent='已请求逐张下载；若浏览器拦截，可点击下方单张保存。'};$('select-page').onclick=()=>{filtered.slice(page*pageSize,(page+1)*pageSize).filter(v=>v.complete).forEach(v=>selected.add(v.id));render()};$('clear').onclick=()=>{selected.clear();render()};$('prev').onclick=()=>{page--;render()};$('next').onclick=()=>{page++;render()};for(const id of ['search','chapter','multi','different','favorites'])$(id).addEventListener(id==='search'?'input':'change',filter);

async function mount(record){
 const candidate=await SpriteArchive.open(record.file),savedFavorites=await storage('settings','get','favorites:'+record.id);
 pause();generation++;active=null;images=[];selected.clear();archive=candidate;packId=record.id;favorites=new Set(savedFavorites||[]);all=archive.all;
 $('chapter').replaceChildren(new Option('全部章节','0'));for(const ch of [...new Set(all.flatMap(v=>v.chapters))].sort((a,b)=>a-b))$('chapter').append(new Option('第 '+ch+' 章',ch));
 $('pack-status').textContent=[archive.meta.game,archive.meta.version,archive.meta.language].filter(Boolean).join(' · ');settings.pack=packId;saveSettings();filter();
}
async function packList(){const records=await storage('packs','getAll');$('packs').replaceChildren(...records.map(p=>new Option(p.name,p.id)));$('packs').value=packId;$('packs').disabled=!records.length;$('remove-pack').disabled=!records.length;return records}
async function importPack(file){if(packBusy||!file)return;packBusy=true;$('import-pack').disabled=true;$('packs').disabled=true;$('remove-pack').disabled=true;
 try{$('pack-status').textContent='正在校验素材包…';const candidate=await SpriteArchive.open(file);const started=performance.now();await candidate.verify((n,total)=>{$('pack-status').textContent=`校验 ${Math.floor(n/total*100)}% · ${n.toLocaleString()} / ${total.toLocaleString()} · ${Math.floor((performance.now()-started)/1000)} 秒`});$('pack-status').textContent='校验完成，正在保存到本机…';
 let record=await storage('packs','get',candidate.id),duplicate=!!record;
 if(!record){record={id:candidate.id,name:candidate.meta.name,file};await storage('packs','put',record)}
 await mount(record);await packList();if(duplicate)$('pack-status').textContent+=' · 此素材包已导入';navigator.storage?.persist?.().catch(()=>{});
 }catch(e){$('pack-status').textContent=e.name==='QuotaExceededError'?'空间不足，请移除不用的素材包后重试':e.message}finally{packBusy=false;$('import-pack').disabled=false;$('pack-input').value='';await packList()}
}
$('import-pack').onclick=()=>$('pack-input').click();$('pack-input').onchange=e=>importPack(e.target.files[0]);
$('packs').onchange=async()=>{if(packBusy)return;packBusy=true;try{await mount(await storage('packs','get',$('packs').value))}catch(e){$('pack-status').textContent=e.message}finally{packBusy=false}};
$('remove-pack').onclick=async()=>{if(packBusy||!packId||!confirm('移除此设备保存的素材包？原始 ZIP 和收藏会保留。'))return;packBusy=true;try{await storage('packs','delete',packId);archive=null;packId='';all=[];selected.clear();filter();const records=await packList();if(records.length)await mount(records[0]);else{$('pack-status').textContent='导入桌面版导出的 ZIP 素材包';settings.pack='';saveSettings()}await packList()}catch(e){$('pack-status').textContent=e.message}finally{packBusy=false}};
$('favorite-detail').onclick=()=>active&&favorite(active.id);
const remember=['scale','custom-scale','speed','fps','format','batch-scale','batch-custom-scale','batch-speed','batch-fps','batch-format','card-size','multi','different','favorites'];
for(const prefix of ['','batch-']){
 const option=new Option('自定义缩放','custom');$(prefix+'scale').append(option);
 $(prefix+'scale').addEventListener('change',()=>{$(prefix+'custom-scale').hidden=$(prefix+'scale').value!=='custom';if(!prefix)paint()});
 $(prefix+'custom-scale').oninput=()=>{if(!prefix)paint()};
}
function cardSize(){document.documentElement.style.setProperty('--card-size',$('card-size').value+'px')}
for(const id of remember)$(id).addEventListener('change',()=>{const e=$(id);if(e.type==='number'&&(!e.value||!e.checkValidity()))return;settings[id]=e.type==='checkbox'?e.checked:e.value;saveSettings();if(id==='card-size')cardSize()});
if(!isAndroid){
let installPrompt;
addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;$('install').hidden=false});
$('install').onclick=async()=>{await installPrompt?.prompt();installPrompt=null;$('install').hidden=true};
}
async function init(){
 $('retry').hidden=true;
 try{settings=await storage('settings','get','ui')||{};for(const id of remember)if(settings[id]!==undefined){const e=$(id);if(e.type==='checkbox')e.checked=settings[id];else e.value=settings[id]}
 for(const prefix of ['','batch-']){$(prefix+'fps').hidden=$(prefix+'speed').value!=='custom';$(prefix+'custom-scale').hidden=$(prefix+'scale').value!=='custom'}cardSize();
 const records=await packList(),record=records.find(r=>r.id===settings.pack)||records[0];if(record){await mount(record);await packList()}else filter();
 }catch(e){$('pack-status').textContent='本地存储不可用：'+e.message}
 if(isAndroid){document.querySelector('body > footer')?.remove();return}
 if('serviceWorker' in navigator&&isSecureContext){try{await navigator.serviceWorker.register('./sw.js');await navigator.serviceWorker.ready;$('offline-status').textContent='离线资源已就绪 · 可添加到主屏幕'}catch{$('offline-status').textContent='离线资源准备失败，请联网刷新重试'}}else $('offline-status').textContent='请通过 HTTPS 打开，以启用安装和离线';
}
init();

document.getElementById('open-help').onclick=()=>document.getElementById('help').showModal();
document.getElementById('close-help').onclick=()=>document.getElementById('help').close();
