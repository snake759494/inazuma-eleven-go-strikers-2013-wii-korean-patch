"""Build Korean font files (ui.bin 0,1,2) by rendering Hangul into kanji slots."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
import s13, font, kor

ROOT = s13.ROOT
W, H = 24, 25
SS = 4
# font index -> (ttf, box(x0,y0,x1,y1) inclusive target ink area)
CFG = {
    0: ('NanumSquareNeo-cBd.ttf', (1, 1, 22, 23)),
    1: ('NanumSquareNeo-dEb.ttf', (1, 1, 22, 23)),
    2: ('NanumSquareNeo-bRg.ttf', (2, 3, 22, 22)),
}


def render(ch, ttf, box, size_px):
    f = ImageFont.truetype(os.path.join(ROOT, ttf), size_px * SS)
    img = Image.new('L', (W * SS * 2, H * SS * 2), 0)
    d = ImageDraw.Draw(img)
    d.text((W * SS // 2, H * SS // 2), ch, font=f, fill=255)
    return img, f


def calib(ttf, box):
    """choose pixel size so that the typical Hangul fits box height/width; return size and vertical offset."""
    bw = box[2] - box[0] + 1
    bh = box[3] - box[1] + 1
    best = None
    for size in range(16, 34):
        f = ImageFont.truetype(os.path.join(ROOT, ttf), size * SS)
        # combined bbox of tall/wide samples
        xs0, ys0, xs1, ys1 = 1e9, 1e9, -1e9, -1e9
        for ch in '뷁꿿힣를많됐쀍갉':
            bb = f.getbbox(ch)
            xs0 = min(xs0, bb[0]); ys0 = min(ys0, bb[1]); xs1 = max(xs1, bb[2]); ys1 = max(ys1, bb[3])
        w = (xs1 - xs0) / SS
        h = (ys1 - ys0) / SS
        if w <= bw + 0.3 and h <= bh + 0.3:
            best = (size, xs0, ys0, xs1, ys1)
    return best


def glyph_bytes(ch, ttf, box, cal):
    size, xs0, ys0, xs1, ys1 = cal
    f = ImageFont.truetype(os.path.join(ROOT, ttf), size * SS)
    img = Image.new('L', (W * SS, H * SS), 0)
    d = ImageDraw.Draw(img)
    bw = (box[2] - box[0] + 1) * SS
    bh = (box[3] - box[1] + 1) * SS
    ox = box[0] * SS + (bw - (xs1 - xs0)) / 2 - xs0
    oy = box[1] * SS + (bh - (ys1 - ys0)) / 2 - ys0
    d.text((round(ox), round(oy)), ch, font=f, fill=255)
    small = img.resize((W, H), Image.BOX)
    px = list(small.getdata())
    out = bytearray(W * H // 2)
    for i, v in enumerate(px):
        a = min(15, (v * 15 + 127) // 255)
        if i % 2 == 0:
            out[i // 2] |= a
        else:
            out[i // 2] |= a << 4
    return bytes(out), small


def build(fi, src_bytes, preview=None):
    ttf, box = CFG[fi]
    cal = calib(ttf, box)
    glyphs = font.load(src_bytes)
    n = len(glyphs)
    prev_imgs = []
    for i, ch in enumerate(kor.HANGUL):
        k = kor.BASE_KUTEN + i
        raw, im = glyph_bytes(ch, ttf, box, cal)
        glyphs[k] = s13.lz_compress(raw, header=False)
        if preview is not None and i < 400:
            prev_imgs.append(im)
    # write font: count, offsets, data (dedupe identical)
    first = min(struct.unpack_from('<%dI' % n, src_bytes, 4))
    out = bytearray(struct.pack('<I', n) + b'\0' * (4 * n) + src_bytes[4 + 4 * n:first])
    seen = {}
    offs = []
    for g in glyphs:
        if g in seen:
            offs.append(seen[g]); continue
        o = len(out)
        seen[g] = o
        offs.append(o)
        out += g
        if not g.endswith(b'\0'):
            out += b'\0'
    struct.pack_into('<%dI' % n, out, 4, *offs)
    if preview is not None:
        sheet = Image.new('L', (26 * 40, 27 * 10), 0)
        for j, im in enumerate(prev_imgs):
            sheet.paste(im, ((j % 40) * 26, (j // 40) * 27))
        sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(preview)
    print('font', fi, ttf, 'size', cal[0], 'bytes', len(out))
    return bytes(out)


if __name__ == '__main__':
    for fi in (0, 1, 2):
        d = open(os.path.join(ROOT, 'work', 'ui', '%04d.bin' % fi), 'rb').read()
        out = build(fi, d, os.path.join(ROOT, 'work', 'fontprev%d.png' % fi))
        # verify roundtrip of glyph decode
        g = font.load(out)
        assert len(g) == len(font.load(d))
        open(os.path.join(ROOT, 'work', 'ui', '%04d.kor' % fi), 'wb').write(out)
