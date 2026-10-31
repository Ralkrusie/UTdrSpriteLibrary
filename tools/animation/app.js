'use strict';
const $=id=>document.getElementById(id);let all=[],filtered=[],page=0,selected=new Set(),active=null,images=[],playing=false,frame=0,start=0,raf=0,ticket=0,jobId=null;
const size=48;
let selectionAnchor=null,favoriteAnchor=null,favoriteBusy=false;
function rangeIds(id,anchor,shift){const to=filtered.findIndex(v=>v.id===id),from=shift?filtered.findIndex(v=>v.id===anchor):-1;return from<0||to<0?[id]:filtered.slice(Math.min(from,to),Math.max(from,to)+1).map(v=>v.id)}
function selectRange(id,enabled,shift){const items=new Map(all.map(v=>[v.id,v]));for(const key of rangeIds(id,selectionAnchor,shift)){const v=items.get(key);if(v&&eligible(v)){enabled?selected.add(key):selected.delete(key)}}selectionAnchor=id;render()}
function el(t,text,cls){let e=document.createElement(t);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e}
async function api(path,body){const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const d=await r.json();if(!r.ok)throw Error(d.error||r.statusText);return d}
function setFavoriteIcon(button,enabled){
 button.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 1.5 15.3 8.2 22.7 9.3 17.35 14.5 18.6 21.9 12 18.4 5.4 21.9 6.65 14.5 1.3 9.3 8.7 8.2Z"/></svg>';
 button.classList.toggle('is-favorite',!!enabled);button.setAttribute('aria-pressed',String(!!enabled));button.setAttribute('aria-label',enabled?'取消收藏':'收藏');button.title=enabled?'取消收藏':'收藏';
}
function jumpPage(){const value=Number($('page-number').value);if(!Number.isFinite(value)||value<1){$('page-number').value=page+1;return}page=Math.min(Math.ceil(filtered.length/size)||1,Math.floor(value))-1;render()}
$('page-number').onchange=jumpPage;$('page-number').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();jumpPage()}};
function scaleValue(detail=false){const prefix=detail?'detail-':'',custom=$(prefix+'scale').value==='custom',input=$(prefix+'custom-scale'),value=custom?input.valueAsNumber:Number($(prefix+'scale').value);return Number.isFinite(value)&&value>=.25&&value<=20?value:null}
function syncScale(detail=false){const prefix=detail?'detail-':'';$(prefix+'custom-scale-label').hidden=$(prefix+'scale').value!=='custom'}
function setScale(value,detail=false){const prefix=detail?'detail-':'',menu=$(prefix+'scale');menu.value=[...menu.options].some(o=>o.value===String(value))?String(value):'custom';$(prefix+'custom-scale').value=value;syncScale(detail)}
// Match the encoder's integer pixel dimensions, including nearest-even rounding.
function scaledPixels(pixels,scale){const n=pixels*scale,whole=Math.floor(n);return Math.max(1,n-whole===.5?whole+whole%2:Math.round(n))}
function options(){return{format:$('format').value,scale:scaleValue(),fps:$('speed-mode').value==='custom'?+$('fps').value:+$('speed-mode').value}}
function eligible(v){return v.complete&&v.count>=($('format').value==='png'?1:2)}
function detailEligible(){return active&&scaleValue(true)!==null&&images.length>=($('detail-format').value.startsWith('png')?1:2)&&!images.some(i=>!i)}
function filter(keepPage=false){let q=$('search').value.toLowerCase().trim(),ch=+$('chapter').value;const counts=new Map();all.forEach(v=>counts.set(v.name,(counts.get(v.name)||0)+1));filtered=all.filter(v=>(!q||v.name.toLowerCase().includes(q))&&(!ch||v.chapters.includes(ch))&&(!$('multi').checked||v.count>1)&&(!$('differences').checked||counts.get(v.name)>1)&&(!$('favorites-only').checked||v.favorite));if(keepPage!==true){page=0;selectionAnchor=null;favoriteAnchor=null}render()}
function selection(){ $('selection').textContent=`已选 ${selected.size} 个变体`;$('export-selected').disabled=!selected.size||!!jobId||scaleValue()===null;$('select-filtered').disabled=!filtered.some(eligible)}
function fitThumbnail(box){
 const img=box.querySelector('img');if(!img?.naturalWidth||!box.clientWidth)return;
 const available=Math.min(Math.max(1,box.clientWidth-16)/img.naturalWidth,Math.max(1,box.clientHeight-12)/img.naturalHeight);
 const scale=available>=1?Math.floor(available):available;
 img.style.width=img.naturalWidth*scale+'px';img.style.height=img.naturalHeight*scale+'px';
}
const thumbnailResize=new ResizeObserver(entries=>{for(const entry of entries)fitThumbnail(entry.target)});
function render(){const pages=Math.max(1,Math.ceil(filtered.length/size));$('stats').textContent=`${filtered.length.toLocaleString()} 个精灵变体 · 每页 ${size} 个`;page=Math.max(0,Math.min(page,pages-1));$('page-number').value=page+1;$('page-number').max=pages;$('page').textContent=`/ ${pages}`;$('prev').disabled=page===0;$('next').disabled=page+1>=pages;thumbnailResize.disconnect();$('grid').replaceChildren();for(const v of filtered.slice(page*size,(page+1)*size)){const card=el('article',undefined,'card'),label=el('label',undefined,'pick'),check=el('input');check.type='checkbox';check.checked=selected.has(v.id);check.disabled=!eligible(v);check.setAttribute('aria-label','选择 '+v.name+' Ch'+v.chapters.join('/'));check.onclick=e=>selectRange(v.id,check.checked,e.shiftKey);label.append(check,el('span',(v.chapters.length?'Ch'+v.chapters.join('/'):'UT')+' · '+v.count+' 帧'));const b=el('button',undefined,'open'),p=el('div',undefined,'preview');if(v.thumbnail){let img=el('img');img.src='/'+v.thumbnail;img.alt='';img.loading='lazy';img.onload=()=>fitThumbnail(p);p.append(img);thumbnailResize.observe(p)}else p.textContent='无位图帧';b.append(p,el('div',v.name,'resource-name'),el('small',`${v.width}×${v.height}${v.complete?'':' · 帧不完整'}`));b.onclick=()=>open(v.id);const star=el('button',undefined,'favorite');setFavoriteIcon(star,v.favorite);star.onclick=e=>toggleFavorite(v.id,e.shiftKey);const head=el('div',undefined,'card-head');head.append(label,star);card.append(head,b);$('grid').append(card)}selection()}
function pause(){playing=false;cancelAnimationFrame(raf);$('play').textContent='播放'}
function paint(){if(!active||!images.length)return;const canvas=$('canvas'),ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);if(images[frame])ctx.drawImage(images[frame],0,0);const scale=scaleValue(true);if(scale!==null){const width=scaledPixels(canvas.width,scale),height=scaledPixels(canvas.height,scale);canvas.style.width=width+'px';canvas.style.height=height+'px';$('detail-size').textContent=`原始 ${canvas.width} × ${canvas.height} px → ${scale}×：${width} × ${height} px`}else $('detail-size').textContent='缩放范围为 0.25–20×';$('scrub').value=frame;$('frame-label').textContent=`帧 ${frame} / ${images.length-1}`}
function play(){if(!images.length)return;playing=true;$('play').textContent='暂停';start=performance.now()-frame*1000/Math.max(.1,+$('detail-fps').value||10);function tick(t){if(!playing)return;frame=Math.floor((t-start)*Math.max(.1,Math.min(120,+$('detail-fps').value||10))/1000)%images.length;paint();raf=requestAnimationFrame(tick)}raf=requestAnimationFrame(tick)}
async function open(id){pause();const tag=++ticket;active=null;images=[];$('open-folder').disabled=true;$('detail-status').textContent='正在读取全部帧…';$('export-one').disabled=true;$('name').textContent='加载中';$('detail-result').hidden=true;$('detail').showModal();try{const v=await api('/api/variant/'+id);const loaded=await Promise.all(v.frames.map(f=>f.image?new Promise((resolve,reject)=>{let i=new Image();i.onload=()=>resolve(i);i.onerror=()=>reject(Error('图像加载失败'));i.src='/'+f.image}):Promise.resolve(null)));if(tag!==ticket)return;active=v;images=loaded;frame=0;syncFavorite();$('name').textContent=v.name+(v.chapters.length?' · Ch'+v.chapters.join('/'):' · UT');$('detail-speed').value=['7.5','3.75'].includes($('detail-fps').value)?$('detail-fps').value:'custom';$('detail-custom-label').hidden=$('detail-speed').value!=='custom';$('open-folder').disabled=false;$('canvas').width=Math.max(1,...v.frames.map(f=>f.width||0));$('canvas').height=Math.max(1,...v.frames.map(f=>f.height||0));$('scrub').max=Math.max(0,images.length-1);$('detail-status').textContent='';$('export-one').disabled=!!jobId||!detailEligible();paint();play()}catch(e){$('detail-status').textContent=e.message}}
const stateNames={queued:'排队中',running:'导出中',cancelled:'已取消',failed:'导出失败',done:'已完成',interrupted:'已中断'};
let lastJob=null;
async function confirmedExport(route,body){let r=await api(route,body);if(r.duplicate){if(!confirm('已在以下位置导出过完全相同的内容：\n'+r.duplicate.folder+'\n\n仍要再导出一份吗？'))return null;r=await api(route,{...body,allow_duplicate:true})}return r}
async function exportIds(ids,opts){if(jobId||!Number.isFinite(opts.scale)||opts.scale<.25||opts.scale>20)return;try{
 $('error').textContent='';const r=await confirmedExport('/api/export',{ids,options:opts,output_dir:$('output-dir').value});if(!r)return;jobId=r.id;
 selection();$('export-one').disabled=true;$('job').hidden=false;$('cancel').hidden=false;$('open-result').hidden=true;$('detail-result').hidden=true;$('progress').hidden=false;$('detail-status').textContent='正在导出…';poll();
 }catch(e){$('error').textContent=e.message;$('detail-status').textContent=e.message}}
