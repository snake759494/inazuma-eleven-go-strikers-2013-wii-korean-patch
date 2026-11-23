"""SHTX texture decode/encode + bulk export of ui.bin."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__))
import s13
from PIL import Image


def decode(d):
    assert d[:4] == b'SHTX', d[:4]
    fmt = d[4:6]
    w, h, unk = struct.unpack_from('<HHH', d, 6)
    if fmt == b'FF':
        px = d[12:12 + w * h * 4]
        return Image.frombuffer('RGBA', (w, h), px, 'raw', 'BGRA', 0, 1).copy(), fmt
    pal = [struct.unpack_from('<I', d, 12 + 4 * i)[0] for i in range(256)]
    palc = [((c >> 16) & 255, (c >> 8) & 255, c & 255, c >> 24) for c in pal]
    data = d[12 + 1024:]
    img = Image.new('RGBA', (w, h))
    if fmt == b'F4':
        out = []
        for i in range(w * h):
            b = data[i // 2]
            out.append(palc[(b >> 4) if i % 2 == 0 else (b & 15)])
    else:
        out = [palc[data[i]] for i in range(w * h)]
    img.putdata(out)
    return img, fmt


def encode(img, orig):
    """Encode RGBA image in the same format as original SHTX bytes."""
    fmt = orig[4:6]
    w, h = img.size
    hdr = orig[:6] + struct.pack('<HH', w, h) + orig[10:12]
    img = img.convert('RGBA')
    if fmt == b'FF':
        r, g, b, a = img.split()
        return hdr + Image.merge('RGBA', (b, g, r, a)).tobytes() + orig[12 + w * h * 4:]
    n = 16 if fmt == b'F4' else 256
    q = img.quantize(colors=n, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    pal = q.getpalette(rawmode='RGBA')[:n * 4]
    pal += [0] * (n * 4 - len(pal))
    palb = bytearray()
    for i in range(n):
        r, g, b, a = pal[i * 4:i * 4 + 4]
        palb += struct.pack('<I', (a << 24) | (r << 16) | (g << 8) | b)
    palb += orig[12 + 4 * n:12 + 1024]
    idx = q.tobytes()
    if fmt == b'F4':
        data = bytes(((idx[i] & 15) << 4) | (idx[i + 1] & 15) for i in range(0, len(idx), 2))
        tail = orig[12 + 1024 + w * h // 2:]
    else:
        data = idx
        tail = orig[12 + 1024 + w * h:]
    return hdr + bytes(palb) + data + tail


def _work(args):
    i, raw, outdir = args
    try:
        d = s13.lz_decompress(raw)
    except Exception:
        return i, None
    if d[:4] != b'SHTX':
        return i, None
    try:
        img, fmt = decode(d)
    except Exception as e:
        return i, 'err'
    img.save(os.path.join(outdir, '%04d.png' % i))
    open(os.path.join(outdir, '%04d.shtx' % i), 'wb').write(d)
    return i, (fmt.decode(), img.size)


if __name__ == '__main__':
    from multiprocessing import Pool
    src = sys.argv[1]
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    a = s13.Archive(src)
    jobs = [(i, a.raw(i), outdir) for i in range(a.count)]
    with Pool(8) as p:
        res = p.map(_work, jobs, chunksize=8)
    n = sum(1 for _, r in res if r and r != 'err')
    print('textures', n)
    import json
    json.dump({i: r for i, r in res if r and r != 'err'}, open(os.path.join(outdir, 'index.json'), 'w'))
