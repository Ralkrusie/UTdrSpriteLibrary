"""PNG-frame animation encoder; no game-code playback is implied."""
import hashlib,json,math,re,subprocess,tempfile,sys,shutil
from fractions import Fraction
from pathlib import Path
from PIL import Image
from library import open_image

def settings(v, options):
    scale=float(options.get('scale',5));custom=options.get('fps',3.75)
    if not math.isfinite(scale) or not .25<=scale<=20:raise ValueError('Scale must be 0.25–20')
    fps=float(custom);fallback=False
    if not math.isfinite(fps) or not .1<=fps<=120:raise ValueError('FPS must be 0.1–120')
    fmt=options.get('format','apng')
    if fmt not in ('gif','apng','png','mov'):raise ValueError('Unknown format')
    return scale,fps,fmt,fallback

def encode_png(root,v,folder,options,cancel=lambda:False):
    scale,_,_,_=settings(v,options)
    refs=v['frames'];index=options.get('frame_index')
    if index is not None and (type(index) is not int or not 0<=index<len(refs)):
        raise ValueError('Invalid frame index')
    indices=range(len(refs)) if index is None else [index]
    if not refs:raise ValueError('No bitmap frames')
    files=[]
    for i in indices:
        if cancel():raise InterruptedError('Cancelled')
        f=refs[i]
        if 'image' not in f:raise ValueError('Missing bitmap frame')
        size=(max(1,round(f['width']*scale)),max(1,round(f['height']*scale)))
        if size[0]*size[1]>40_000_000:raise ValueError('Frame exceeds 40 million pixels; reduce scale')
        name=export_filename(v,options)+f'_{i:04d}.png'
        with open_image(root,f['image']) as src:
            with src.convert('RGBA') as rgba:
                with rgba.resize(size,Image.Resampling.NEAREST) as frame:frame.save(folder/name,format='PNG')
        files.append({'file':name,'frame':i,'size':list(size)})
    return {'name':v['name'],'variant':v['id'],'format':'png','scale':scale,'files':files}

def encode(root,v,out,options,cancel=lambda:False):
    scale,fps,fmt,fallback=settings(v,options)
    refs=v['frames']
    if len(refs)<2 or any('image' not in f for f in refs):raise ValueError('Requires at least two complete bitmap frames')
    w=max(f['width'] for f in refs);h=max(f['height'] for f in refs)
    size=(max(1,round(w*scale)),max(1,round(h*scale)))
    if size[0]*size[1]*len(refs)>40_000_000:raise ValueError('Animation exceeds 40 million frame-pixels; reduce scale')
    frames=[]
    try:
        for f in refs:
            if cancel():raise InterruptedError('Cancelled')
            with open_image(root,f['image']) as src:
                canvas=Image.new('RGBA',(w,h));canvas.paste(src.convert('RGBA'),(0,0))
                frame=canvas.resize(size,Image.Resampling.NEAREST);canvas.close()
            if fmt=='gif':
                rgb=frame.convert('RGB');pal=rgb.quantize(colors=255,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE);rgb.close()
                alpha=frame.getchannel('A');mask=alpha.point(lambda a:255 if a<128 else 0);pal.paste(255,mask=mask);mask.close();alpha.close();frame.close()
                pal.info['transparency']=255;frame=pal
            frames.append(frame)
        if fmt=='mov':
            durations=[1000/fps]*len(frames)
            encode_mov(frames,out,fps,cancel)
        elif fmt=='gif':
            # GIF time is in 10-ms units. Distribute rounding error across the cycle.
            step=max(1,100/fps);durations=[10*(round((i+1)*step)-round(i*step)) for i in range(len(frames))]
            frames[0].save(out,format='GIF',save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=2,transparency=255,optimize=False)
        else:
            durations=[1000/fps]*len(frames)
            frames[0].save(out,format='PNG',save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=0,blend=0)
        return {'name':v['name'],'variant':v['id'],'chapters':v['chapters'],'source_frames':len(refs),'size':list(size),'scale':scale,'requested_fps':fps,'cycle_ms':sum(durations),'format':fmt,'default_speed_fallback':fallback,'speed_basis':'custom' if options.get('fps') is not None else 'resource_default','assumed_game_fps':options.get('game_fps',30),'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    finally:
        for f in frames:f.close()

def filename(v):
    if 'export_name' in v:return re.sub(r'[^\w.-]', '_', str(v['export_name']))[:150].strip('.') or 'sprite'
    name=re.sub(r'[^\w.-]','_',v['name'])[:120]
    return name+('_Ch'+'-'.join(map(str,v['chapters'])) if v['chapters'] else '_UT')


def export_filename(v, options):
    scale, fps, fmt, _ = settings(v, options)
    number = lambda value: str(value).removesuffix('.0')
    if options.get('original'):
        suffix = '_original_1x'
    elif fmt == 'png':
        suffix = f'_{number(scale)}x'
    else:
        suffix = f'_{number(fps)}fps_{number(scale)}x'
    return filename(v) + suffix


def ffmpeg_path():
    bundled=Path(__file__).resolve().parent/('ffmpeg.exe' if sys.platform=='win32' else 'ffmpeg')
    if bundled.exists():return str(bundled)
    installed=shutil.which('ffmpeg')
    if installed:return installed
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:raise RuntimeError('MOV 导出需要 FFmpeg，请使用完整便携版或安装 imageio-ffmpeg')

def encode_mov(frames,out,fps,cancel):
    # Raw RGBA -> qtrle ARGB preserves all four channels without chroma subsampling.
    out=Path(out)
    with tempfile.TemporaryDirectory(prefix='.mov-',dir=out.parent) as temp:
        raw=Path(temp)/'frames.rgba'
        with raw.open('wb') as stream:
            for frame in frames:
                if cancel():raise InterruptedError('Cancelled')
                stream.write(frame.tobytes())
        rate=Fraction(str(fps)).limit_denominator(1000000)
        command=[ffmpeg_path(),'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgba','-video_size',f'{frames[0].width}x{frames[0].height}','-framerate',str(rate),'-i',str(raw),'-an','-c:v','qtrle','-pix_fmt','argb','-f','mov',str(out)]
        with (Path(temp)/'error.txt').open('w+b') as errors:
            process=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=errors,creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
            try:
                while True:
                    if cancel():raise InterruptedError('Cancelled')
                    try:code=process.wait(timeout=.1);break
                    except subprocess.TimeoutExpired:pass
                if code:
                    errors.seek(0);raise RuntimeError(errors.read().decode('utf-8',errors='replace')[-1500:])
            except BaseException:
                process.kill();process.wait();out.unlink(missing_ok=True);raise