async function poll(){if(!jobId)return;try{
 const j=await api('/api/job/'+jobId);$('progress').max=j.total||1;$('progress').value=j.done;
 const status=`${stateNames[j.state]||j.state} ${j.done}/${j.total} · 成功 ${j.success} · 失败 ${j.errors} ${j.current}`;
 $('job-status').textContent=status;$('detail-status').textContent=status;
 if(!['queued','running'].includes(j.state)){
 $('cancel').hidden=true;$('progress').hidden=true;lastJob=j.id;const result=j.state==='done'&&!j.errors?`已导出 ${j.success} 项`:status;$('job-status').textContent=result;$('detail-status').textContent=result;$('open-result').hidden=false;$('detail-result').hidden=false;
 jobId=null;selection();$('export-one').disabled=!detailEligible();
 }else setTimeout(poll,700);
 }catch(e){$('error').textContent='进度读取失败：'+e.message;setTimeout(poll,2500)}}
$('play').onclick=()=>playing?pause():play();$('detail-fps').oninput=()=>{pause();play()};$('detail-speed').onchange=()=>{$('detail-custom-label').hidden=$('detail-speed').value!=='custom';if($('detail-speed').value==='custom'){$('detail-fps').focus();return}$('detail-fps').value=$('detail-speed').value;pause();play()};function detailScaleChanged(){syncScale(true);$('export-one').disabled=!!jobId||!detailEligible();paint()}$('detail-scale').onchange=detailScaleChanged;$('detail-custom-scale').oninput=detailScaleChanged;$('scrub').oninput=()=>{pause();frame=+$('scrub').value;paint()};$('frame-prev').onclick=()=>{pause();frame=(frame-1+images.length)%images.length;paint()};$('frame-next').onclick=()=>{pause();frame=(frame+1)%images.length;paint()};$('close').onclick=()=>$('detail').close();$('detail').onclose=()=>{ticket++;pause();images=[]};$('export-one').onclick=()=>{if(!active)return;const fmt=$('detail-format').value;if(fmt==='png')pause();exportIds([active.id],{format:fmt==='png-all'?'png':fmt,fps:+$('detail-fps').value,scale:scaleValue(true),...(fmt==='png'?{frame_index:frame}:{})})};$('export-selected').onclick=()=>exportIds([...selected],options());$('select-filtered').onclick=()=>{filtered.filter(eligible).forEach(v=>selected.add(v.id));render()};$('cancel').onclick=()=>jobId&&api('/api/cancel',{id:jobId}).catch(e=>$('error').textContent=e.message);$('select-page').onclick=()=>{filtered.slice(page*size,(page+1)*size).filter(eligible).forEach(v=>selected.add(v.id));render()};$('clear').onclick=()=>{selected.clear();selectionAnchor=null;render()};$('prev').onclick=()=>{page--;render()};$('next').onclick=()=>{page++;render()};for(const id of['search','chapter','multi','differences','favorites-only'])$(id).addEventListener(id==='search'?'input':'change',()=>filter());

