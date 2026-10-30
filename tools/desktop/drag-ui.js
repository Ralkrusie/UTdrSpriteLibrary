// Appended to the existing UI only in the native Windows trial package.
if(window.spriteDesktop){
 const notice=el('p','调整参数后可拖动预览图。'),retry=el('button','重新准备'),reveal=el('button','查看拖拽文件');
 notice.setAttribute('role','status');reveal.hidden=true;
 const bar=el('div',undefined,'controls drag-controls');bar.append(notice,retry,reveal);$('detail-info').append(bar);
 const canvas=$('canvas');let lastKey='',token=null,revision=0,timer=0;
 function current(){return active&&$('detail').open&&scaleValue(true)!==null?{id:active.id,format:$('detail-format').value,scale:scaleValue(true),fps:+$('detail-fps').value,frame:$('detail-format').value==='png'?frame:0,output:$('output-dir').value}:null}
 function refresh(){
  const request=current(),key=JSON.stringify(request);if(key===lastKey)return;lastKey=key;const rev=++revision;clearTimeout(timer);token=null;canvas.draggable=false;canvas.style.cursor='default';reveal.hidden=true;
  if(!request){if(active&&$('detail').open)notice.textContent='缩放范围为 0.25–20×';return}
  if(!['gif','png','apng','png-all','mov'].includes(request.format)){notice.textContent='拖拽试用支持 GIF 和 PNG 当前帧，请切换格式。';return}
  if(request.format==='png')pause();notice.textContent='正在按当前参数准备拖拽文件…';
  timer=setTimeout(async()=>{try{const result=await window.spriteDesktop.prepare(request);if(rev!==revision)return;token=result.token;canvas.draggable=true;canvas.style.cursor='grab';notice.textContent='可拖动预览图 · '+(request.format==='png-all'?'PNG 全部帧（'+result.count+' 张）':request.format.toUpperCase())+' · '+request.scale+'×'}catch(error){if(rev===revision)notice.textContent='准备失败：'+error.message+'（可点击重新准备）'}},450);
 }
 retry.onclick=()=>{lastKey='';refresh()};reveal.onclick=()=>token&&window.spriteDesktop.reveal(token);
 canvas.addEventListener('dragstart',event=>{event.preventDefault();if(token&&$('detail').open&&JSON.stringify(current())===lastKey)window.spriteDesktop.drag(token)});
 window.spriteDesktop.onSaved(saved=>{if(saved===token)reveal.hidden=false});
 window.spriteDesktop.onError(message=>{notice.textContent='拖出失败：'+message});
 setInterval(refresh,250);
}
