"""Verify qtrle MOV round trips RGBA exactly, including odd sizes and alpha."""
import argparse,sys,subprocess,tempfile,json
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
from encoder import encode_mov,ffmpeg_path
import encoder

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',type=Path);args=parser.parse_args()
 if args.ffmpeg:
  binary=args.ffmpeg.resolve();assert binary.is_file();encoder.ffmpeg_path=lambda:str(binary)
 decoder=encoder.ffmpeg_path()
 with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'releases') as temp:
  folder=Path(temp);frames=[]
  for i in range(4):
   im=Image.new('RGBA',(21,35));im.putdata([((x*31+i*7)%256,(x*19)%256,(x*11)%256,(x*13+i)%256) for x in range(21*35)]);frames.append(im)
  for fps in (.1,3.75,7.5,6.3,120):
   out=folder/'test.mov';encode_mov(frames,out,fps,lambda:False)
   decoded=subprocess.run([decoder,'-v','error','-i',str(out),'-f','rawvideo','-pix_fmt','rgba','-'],check=True,stdout=subprocess.PIPE).stdout
   assert decoded==b''.join(im.tobytes() for im in frames),f'RGBA differs at {fps}'
  try:
   encode_mov(frames,folder/'cancel.mov',3.75,lambda:True)
   raise AssertionError('Cancellation ignored')
  except InterruptedError:pass
  assert not (folder/'cancel.mov').exists()
  print('PASS MOV: exact RGBA at 0.1/3.75/7.5/6.3/120 FPS, odd sizes and cancellation')
if __name__=='__main__':main()