$('open-folder').onclick=async()=>{if(!active)return;try{const r=await confirmedExport('/api/open-folder',{id:active.id,output_dir:$('output-dir').value});if(!r)return;jobId=r.id;$('job').hidden=false;$('cancel').hidden=false;$('progress').hidden=false;selection();poll()}catch(e){$('detail-status').textContent=e.message}};


$('output-dir').onchange=async()=>{try{const r=await api('/api/settings',{output_dir:$('output-dir').value});$('output-dir').value=r.output_dir;$('output-status').textContent=''}catch(e){$('output-status').textContent=e.message}};
$('pick-output').onclick=async()=>{if(window.spriteDesktop){try{const path=await window.spriteDesktop.pick('output');if(path){const r=await api('/api/settings',{output_dir:path});$('output-dir').value=r.output_dir}}catch(e){$('output-status').textContent=e.message}return}const button=$('pick-output');button.disabled=true;$('cancel-pick').hidden=false;$('output-status').textContent='选择窗口未出现时可直接填路径。';try{const r=await api('/api/pick-output',{});$('output-dir').value=r.output_dir;$('output-status').textContent=''}catch(e){$('output-status').textContent=e.message}finally{button.disabled=false;$('cancel-pick').hidden=true}};
$('open-output').onclick=async()=>{try{const r=await api('/api/settings',{output_dir:$('output-dir').value});$('output-dir').value=r.output_dir;await api('/api/open-export',{})}catch(e){$('output-status').textContent=e.message}};
let outputEdited=false,cardSizeEdited=false;$('output-dir').addEventListener('input',()=>outputEdited=true);
function applyCardSize(value){const width=Number.isFinite(value)?Math.max(180,Math.min(360,Math.round(value/10)*10)):230;const panel=document.querySelector('.browser-panel');panel.style.setProperty('--card-width',width+'px');panel.style.setProperty('--preview-height',Math.round(140*width/230)+'px');$('card-size').value=width;$('card-size-value').textContent=width+' px'}
$('card-size').oninput=()=>{cardSizeEdited=true;applyCardSize(+$('card-size').value)};
$('card-size').onchange=()=>api('/api/settings',{card_width:+$('card-size').value}).catch(e=>$('error').textContent=e.message);
api('/api/settings').then(r=>{if(!outputEdited)$('output-dir').value=r.output_dir;if(!cardSizeEdited)applyCardSize(r.card_width);restoreViews(r.view_options||{});savedPresets=r.presets||[];presetMenu();$('use-preset').checked=false;syncPreset()}).catch(e=>$('error').textContent=e.message);


