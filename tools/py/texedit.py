"""Apply Korean text edits to SHTX textures.
spec file work/tex/spec.json : { "<id>": [ op, ... ], ... }
op: {"box":[x0,y0,x1,y1], "text":"한글", "font":"eHv", "fill":"#ffffff" | ["#top","#bottom"],
     "stroke":[w,"#color"], "stroke2":[w,"#color"], "clear":"alpha"|"none"|"#rrggbbaa"|"inpaint",
     "align":"c"|"l"|"r", "valign":"c", "pad":1, "size":optional px, "lines":optional explicit '\n'}
"""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import shtx, s13

ROOT = s13.ROOT
TEX = os.path.join(ROOT, 'work', 'tex')
FONTS = {
    'aLt': 'NanumSquareNeo-aLt.ttf', 'bRg': 'NanumSquareNeo-bRg.ttf', 'cBd': 'NanumSquareNeo-cBd.ttf',
    'dEb': 'NanumSquareNeo-dEb.ttf', 'eHv': 'NanumSquareNeo-eHv.ttf',
    'hgB': 'SeoulHangangB.ttf', 'hgEB': 'SeoulHangangEB.ttf', 'hgM': 'SeoulHangangM.ttf',
    'galmuri': os.path.join('tools', 'fonts', 'Galmuri11.ttf'), 'galmuri9': os.path.join('tools', 'fonts', 'Galmuri9.ttf'),
    'galmuri11b': os.path.join('tools', 'fonts', 'Galmuri11-Bold.ttf'),
}
SS = 4


def col(c):
    c = c.lstrip('#')
    if len(c) == 6:
        c += 'ff'
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4, 6))


