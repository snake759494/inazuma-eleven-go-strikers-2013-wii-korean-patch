"""Special-move caption textures (scn.bin / scn_sh.bin U8 'Cap_*' layouts) -> Korean.
needs work/cap/names.json {cap_key: {"jp":..., "ko":...}}
writes work/cap/out/<archive>_<index>.bin (decompressed U8) and previews.
"""
import sys, os, json, re, statistics
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import s13, tpl, tex0

ROOT = s13.ROOT
os.chdir(ROOT)
FONT = 'NanumSquareNeo-eHv.ttf'
WHOLE = re.compile(r'(bg\d*|top|btm|all|L|R)$')
LETTER = re.compile(r'_(\d{3})([a-z]+)$')
SS = 3


def style(img):
    px = [p for p in img.getdata() if p[3] > 200]
    if not px:
        return (255, 255, 255), (0, 0, 0), True
    lum = lambda p: p[0] * 3 + p[1] * 6 + p[2]
    bright = [p for p in px if lum(p) > 1500]
    dark = [p for p in px if lum(p) < 600]
    med = lambda L: tuple(int(statistics.median(c[i] for c in L)) for i in range(3))
    if len(bright) < len(px) * 0.12:
        return med(dark) if dark else (0, 0, 0), med(dark) if dark else (0, 0, 0), True
    return med(bright), (med(dark) if dark else (0, 0, 0)), False


