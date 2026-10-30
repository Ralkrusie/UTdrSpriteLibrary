"""Collect exact upstream source snapshots; this does not certify source completeness."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES={
 'UndertaleModTool-0.9.2.0.zip':'https://codeload.github.com/UnderminersTeam/UndertaleModTool/zip/03c7048438347799e0717b6e57a9358d000472e0',
 'Underanalyzer-4ff50a8.zip':'https://codeload.github.com/UnderminersTeam/Underanalyzer/zip/4ff50a866b4c1a7acee8cebe6a56d6a48709b453',
 'FFmpeg-n7.1.zip':'https://codeload.github.com/FFmpeg/FFmpeg/zip/refs/tags/n7.1',
 'Magick.NET-14.16.0.zip':'https://codeload.github.com/dlemstra/Magick.NET/zip/refs/tags/14.16.0',
 'Newtonsoft.Json-13.0.4.zip':'https://codeload.github.com/JamesNK/Newtonsoft.Json/zip/refs/tags/13.0.4',
 'SharpZipLib-1.4.2.zip':'https://codeload.github.com/icsharpcode/SharpZipLib/zip/refs/tags/v1.4.2',
}
def main():
 out=ROOT/'vendor/release-sources';out.mkdir(exist_ok=True,parents=True)
 def fetch(item):
  name,url=item;dest=out/name
  try:
   if not dest.exists():
    req=urllib.request.Request(url,headers={'User-Agent':'UTdrSpriteLibrary-source-bundle'})
    data=urllib.request.urlopen(req,timeout=90).read();dest.write_bytes(data)
   record={'file':name,'url':url,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size};print(name,record['bytes'],flush=True);return record
  except Exception as e:print(name,str(e),flush=True);return {'file':name,'url':url,'error':str(e)}
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(fetch,SOURCES.items()))
 (out/'manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
 if any('error' in r for r in records):raise SystemExit(1)
if __name__=='__main__':main()