def render_text(op, bw, bh):
    """returns RGBA image of size (bw,bh) with text."""
    fontp = os.path.join(ROOT, FONTS.get(op.get('font', 'eHv'), op.get('font', 'eHv')))
    text = op['text']
    lines = text.split('\n')
    s1 = op.get('stroke', [0, '#000000'])
    s2 = op.get('stroke2', [0, '#000000'])
    sw = (s1[0] + s2[0]) + max([abs(v) for k in ('shadow', 'oshadow') if op.get(k) for v in op[k][:2]] or [0])
    pad = op.get('pad', 0)
    pixel = 'galmuri' in op.get('font', '')
    ss = 1 if pixel else SS
    avail_h = bh - 2 * pad
    nlines = len(lines)
    size = op.get('size') or max(6, int((avail_h - 2 * sw) / nlines / 1.08))
    f = ImageFont.truetype(fontp, size * ss)
    spacing = int(op.get('spacing', 0) * ss)
    # measure
    ascent, descent = f.getmetrics()
    lh = int((size * 1.0 + op.get('linegap', 0)) * ss)
    import re as _re
    SEG = _re.compile(r'\{(#[0-9a-fA-F]{6,8})\}(.*?)\{/\}')
    def segs(l):
        out_, pos = [], 0
        for m in SEG.finditer(l):
            if m.start() > pos: out_.append((None, l[pos:m.start()]))
            out_.append((m.group(1), m.group(2))); pos = m.end()
        if pos < len(l): out_.append((None, l[pos:]))
        return out_
    plain = [''.join(t for _, t in segs(l)) for l in lines]
    colored = any(c for l in lines for c, _ in segs(l))
    colimg = Image.new('RGBA', (1, 1))
    widths = [f.getlength(l) for l in plain]
    tw = max(widths) + 2 * sw * ss
    th = lh * nlines + 2 * sw * ss
    canvas = Image.new('RGBA', (int(tw) + 8 * ss, int(th) + 8 * ss), (0, 0, 0, 0))
    # mask of glyphs
    mask = Image.new('L', canvas.size, 0)
    d = ImageDraw.Draw(mask)
    ox = sw * ss + 4 * ss
    cmasks = []
    for i, l in enumerate(lines):
        bb = f.getbbox('한')
        y = 4 * ss + sw * ss + i * lh - bb[1] + (lh - (bb[3] - bb[1])) // 2
        x = ox
        if op.get('align', 'c') == 'c':
            x = ox + (max(widths) - widths[i]) / 2
        elif op.get('align') == 'r':
            x = ox + (max(widths) - widths[i])
        for c_, t_ in segs(l):
            d.text((x, y), t_, font=f, fill=255)
            if c_:
                cmask = Image.new('L', canvas.size, 0)
                ImageDraw.Draw(cmask).text((x, y), t_, font=f, fill=255)
                cmasks.append((c_, cmask))
            x += f.getlength(t_)
    out = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    def dil(m, r):
        if r <= 0:
            return m
        return m.filter(ImageFilter.MaxFilter(2 * int(r * ss) + 1)) if r * ss < 12 else _bigdil(m, int(r * ss))
    if op.get('oshadow'):
        dx, dy, sc_ = op['oshadow']
        mt = dil(mask, s1[0] + s2[0])
        sh = Image.new('L', canvas.size, 0)
        sh.paste(mt, (int(dx * ss), int(dy * ss)))
        out.paste(Image.new('RGBA', canvas.size, col(sc_)), (0, 0), sh)
    if s2[0] > 0:
        m2 = dil(mask, s1[0] + s2[0])
        out.paste(Image.new('RGBA', canvas.size, col(s2[1])), (0, 0), m2)
    if s1[0] > 0:
        m1 = dil(mask, s1[0])
        out.paste(Image.new('RGBA', canvas.size, col(s1[1])), (0, 0), m1)
    if op.get('shadow'):
        dx, dy, sc_ = op['shadow']
        sh = Image.new('L', canvas.size, 0)
        sh.paste(mask, (int(dx * ss), int(dy * ss)))
        out.paste(Image.new('RGBA', canvas.size, col(sc_)), (0, 0), sh)
    fill = op.get('fill', '#ffffff')
    if isinstance(fill, list):
        top, bot = col(fill[0]), col(fill[1])
        grad = Image.new('RGBA', canvas.size)
        gd = ImageDraw.Draw(grad)
        bbox = mask.getbbox() or (0, 0, 1, canvas.size[1])
        for yy in range(canvas.size[1]):
            t = min(1, max(0, (yy - bbox[1]) / max(1, bbox[3] - bbox[1])))
            gd.line([(0, yy), (canvas.size[0], yy)], fill=tuple(int(top[k] + (bot[k] - top[k]) * t) for k in range(4)))
        out.paste(grad, (0, 0), mask)
    else:
        out.paste(Image.new('RGBA', canvas.size, col(fill)), (0, 0), mask)
    for c_, cm in cmasks:
        out.paste(Image.new('RGBA', canvas.size, col(c_)), (0, 0), cm)
    bb = out.getbbox()
    if not bb:
        return Image.new('RGBA', (bw, bh))
    out = out.crop(bb)
    # fit into box
    W = (bw - 2 * pad) * ss if not pixel else bw - 2 * pad
    H = (bh - 2 * pad) * ss if not pixel else bh - 2 * pad
    sx = min(1.0, W / out.width)
    sy = min(1.0, H / out.height)
    if op.get('keep_aspect'):
        sx = sy = min(sx, sy)
    nw = max(1, int(out.width * sx / (1 if pixel else ss)))
    nh = max(1, int(out.height * sy / (1 if pixel else ss)))
    out = out.resize((nw, nh), Image.NEAREST if pixel else Image.LANCZOS)
    res = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
    al = op.get('align', 'c')
    x = pad + ((bw - 2 * pad - nw) // 2 if al == 'c' else (0 if al == 'l' else bw - 2 * pad - nw))
    va = op.get('valign', 'c')
    y = pad + ((bh - 2 * pad - nh) // 2 if va == 'c' else (0 if va == 't' else bh - 2 * pad - nh))
    res.alpha_composite(out, (x, y))
    return res


def _bigdil(m, r):
    import math
    out = m
    step = 5
    while r > 0:
        k = min(r, step)
        out = out.filter(ImageFilter.MaxFilter(2 * k + 1))
        r -= k
    return out


def clear_box(img, box, mode):
    x0, y0, x1, y1 = box
    if mode == 'none':
        return
    if mode == 'alpha':
        img.paste((0, 0, 0, 0), (x0, y0, x1, y1))
    elif mode == 'inpaint':
        # fill each row with interpolation between left/right border pixels
        px = img.load()
        for y in range(y0, y1):
            L = px[max(0, x0 - 1), y]; R = px[min(img.width - 1, x1), y]
            for x in range(x0, x1):
                t = (x - x0 + 1) / (x1 - x0 + 1)
                px[x, y] = tuple(int(L[k] + (R[k] - L[k]) * t) for k in range(4))
    elif mode == 'vinpaint':
        px = img.load()
        for x in range(x0, x1):
            T = px[x, max(0, y0 - 1)]; B = px[x, min(img.height - 1, y1)]
            for y in range(y0, y1):
                t = (y - y0 + 1) / (y1 - y0 + 1)
                px[x, y] = tuple(int(T[k] + (B[k] - T[k]) * t) for k in range(4))
    else:
        img.paste(col(mode), (x0, y0, x1, y1))


STYLES = {
    'orange': {'fill': ['#fff060', '#ff6a00'], 'stroke': [2, '#000000'], 'stroke2': [2, '#ffffff'], 'shadow': [1.5, 1.5, '#3a8cff']},
    'banner': {'fill': ['#ffef50', '#ff8000'], 'stroke': [3, '#a82400'], 'stroke2': [3, '#ffffff'], 'font': 'eHv'},
    'yellow': {'fill': ['#fff57a', '#ffbf00'], 'stroke': [3, '#0a2a8a'], 'stroke2': [3, '#ffffff'], 'font': 'eHv'},
    'blue': {'fill': ['#c8f0ff', '#3a7de0'], 'stroke': [3, '#0b2a8a'], 'stroke2': [3, '#ffffff'], 'font': 'eHv'},
    'green': {'fill': ['#b4f56e', '#27a01a'], 'stroke': [3, '#0b4f12'], 'stroke2': [3, '#ffffff'], 'font': 'eHv'},
    'pink': {'fill': ['#ffb0cc', '#e02a68'], 'stroke': [3, '#6e0a33'], 'stroke2': [3, '#ffffff'], 'font': 'eHv'},
    'header': {'fill': ['#fff69a', '#e0b000'], 'stroke': [2.5, '#0a3cb0'], 'stroke2': [2.5, '#000000'], 'oshadow': [1.5, 2.5, '#f0b800'], 'font': 'eHv', 'size': 30},
    'title': {'fill': ['#fff4a0', '#ffc000'], 'stroke': [2, '#3a2000'], 'stroke2': [2, '#ffffff'], 'font': 'eHv'},
}


def apply(tid, ops):
    src = os.path.join(TEX, 'ui', '%04d.shtx' % tid)
    orig = open(src, 'rb').read()
    img, fmt = shtx.decode(orig)
    img = img.convert('RGBA')
    for op in ops:
        if 'style' in op:
            op = dict(STYLES[op['style']], **op)
        box = op['box']
        clear_box(img, box, op.get('clear', 'alpha'))
        if op.get('text'):
            t = render_text(op, box[2] - box[0], box[3] - box[1])
            img.alpha_composite(t, (box[0], box[1]))
    os.makedirs(os.path.join(TEX, 'out'), exist_ok=True)
    os.makedirs(os.path.join(TEX, 'prev'), exist_ok=True)
    img.save(os.path.join(TEX, 'prev', '%04d.png' % tid))
    open(os.path.join(TEX, 'out', '%04d.shtx' % tid), 'wb').write(shtx.encode(img, orig))


if __name__ == '__main__':
    spec = {}
    for p in sorted(glob.glob(os.path.join(TEX, 'spec*.json'))):
        spec.update(json.load(open(p, encoding='utf-8')))
    only = sys.argv[1:]
    for k, ops in spec.items():
        if only and k not in only:
            continue
        apply(int(k), ops)
        print('applied', k)