$('cancel-pick').onclick=()=>api('/api/cancel-pick',{}).catch(e=>$('output-status').textContent=e.message);

async function openResult(){if(lastJob)try{await api('/api/open-export',{id:lastJob})}catch(e){$('error').textContent=e.message;$('detail-status').textContent=e.message}}
$('open-result').onclick=openResult;$('detail-result').onclick=openResult;

let savedPresets=[];
function chosenPreset(){return savedPresets.find(p=>p.id===$('batch-preset').value)}
function presetMenu(value='',enable=false){
 $('batch-preset').replaceChildren();if(!savedPresets.length){const blank=el('option','暂无预设');blank.value='';blank.disabled=true;$('batch-preset').append(blank)}
 for(const p of savedPresets){const o=el('option',p.name);o.value=p.id;$('batch-preset').append(o)}
 $('batch-preset').value=savedPresets.some(p=>p.id===value)?value:(savedPresets[0]?.id||'');$('batch-preset').disabled=!savedPresets.length;if(enable)useSelectedPreset();else{$('use-preset').checked=false;syncPreset()}
}
function syncPreset(){
 const p=chosenPreset();if(!p)$('use-preset').checked=false;
 $('use-preset').disabled=!p;const locked=$('use-preset').checked;
 $('preset-summary').textContent=locked&&p?'预设设置 · 使用「'+p.name+'」':'预设设置';
 $('export-selected').textContent=locked&&p?`按预设【${p.name}】批量导出已勾选内容`:'批量导出已勾选内容';
 for(const id of ['speed-mode','fps','scale','custom-scale','format','preset-name','save-preset'])$(id).disabled=locked;
 $('save-preset').disabled=locked||scaleValue()===null;
 $('delete-preset').disabled=locked||!p;$('preset-info').hidden=!p;
 $('preset-info').textContent=p?`${p.format==='png'?'PNG 全部帧':p.format.toUpperCase()+' 动图'} · ${p.scale}×${p.format==='png'?'':' · '+p.fps+' FPS'}`:'';
}
function batchChanged(){
 syncScale();syncPreset();
 const png=$('format').value==='png';$('batch-speed-label').hidden=png;$('custom-label').hidden=png||$('speed-mode').value!=='custom';
 const valid=new Set(all.filter(eligible).map(v=>v.id));selected=new Set([...selected].filter(id=>valid.has(id)));render();
}
function loadPreset(p){
 $('format').value=p.format;setScale(p.scale);$('speed-mode').value=['7.5','3.75'].includes(String(p.fps))?String(p.fps):'custom';$('fps').value=p.fps;$('preset-name').value=p.name;batchChanged();
}
function useSelectedPreset(){const p=chosenPreset();$('use-preset').checked=!!p;if(p)loadPreset(p);$('preset-status').textContent='';syncPreset()}
$('batch-preset').onchange=useSelectedPreset;
$('use-preset').onchange=()=>{if($('use-preset').checked&&chosenPreset())loadPreset(chosenPreset());$('preset-status').textContent='';syncPreset()};
for(const id of ['speed-mode','fps','scale','format'])$(id).addEventListener('change',batchChanged);
$('custom-scale').oninput=()=>{syncPreset();selection()};
$('save-preset').onclick=async()=>{
 if($('use-preset').checked)return;
 const name=$('preset-name').value.trim(),o=options();
 if(!name){$('preset-status').textContent='请填写名称';return}
 if(o.scale===null){$('preset-status').textContent='缩放范围为 0.25–20×';return}
 if(!Number.isFinite(o.fps)||o.fps<.1||o.fps>120){$('preset-status').textContent='FPS 范围为 0.1–120';return}
 const prior=savedPresets.find(p=>p.name===name),p={id:prior?.id||'saved-'+Date.now(),name,...o};
 const next=savedPresets.filter(p=>p.name!==name).concat(p);
 try{await api('/api/settings',{presets:next});savedPresets=next;presetMenu(p.id,true);$('preset-status').textContent='已保存'}catch{$('preset-status').textContent='无法保存预设'}
};
$('delete-preset').onclick=async()=>{
 if($('use-preset').checked)return;
 const p=chosenPreset();if(!p)return;const next=savedPresets.filter(item=>item.id!==p.id);
 try{await api('/api/settings',{presets:next});savedPresets=next;$('preset-name').value='';presetMenu();$('preset-status').textContent='已删除'}catch{$('preset-status').textContent='无法删除预设'}
};
$('detail-format').onchange=()=>{if($('detail-format').value==='png')pause();$('export-one').disabled=!!jobId||!detailEligible()};
presetMenu();

