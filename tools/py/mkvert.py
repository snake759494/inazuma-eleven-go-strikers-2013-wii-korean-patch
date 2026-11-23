"""Vertical name plates (2722-2778): rebuild with Korean syllables, one per dark box."""
import sys, os, json, colorsys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import s13, shtx, boxes

ROOT = s13.ROOT
os.chdir(ROOT)
g = json.load(open('work/text/glossary_players.json', encoding='utf8'))
gm = {k.replace('　', '').replace(' ', ''): v for k, v in g.items()}
A = json.load(open('work/tex/catalog_a.json', encoding='utf8')) + json.load(open('work/tex/catalog_b.json', encoding='utf8'))
FONT = 'NanumSquareNeo-eHv.ttf'


def vivid(img, box):
    """most saturated bright colour inside box"""
    best = (0, (255, 255, 255))
    px = img.load()
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            r, gg, b, a = px[x, y]
            if a < 200: continue
            h, l, s = colorsys.rgb_to_hls(r / 255, gg / 255, b / 255)
            sc = s * l * (1 if l > 0.35 else 0)
            if sc > best[0]: best = (sc, (r, gg, b))
    return best[1] if best[0] > 0.15 else (255, 255, 255)


def glyph(ch, size, colr):
    S = 4
    f = ImageFont.truetype(FONT, int(size * S * 0.82))
    im = Image.new('L', (size * S, size * S), 0)
    d = ImageDraw.Draw(im)
    bb = f.getbbox(ch)
    d.text(((size * S - (bb[2] - bb[0])) / 2 - bb[0], (size * S - (bb[3] - bb[1])) / 2 - bb[1]), ch, font=f, fill=255)
    m = im.resize((size, size), Image.LANCZOS)
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.paste(Image.new('RGBA', (size, size), colr + (255,)), (0, 0), m)
    return out


def column(out, d, text_parts, cx, top, size, gap, maxy):
    n = sum(len(t) for t, _ in text_parts)
    if n == 0:
        return
    need = n * (size + gap)
    k = min(1.0, (maxy - top) / need)
    size = max(10, int(size * k)); gap = max(2, int(gap * k))
    y = top
    for t, colr in text_parts:
        for ch in t:
            x0 = cx - size // 2
            d.rounded_rectangle([x0, y, x0 + size - 1, y + size - 1], radius=max(2, size // 8), fill=(18, 18, 30, 255))
            gl = glyph(ch, int(size * 0.96), colr)
            out.alpha_composite(gl, (x0 + (size - gl.width) // 2, y + (size - gl.height) // 2))
            y += size + gap


def kname(jp, fallback):
    j = jp.replace(' ', '').replace('　', '').replace('・', '')
    v = g.get(jp) or gm.get(j)
    if v:
        p = v.replace(' ', '　').split('　')
        return p[0], ''.join(p[1:])
    return fallback.replace(' ', ''), ''


def build(e):
    tid = e['id']
    orig = open('work/tex/ui/%04d.shtx' % tid, 'rb').read()
    img, fmt = shtx.decode(orig)
    img = img.convert('RGBA')
    bs = boxes.detect(img, 1)
    if not bs:
        return None
    jps = e['jp'].split('|'); kos = e['ko'].split('|')
    first = bs[0]
    c0 = (first[0] + first[2]) // 2
    main = [b for b in bs if abs((b[0] + b[2]) // 2 - c0) <= 18]
    other = [b for b in bs if b not in main]
    fam, given = kname(jps[0], kos[0])
    lastm = main[-1]
    c_fam = vivid(img, first)
    merged = (lastm[3] - lastm[1]) > 1.6 * (lastm[2] - lastm[0])
    c_giv = (255, 255, 255) if (merged or lastm is first) else vivid(img, lastm)
    if not given:
        h = (len(fam) + 1) // 2
        fam, given = fam[:h], fam[h:]
        if merged or lastm is first: c_giv = c_fam
    sz = min(b[2] - b[0] for b in main)
    out = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    column(out, d, [(fam, c_fam), (given, c_giv)], c0, first[1], sz, 5, img.height - 2)
    res = fam + given
    if len(jps) > 1 and other:
        f2, g2 = kname(jps[1], kos[1] if len(kos) > 1 else jps[1])
        cs = sorted((b[0] + b[2]) // 2 for b in other)
        cx2 = cs[len(cs) // 2]
        cx2 = min(max(cx2, sz // 2 + 1), img.width - sz // 2 - 1)
        top2 = min(b[1] for b in other)
        sz2 = min(min(b[2] - b[0], b[3] - b[1]) for b in other)
        column(out, d, [(f2 + g2, vivid(img, other[0]))], cx2, top2, max(14, sz2), 4, img.height - 2)
        res += '|' + f2 + g2
    out.save('work/tex/prev/%04d.png' % tid)
    open('work/tex/out/%04d.shtx' % tid, 'wb').write(shtx.encode(out, orig))
    return res


if __name__ == '__main__':
    os.makedirs('work/tex/out', exist_ok=True); os.makedirs('work/tex/prev', exist_ok=True)
    for e in A:
        if 2722 <= e['id'] <= 2778:
            print(e['id'], e['jp'], build(e))
