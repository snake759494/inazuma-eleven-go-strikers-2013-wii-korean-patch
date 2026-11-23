"""Move cut-in thumbnails (168x96): cover Japanese logo band and draw Korean move name."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import s13, shtx, texedit

ROOT = s13.ROOT
os.chdir(ROOT)
OVR = json.load(open('work/tex/cut_override.json')) if os.path.exists('work/tex/cut_override.json') else {}


def text_rows(img):
    """score rows by black/white adjacency (logo text has dark outline around bright fill)"""
    w, h = img.size
    px = img.convert('RGB').load()
    score = [0] * h
    for y in range(h):
        for x in range(1, w - 1):
            r, g, b = px[x, y]
            mx_, mn_ = max(r, g, b), min(r, g, b)
            wgt = 1.0 if mn_ > 200 else (0.8 if mx_ > 190 and mx_ - mn_ > 90 else 0)
            if wgt:
                for dx in (-1, 1):
                    r2, g2, b2 = px[x + dx, y]
                    if r2 + g2 + b2 < 100:
                        score[y] += wgt
                        break
    return score


def band(score, h, bh):
    best = (-1, 0)
    for y0 in range(0, h - bh + 1):
        s = sum(score[y0:y0 + bh])
        if s > best[0]:
            best = (s, y0)
    return best[1]


def build(e, bh=34):
    tid = e['id']
    orig = open('work/tex/ui/%04d.shtx' % tid, 'rb').read()
    img, fmt = shtx.decode(orig)
    img = img.convert('RGBA')
    w, h = img.size
    sc = text_rows(img)
    sm = [sum(sc[max(0, i - 2):i + 3]) for i in range(h)]
    mx = max(sm)
    c = sm.index(mx) if mx else h // 2
    mx = mx or 1
    lo = c
    while lo > 0 and sm[lo - 1] > 0.2 * mx: lo -= 1
    hi = c
    while hi < h - 1 and sm[hi + 1] > 0.2 * mx: hi += 1
    bh = max(30, min(62, hi - lo + 8))
    y0 = max(1, min(h - bh - 1, (lo + hi) // 2 - bh // 2))
    ov = OVR.get(str(tid))
    if ov:
        y0, bh = ov
    # blurred + darkened band with feathered edges
    blur = img.filter(ImageFilter.GaussianBlur(5))
    dark = Image.new('RGBA', img.size, (0, 0, 0, 255))
    blur = Image.blend(blur, dark, 0.55)
    m = Image.new('L', img.size, 0)
    ImageDraw.Draw(m).rectangle([0, y0, w, y0 + bh], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(2))
    out = img.copy()
    out.paste(blur, (0, 0), m)
    op = {'text': e['ko'], 'font': 'eHv', 'fill': '#ffffff', 'stroke': [2, '#000000'], 'size': 22}
    t = texedit.render_text(op, w - 8, bh)
    out.alpha_composite(t, (4, y0))
    os.makedirs('work/tex/prev', exist_ok=True)
    out.save('work/tex/prev/%04d.png' % tid)
    open('work/tex/out/%04d.shtx' % tid, 'wb').write(shtx.encode(out, orig))


if __name__ == '__main__':
    L = json.load(open('work/tex/moves_cut.json', encoding='utf8'))
    only = [int(x) for x in sys.argv[1:]]
    for e in L:
        if only and e['id'] not in only:
            continue
        build(e)
    print('done', len(L))