// Each export view keeps its own last valid parameters.
const viewEdited={batch:false,detail:false};let viewSave=Promise.resolve();
$('detail-format').value=window.spriteDesktop?'gif':'apng';$('detail-fps').value=3.75;
function rememberView(detail=false){
 const key=detail?'detail':'batch';viewEdited[key]=true;
 const value=detail?{format:$('detail-format').value,scale:scaleValue(true),fps:+$('detail-fps').value}:options();
 if(value.scale===null||!Number.isFinite(value.fps)||value.fps<.1||value.fps>120)return;
 viewSave=viewSave.catch(()=>{}).then(()=>api('/api/settings',{view_options:{[key]:value}})).catch(e=>$('error').textContent=e.message);
}
function restoreViews(views){
 for(const key of ['batch','detail']){
  const v=views[key];if(!v||viewEdited[key])continue;const detail=key==='detail';
  $(detail?'detail-format':'format').value=v.format;setScale(v.scale,detail);
  $(detail?'detail-fps':'fps').value=v.fps;
  $(detail?'detail-speed':'speed-mode').value=['3.75','7.5'].includes(String(v.fps))?String(v.fps):'custom';
  if(detail){$('detail-custom-label').hidden=$('detail-speed').value!=='custom';paint()}else batchChanged();
 }
}
for(const id of ['format','scale','custom-scale','speed-mode','fps'])$(id).addEventListener('change',()=>rememberView());
for(const id of ['detail-format','detail-scale','detail-custom-scale','detail-speed','detail-fps'])$(id).addEventListener('change',()=>rememberView(true));
for(const id of ['custom-scale','fps'])$(id).addEventListener('input',()=>rememberView());
for(const id of ['detail-custom-scale','detail-fps'])$(id).addEventListener('input',()=>rememberView(true));
$('batch-preset').addEventListener('change',()=>rememberView());
$('use-preset').addEventListener('change',()=>rememberView());
$('open-help').onclick=()=>{$('help-status').textContent='';$('help').showModal()};
$('close-help').onclick=()=>$('help').close();
$('help').addEventListener('click',async event=>{
 const link=event.target.closest('a[href]');if(!link||!window.spriteDesktop?.openExternal)return;
 event.preventDefault();try{await window.spriteDesktop.openExternal(link.href)}catch(error){$('help-status').textContent='无法打开链接：'+error.message}
});
