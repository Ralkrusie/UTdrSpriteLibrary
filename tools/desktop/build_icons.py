"""Convert the approved first frame into desktop PNG/ICO/ICNS assets."""
import hashlib
import io
from pathlib import Path
import struct
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/ui'


def build():
    source = OUT / 'spr_dw_ch3_board_npc_bibliox_0.png'
    if hashlib.sha256(source.read_bytes()).hexdigest() != '866e146743279600764a26a973f2c78afac6325ea145714f4f4fbbd0ce8a0bfd':
        raise ValueError('Unexpected icon source')
    pngs = {}
    with Image.open(source) as original:
        original = original.convert('RGBA')
        for size in (16, 24, 32, 48, 64, 128, 256, 512, 1024):
            with Image.new('RGBA', (size, size), (0, 0, 0, 0)) as canvas:
                with original.resize((size, size), Image.Resampling.NEAREST) as sprite:
                    canvas.alpha_composite(sprite, (0, 0))
                buffer = io.BytesIO()
                canvas.save(buffer, format='PNG')
                pngs[size] = buffer.getvalue()
    (OUT / 'app-icon.png').write_bytes(pngs[256])
    sizes = (16, 24, 32, 48, 64, 128, 256)
    offset = 6 + 16 * len(sizes)
    entries = []
    for size in sizes:
        entries.append(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(pngs[size]), offset))
        offset += len(pngs[size])
    (OUT / 'app-icon.ico').write_bytes(struct.pack('<HHH', 0, 1, len(sizes)) + b''.join(entries) + b''.join(pngs[s] for s in sizes))
    types = {16:b'icp4', 32:b'icp5', 64:b'icp6', 128:b'ic07', 256:b'ic08', 512:b'ic09', 1024:b'ic10'}
    chunks = b''.join(kind + struct.pack('>I', len(pngs[s]) + 8) + pngs[s] for s, kind in types.items())
    (OUT / 'app-icon.icns').write_bytes(b'icns' + struct.pack('>I', 8 + len(chunks)) + chunks)
    print('Desktop icon assets generated')


if __name__ == '__main__':
    build()
