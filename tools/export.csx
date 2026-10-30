// Read-only export. No Save/Write of the loaded game package.
using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Security.Cryptography;
using Newtonsoft.Json.Linq;
using ImageMagick;
using UndertaleModLib.Models;
using UndertaleModLib.Util;
EnsureDataLoaded();
string root=Environment.GetEnvironmentVariable("DR_LIBRARY_OUT");
string chapter=Environment.GetEnvironmentVariable("DR_LIBRARY_CHAPTER");
if(String.IsNullOrEmpty(root)||String.IsNullOrEmpty(chapter))throw new Exception("Missing output configuration");
Directory.CreateDirectory(Path.Combine(root,"images"));
var entries=new JArray();var errors=new JArray();
var cache=new Dictionary<UndertaleTexturePageItem,JObject>();
using(var worker=new TextureWorker()) {
 JObject Frame(UndertaleTexturePageItem t,string label) {
  if(t==null)return new JObject{["missing"]=true};
  if(cache.TryGetValue(t,out var known))return (JObject)known.DeepClone();
  try {
   using(var img=worker.GetTextureFor(t,label,true)) {
    byte[] pixels=img.ToByteArray(MagickFormat.Rgba);
    byte[] header=Encoding.UTF8.GetBytes(img.Width+"x"+img.Height+":RGBA8:");
    byte[] packed=new byte[header.Length+pixels.Length];Buffer.BlockCopy(header,0,packed,0,header.Length);Buffer.BlockCopy(pixels,0,packed,header.Length,pixels.Length);
    string hash=Convert.ToHexString(SHA256.HashData(packed)).ToLowerInvariant();
    string rel="images/"+hash.Substring(0,2)+"/"+hash+".png";
    string path=Path.Combine(root,rel);Directory.CreateDirectory(Path.GetDirectoryName(path));
    if(!File.Exists(path))TextureWorker.SaveImageToFile(img,path);
    var f=new JObject{["image"]=rel,["pixel_sha256"]=hash,["width"]=img.Width,["height"]=img.Height,["target"]=new JArray(t.TargetX,t.TargetY,t.TargetWidth,t.TargetHeight),["source"]=new JArray(t.SourceX,t.SourceY,t.SourceWidth,t.SourceHeight),["texture_page"]=Data.EmbeddedTextures.IndexOf(t.TexturePage)};
    cache[t]=f;return (JObject)f.DeepClone();
   }
  }catch(Exception e){errors.Add(new JObject{["asset"]=label,["error"]=e.Message});return new JObject{["error"]=e.Message};}
 }
 for(int i=0;i<Data.Sprites.Count;i++) {
  var s=Data.Sprites[i];var frames=new JArray();int n=0;
  foreach(var f in s.Textures)frames.Add(Frame(f?.Texture,s.Name.Content+":"+(n++)));
  entries.Add(new JObject{["kind"]="sprite",["name"]=s.Name.Content,["index"]=i,["width"]=s.Width,["height"]=s.Height,["origin"]=new JArray(s.OriginX,s.OriginY),["bbox"]=new JArray(s.MarginLeft,s.MarginTop,s.MarginRight,s.MarginBottom),["speed"]=s.GMS2PlaybackSpeed,["speed_type"]=s.GMS2PlaybackSpeedType.ToString(),["frames"]=frames});
  if(i%500==0)ScriptMessage(chapter+": sprites "+i+"/"+Data.Sprites.Count);
 }
 for(int i=0;i<Data.Backgrounds.Count;i++) {
  var b=Data.Backgrounds[i];entries.Add(new JObject{["kind"]="background",["name"]=b.Name.Content,["index"]=i,["tile_size"]=new JArray(b.GMS2TileWidth,b.GMS2TileHeight),["frames"]=new JArray(Frame(b.Texture,b.Name.Content))});
 }
 for(int i=0;i<Data.Fonts.Count;i++) {
  var f=Data.Fonts[i];entries.Add(new JObject{["kind"]="font",["name"]=f.Name.Content,["index"]=i,["frames"]=new JArray(Frame(f.Texture,f.Name.Content))});
 }
}
Directory.CreateDirectory(Path.Combine(root,"chapters"));
File.WriteAllText(Path.Combine(root,"chapters",chapter+".json"),new JObject{["chapter"]=chapter,["entries"]=entries,["errors"]=errors}.ToString(),new UTF8Encoding(false));
ScriptMessage(chapter+": exported "+entries.Count+" resources; errors "+errors.Count);
