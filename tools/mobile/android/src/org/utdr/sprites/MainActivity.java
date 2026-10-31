package org.utdr.sprites;

import android.app.*;
import android.content.*;
import android.net.Uri;
import android.os.*;
import android.webkit.*;
import android.widget.Toast;
import android.widget.FrameLayout;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;

public class MainActivity extends Activity {
 private WebView web;
 private ValueCallback<Uri[]> chooser;
 private File pendingSave;
 private final ExecutorService io=Executors.newSingleThreadExecutor();
 private static final String ORIGIN="https://appassets.androidplatform.net/";
 private void message(String text){runOnUiThread(()->Toast.makeText(this,text,Toast.LENGTH_LONG).show());}
 @Override public void onCreate(Bundle state){
  super.onCreate(state);
  FrameLayout root=new FrameLayout(this);root.setBackgroundColor(android.graphics.Color.BLACK);
  web=new WebView(this);root.addView(web,new FrameLayout.LayoutParams(-1,-1));setContentView(root);
  // Resize the WebView viewport itself: WebView padding does not constrain
  // HTML top-layer dialogs or fixed elements to the safe area.
  root.setOnApplyWindowInsetsListener((v,insets)->{
   int left=insets.getSystemWindowInsetLeft(),top=insets.getSystemWindowInsetTop(),right=insets.getSystemWindowInsetRight(),bottom=insets.getSystemWindowInsetBottom();
   android.view.DisplayCutout cutout=insets.getDisplayCutout();
   if(cutout!=null){left=Math.max(left,cutout.getSafeInsetLeft());top=Math.max(top,cutout.getSafeInsetTop());right=Math.max(right,cutout.getSafeInsetRight());bottom=Math.max(bottom,cutout.getSafeInsetBottom());}
   v.setPadding(left,top,right,bottom);return insets.consumeSystemWindowInsets();
  });
  root.requestApplyInsets();
  WebSettings s=web.getSettings();s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);s.setAllowFileAccess(false);s.setAllowContentAccess(true);s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);s.setSupportMultipleWindows(false);
  web.addJavascriptInterface(new Bridge(),"AndroidExports");
  web.setWebViewClient(new WebViewClient(){
   public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){
    String url=request.getUrl().toString();
    if(request.isForMainFrame() && (url.equals("https://github.com/Ralkrusie/UTdrSpriteLibrary/releases")||url.equals("https://wwaya.lanzouv.com/b01euw4aoh")||url.equals("https://space.bilibili.com/571877935")||url.equals("https://afdian.com/a/ralkrusie"))){
     try{startActivity(new Intent(Intent.ACTION_VIEW,request.getUrl()));}catch(android.content.ActivityNotFoundException e){android.widget.Toast.makeText(MainActivity.this,"未找到可打开链接的浏览器",android.widget.Toast.LENGTH_SHORT).show();}
    }return true;
   }
   public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest request){
    Uri uri=request.getUrl();String name=uri.getPath();
    if("https".equals(uri.getScheme())&&"appassets.androidplatform.net".equals(uri.getHost())&&name!=null&&name.matches("/[A-Za-z0-9_.-]+")){
     name=name.substring(1);String type=name.endsWith(".js")?"text/javascript":name.endsWith(".css")?"text/css":name.endsWith(".html")?"text/html":name.endsWith(".png")?"image/png":"application/json";
     try{return new WebResourceResponse(type,"UTF-8",getAssets().open("web/"+name));}catch(IOException ignored){}
    }
    return new WebResourceResponse("text/plain","UTF-8",404,"Not Found",Collections.emptyMap(),new ByteArrayInputStream(new byte[0]));
   }
  });
  web.setWebChromeClient(new WebChromeClient(){
   public boolean onShowFileChooser(WebView v,ValueCallback<Uri[]> callback,FileChooserParams params){
    if(chooser!=null)chooser.onReceiveValue(null);chooser=callback;
    Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"application/zip","application/x-zip-compressed","application/octet-stream"});
    try{startActivityForResult(intent,10);}catch(ActivityNotFoundException e){chooser.onReceiveValue(null);chooser=null;message("未找到系统文件选择器");}return true;
   }
   public boolean onJsConfirm(WebView v,String url,String text,JsResult result){new AlertDialog.Builder(MainActivity.this).setMessage(text).setPositiveButton("确定",(d,w)->result.confirm()).setNegativeButton("取消",(d,w)->result.cancel()).setOnCancelListener(d->result.cancel()).show();return true;}
  });
  web.loadUrl(ORIGIN+"index.html");
 }
 @Override public void onBackPressed(){web.evaluateJavascript("(()=>{const h=document.querySelector('#help');if(h?.open){h.close();return true}const j=document.querySelector('#job'),d=document.querySelector('#detail');if(j?.open){document.querySelector('#job-close').click();return true}if(d?.open){document.querySelector('#close').click();return true}return false})()",result->{if(!"true".equals(result))super.onBackPressed();});}
 @Override protected void onActivityResult(int code,int result,Intent data){
  super.onActivityResult(code,result,data);
  if(code==10&&chooser!=null){chooser.onReceiveValue(result==RESULT_OK&&data!=null&&data.getData()!=null?new Uri[]{data.getData()}:null);chooser=null;}
  if(code==11){final File source=pendingSave;pendingSave=null;if(result==RESULT_OK&&data!=null&&data.getData()!=null&&source!=null){final Uri target=data.getData();io.execute(()->{try(InputStream in=new FileInputStream(source);OutputStream out=getContentResolver().openOutputStream(target,"wt")){if(out==null)throw new IOException();byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1)out.write(b,0,n);message("已保存文件");}catch(IOException e){message("保存失败，请检查剩余空间或重新选择位置");}finally{source.delete();source.getParentFile().delete();}});}else if(source!=null){source.delete();source.getParentFile().delete();}}
 }
 @Override protected void onPause(){super.onPause();web.onPause();}
 @Override protected void onResume(){super.onResume();if(web!=null)web.onResume();}
 @Override protected void onDestroy(){if(chooser!=null)chooser.onReceiveValue(null);web.removeJavascriptInterface("AndroidExports");web.destroy();io.shutdown();super.onDestroy();}
 public class Bridge {
  private File file;private OutputStream stream;private String token;private long count;
  @JavascriptInterface public synchronized String begin(String name)throws IOException{
   if(stream!=null){stream.close();file.delete();file.getParentFile().delete();}
   name=name.replaceAll("[^\\p{L}\\p{N}_.-]","_");if(name.length()>140)name=name.substring(0,120)+name.substring(name.lastIndexOf('.'));if(!name.matches(".+\\.(png|gif|zip)"))throw new IOException("Unsupported format");
   token=UUID.randomUUID().toString();File folder=new File(getFilesDir(),"exports/"+token);if(!folder.mkdirs())throw new IOException("Cannot create export");file=new File(folder,name);stream=new FileOutputStream(file);count=0;return token;
  }
  @JavascriptInterface public synchronized boolean append(String id,String base64)throws IOException{
   if(!Objects.equals(id,token)||stream==null||base64.length()>100000)throw new IOException("Invalid export");byte[] bytes=android.util.Base64.decode(base64,android.util.Base64.DEFAULT);count+=bytes.length;if(count>80*1024*1024)throw new IOException("Export too large");stream.write(bytes);return true;
  }
  @JavascriptInterface public synchronized boolean finish(String id,String action)throws IOException{
   if(!Objects.equals(id,token)||stream==null||!Arrays.asList("save","share").contains(action))throw new IOException("Invalid export");stream.close();stream=null;final File ready=file;final Uri uri=new Uri.Builder().scheme("content").authority("org.utdr.sprites.exports").appendPath(token).appendPath(file.getName()).build();
   runOnUiThread(()->{try{
    if(action.equals("share")){Intent intent=new Intent(Intent.ACTION_SEND).setType(ExportProvider.mime(ready.getName())).putExtra(Intent.EXTRA_STREAM,uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);intent.setClipData(ClipData.newRawUri("export",uri));startActivity(Intent.createChooser(intent,"分享素材"));}
    else if(pendingSave==null){pendingSave=ready;startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType(ExportProvider.mime(ready.getName())).putExtra(Intent.EXTRA_TITLE,ready.getName()),11);}
    else message("请先完成上一次保存");
   }catch(RuntimeException e){pendingSave=null;message("操作失败，设备可能没有可用的接收应用");}});return true;
  }
 }
}
