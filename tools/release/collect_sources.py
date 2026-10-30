"""Collect exact upstream source snapshots; this does not certify source completeness."""
import concurrent.futures,hashlib,json,re,time,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES={
 'UndertaleModTool-0.9.2.0.zip':'https://codeload.github.com/UnderminersTeam/UndertaleModTool/zip/03c7048438347799e0717b6e57a9358d000472e0',
 'Underanalyzer-4ff50a8.zip':'https://codeload.github.com/UnderminersTeam/Underanalyzer/zip/4ff50a866b4c1a7acee8cebe6a56d6a48709b453',
 'FFmpeg-n7.1.zip':'https://codeload.github.com/FFmpeg/FFmpeg/zip/refs/tags/n7.1',
 'Magick.NET-14.16.0.zip':'https://codeload.github.com/dlemstra/Magick.NET/zip/refs/tags/14.16.0',
 'Newtonsoft.Json-13.0.4.zip':'https://codeload.github.com/JamesNK/Newtonsoft.Json/zip/refs/tags/13.0.4',
 'SharpZipLib-1.4.2.zip':'https://codeload.github.com/icsharpcode/SharpZipLib/zip/refs/tags/v1.4.2',
 'Magick.Native-1187ae6.zip':'https://codeload.github.com/dlemstra/Magick.Native/zip/1187ae6ead3c4ac8b3020cfd8a98b9990697eec6',
 'ImageMagick-360eda5.zip':'https://codeload.github.com/ImageMagick/ImageMagick/zip/360eda553586e389c9c725fc49df94f209a8a3c7',
 'ImageMagick-Dependencies-2026.07.27.zip':'https://codeload.github.com/ImageMagick/Dependencies/zip/refs/tags/2026.07.27.0556',
 'ImageMagick-Configure-2026.05.30.zip':'https://codeload.github.com/ImageMagick/Configure/zip/refs/tags/2026.05.30.2033',
 'ImageMagick-Configure-2026.07.15.zip':'https://codeload.github.com/ImageMagick/Configure/zip/refs/tags/2026.07.15.0628',
}
def main():
 out=ROOT/'vendor/release-sources';out.mkdir(exist_ok=True,parents=True)
 def fetch(item):
  name,url=item;dest=out/name
  try:
   if not dest.exists():
    for attempt in range(3):
     try:
      req=urllib.request.Request(url,headers={'User-Agent':'UTdrSpriteLibrary-source-bundle'})
      temporary=dest.with_suffix('.part')
      with urllib.request.urlopen(req,timeout=120) as response,temporary.open('wb') as stream:
       while chunk:=response.read(1024*1024):stream.write(chunk)
      with zipfile.ZipFile(temporary) as zipped:
       if zipped.testzip() is not None:raise ValueError('Invalid source ZIP')
      temporary.replace(dest);break
     except Exception:
      if attempt==2:raise
      time.sleep(2)
   with zipfile.ZipFile(dest) as zipped:
    if zipped.testzip() is not None:raise ValueError('Invalid cached source ZIP')
   record={'file':name,'url':url,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size};print(name,record['bytes'],flush=True);return record
  except Exception as e:print(name,str(e),flush=True);return {'file':name,'url':url,'error':str(e)}
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(fetch,SOURCES.items()))
 # The native Windows build pins its patched delegate sources in this script.
 dependency_archive=out/'ImageMagick-Dependencies-2026.07.27.zip'
 if dependency_archive.is_file():
  with zipfile.ZipFile(dependency_archive) as zipped:
   script=zipped.read('Dependencies-2026.07.27.0556/clone-dependencies.sh').decode('utf-8')
  section=script.split('clone_dependencies()\n',1)[1].split('clone_optional_dependencies()',1)[0]
  delegates={f'ImageMagick-{name}-{commit[:12]}.zip':f'https://codeload.github.com/ImageMagick/{name}/zip/{commit}'
             for name,commit in re.findall(r"clone '([\w-]+)' '([0-9a-f]{40})'",section)}
  if len(delegates)!=37:raise ValueError('Unexpected native delegate source list')
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:records+=list(pool.map(fetch,delegates.items()))
 (out/'manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
 if any('error' in r for r in records):raise SystemExit(1)
if __name__=='__main__':main()
