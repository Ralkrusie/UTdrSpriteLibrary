// Render the approved pixel sprite on a black SVG canvas. Development only.
// NODE_PATH must provide Playwright; PWA/APK builds use the checked-in PNGs.
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
(async()=>{
 const source=fs.readFileSync(path.resolve(__dirname,'../../assets/ui/spr_dw_ch3_board_npc_bibliox_0.png'));
 const width=source.readUInt32BE(16),height=source.readUInt32BE(20);
 const browser=await chromium.launch({executablePath:process.env.PWA_BROWSER||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage({deviceScaleFactor:1});
  for(const size of [192,512]){
   const scale=Math.floor(size*13/16/Math.max(width,height)),w=width*scale,h=height*scale;
   const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><rect width="100%" height="100%" fill="#000"/><image x="${Math.floor((size-w)/2)}" y="${Math.floor((size-h)/2)}" width="${w}" height="${h}" style="image-rendering:pixelated" href="data:image/png;base64,${source.toString('base64')}"/></svg>`;
   await page.setViewportSize({width:size,height:size});
   await page.setContent(`<style>body{margin:0;background:black}</style>${svg}`);
   await page.locator('image').evaluate(async e=>{const i=new Image();i.src=e.getAttribute('href');await i.decode()});
   await page.screenshot({path:path.join(__dirname,`icon-${size}.png`)});
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
