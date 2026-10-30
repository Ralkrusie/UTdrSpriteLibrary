import tempfile,unittest,sys
from pathlib import Path
from PIL import Image
from encoder import encode,encode_png,settings
class EncoderTest(unittest.TestCase):
 def test_formats_and_transparency(self):
  with tempfile.TemporaryDirectory(prefix='encoder-',dir=Path(__file__).resolve().parents[2]/'releases') as t:
   root=Path(t);(root/'images').mkdir();refs=[]
   for i in range(2):
    image=Image.new('RGBA',(4,3));image.putpixel((i,1),(255,40,0,255));image.save(root/f'images/{i}.png');refs.append({'image':f'images/{i}.png','width':4,'height':3})
   v={'id':'fixture','name':'fixture','chapters':[1],'speed':.2,'speed_type':'FramesPerGameFrame','frames':refs}
   self.assertEqual(settings(v,{})[:2],(5,3.75))
   for fmt in ('apng','gif'):
    out=root/(fmt+'.png' if fmt=='apng' else fmt+'.gif');record=encode(root,v,out,{'format':fmt,'scale':2,'fps':6})
    with Image.open(out) as im:
     self.assertEqual(im.size,(8,6));self.assertEqual(im.n_frames,2)
     for i in range(2):
      im.seek(i);rgba=im.convert('RGBA');self.assertEqual(rgba.getpixel((0,0))[3],0);self.assertEqual(rgba.getpixel((i*2,2)),(255,40,0,255))
    self.assertAlmostEqual(record['cycle_ms'],333.333,delta=10)
   with self.assertRaises(ValueError):settings(v,{'scale':float('nan')})
   for scale in (0,.249,20.001,float('inf')):
    with self.assertRaises(ValueError):settings(v,{'scale':scale})
   for scale,dimensions in ((.25,(1,1)),(2.5,(10,8)),(20,(80,60))):
    dest=root/f'scaled-{scale}';dest.mkdir()
    result=encode_png(root,v,dest,{'scale':scale,'frame_index':0})
    with Image.open(dest/result['files'][0]['file']) as im:self.assertEqual(im.size,dimensions)
    for fmt in ('apng','gif'):
     target=root/f'scaled-{scale}.{fmt}'
     encode(root,v,target,{'format':fmt,'scale':scale,'fps':3.75})
     with Image.open(target) as im:self.assertEqual(im.size,dimensions)
   with self.assertRaises(InterruptedError):encode(root,v,root/'cancel.png',{'format':'apng'},lambda:True)
   single=root/'single';single.mkdir()
   result=encode_png(root,v,single,{'format':'png','scale':5,'frame_index':1})
   self.assertEqual(len(result['files']),1)
   with Image.open(single/result['files'][0]['file']) as im:
    self.assertEqual(im.size,(20,15));self.assertEqual(im.n_frames,1)
    self.assertEqual(im.getpixel((5,5)),(255,40,0,255));self.assertEqual(im.getpixel((0,0))[3],0)
   batch=root/'batch';batch.mkdir()
   self.assertEqual(len(encode_png(root,v,batch,{'format':'png'})['files']),2)
   static=root/'static';static.mkdir()
   self.assertEqual(len(encode_png(root,v|{'frames':refs[:1]},static,{'format':'png'})['files']),1)
   with self.assertRaises(ValueError):encode_png(root,v,single,{'format':'png','frame_index':3})
if __name__=='__main__':unittest.main()