def draw(text, w, h, fill, outline, sil, target=None):
    if not text or w < 8 or h < 8:
        return Image.new('RGBA', (w, h))
    pad = max(2, int(min(w, h) * 0.06))
    sw = max(2, int(min(h, w * 1.2) * 0.07))
    size = h
    f = ImageFont.truetype(FONT, size * SS)
    bb = f.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    S = sw * SS
    cw, ch = tw + 2 * S + 8, th + 2 * S + 8
    m = Image.new('L', (cw, ch), 0)
    ImageDraw.Draw(m).text((S + 4 - bb[0], S + 4 - bb[1]), text, font=f, fill=255)
    out = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    k = S
    mo = m
    while k > 0:
        s_ = min(k, 6)
        mo = mo.filter(ImageFilter.MaxFilter(2 * s_ + 1)); k -= s_
    out.paste(Image.new('RGBA', (cw, ch), outline + (255,)), (0, 0), mo)
    if not sil:
        out.paste(Image.new('RGBA', (cw, ch), fill + (255,)), (0, 0), m)
    # dynamic slant
    sh = 0.18
    out = out.transform((int(cw + ch * sh), ch), Image.AFFINE, (1, sh, -ch * sh, 0, 1, 0), Image.BICUBIC)
    out = out.crop(out.getbbox())
    W, H = w - 2 * pad, h - 2 * pad
    sc = min(W / out.width, H / out.height)
    if target:
        sc = min(sc * 1.0, target / out.height, W / out.width)
    nw, nh = max(1, int(out.width * min(sc, W / out.width))), max(1, int(out.height * sc))
    nw = min(W, int(out.width * sc * 1.0)) if out.width * sc <= W else W
    if nw < 1 or nh < 1:
        return Image.new('RGBA', (w, h))
    out = out.resize((nw, nh), Image.LANCZOS)
    res = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    res.alpha_composite(out, ((w - nw) // 2, (h - nh) // 2))
    return res


def split(syl, k):
    n = len(syl)
    if n <= k:
        return list(syl) + [''] * (k - n)
    out = []
    base, extra = divmod(n, k)
    p = 0
    for i in range(k):
        c = base + (1 if i < extra else 0)
        out.append(''.join(syl[p:p + c])); p += c
    return out


def process(d, ko):
    d = bytearray(d)
    files = [(fn, o) for fn, o, s, e in tpl.u8_list(bytes(d)) if fn.endswith('.tpl')]
    layers = {}
    for fn, o in files:
        stem = fn[:-4]
        m = LETTER.search(stem)
        if m and not WHOLE.search(m.group(2)):
            idx = int(m.group(1))
            layers.setdefault(idx // 10, []).append((idx, fn, o))
    syl = [c for c in ko if c != ' ']
    previews = []
    for fn, o in files:
        stem = fn[:-4]
        if 'num' in stem:
            continue
        for t in tpl.tpl_images(bytes(d), o):
            if t['fmt'] not in tex0.BLK:
                continue
            img = tex0.decode(bytes(d), t).convert('RGBA')
            fill, outl, sil = style(img)
            m = LETTER.search(stem)
            if m and not WHOLE.search(m.group(2)):
                grp = sorted(layers[int(m.group(1)) // 10])
                sizes = {}
                for g in grp:
                    tt = tpl.tpl_images(bytes(d), g[2])[0]
                    sizes[g[1]] = tt['w'] * tt['h']
                med = statistics.median(sizes.values())
                elig = [g[1] for g in grp if sizes[g[1]] >= 0.6 * med]
                if len(elig) < min(len(syl), len(grp)):
                    elig = [g[1] for g in grp]
                parts = split(syl, len(elig))
                text = parts[elig.index(fn)] if fn in elig else ''
                hs = [tpl.tpl_images(bytes(d), g[2])[0]['h'] for g in grp if g[1] in elig]
                tgt = int(statistics.median(hs) * 0.82)
            else:
                text = ko; tgt = None
            new = draw(text, t['w'], t['h'], fill, outl, sil, tgt)
            if t['fmt'] in (0, 1, 2, 3):
                # intensity formats: keep grayscale look
                g = new.convert('LA').convert('RGBA')
                new = g
            d = bytearray(tex0.encode_into(bytes(d), t, new) if t['fmt'] in (5, 6, 14) else enc_gray(bytes(d), t, new))
            previews.append(new)
    return bytes(d), previews


def enc_gray(d, t, img):
    """encode I4/I8/IA4/IA8"""
    import struct
    d = bytearray(d)
    w, h, fmt = t['w'], t['h'], t['fmt']
    bw, bh, bpp = tex0.BLK[fmt]
    px = img.load()
    pos = t['data']
    for by in range(0, h, bh):
        for bx in range(0, w, bw):
            vals = []
            for k in range(bw * bh):
                x = min(w - 1, bx + k % bw); y = min(h - 1, by + k // bw)
                r, g, b, a = px[x, y]
                vals.append(((r * 3 + g * 6 + b) // 10, a))
            if fmt == 2:
                for k, (l, a) in enumerate(vals):
                    d[pos + k] = ((a >> 4) << 4) | (l >> 4)
                pos += 32
            elif fmt == 3:
                for k, (l, a) in enumerate(vals):
                    d[pos + 2 * k] = a; d[pos + 2 * k + 1] = l
                pos += 32
            elif fmt == 0:
                for k in range(0, 64, 2):
                    d[pos + k // 2] = ((vals[k][0] >> 4) << 4) | (vals[k + 1][0] >> 4)
                pos += 32
            elif fmt == 1:
                for k, (l, a) in enumerate(vals):
                    d[pos + k] = l
                pos += 32
    return bytes(d)


if __name__ == '__main__':
    names = json.load(open('work/cap/names.json', encoding='utf8'))
    os.makedirs('work/cap/out', exist_ok=True); os.makedirs('work/cap/prev', exist_ok=True)
    only = [a for a in sys.argv[1:] if not a.startswith('--')]
    arcs = {}
    for key, v in names.items():
        if only and key not in only:
            continue
        if '--missing' in sys.argv and os.path.exists('work/cap/out/%s.bin' % key):
            continue
        an, i = key.rsplit('_', 1)
        a = arcs.get(an) or arcs.setdefault(an, s13.Archive('work/orig/%s.bin' % an if os.path.exists('work/orig/%s.bin' % an) else 'work/witx/files/%s.bin' % an))
        d = s13.lz_decompress(a.raw(int(i)))
        nd, prev = process(d, v['ko'])
        open('work/cap/out/%s.bin' % key, 'wb').write(nd)
        if prev:
            W = sum(p.width for p in prev[:12]) + 4 * 12; H = max(p.height for p in prev[:12])
            sh = Image.new('RGBA', (W, H), (70, 70, 110, 255)); x = 0
            for p in prev[:12]:
                sh.alpha_composite(p, (x, 0)); x += p.width + 4
            sh.save('work/cap/prev/%s.png' % key)
    print('done', len(names))
