"""Main menu icons in grp.bin #4686 (BRRES TEX0)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageFilter
import s13, tex0, texedit

os.chdir(s13.ROOT)
IDX = 4686
SPEC = {
    'bushitu': ('부실', ['#ffffff', '#cfe8ff'], '#0b3c9a'),
    'exhibition': ('엑시비션', ['#d6ff5a', '#4fd21a'], '#0b4f12'),
    'minigame': ('미니게임', ['#ffffff', '#ffe0c0'], '#a3300a'),
    'settei': ('설정', ['#ffffff', '#efe0ff'], '#4b1f99'),
    'tournament': ('토너먼트', ['#fff38a', '#ffcc00'], '#3a2a00'),
    'tuushin': ('통신', ['#ffffff', '#ffe0f2'], '#9a0b5a'),
}


def fix(img, key):
    img = img.convert('RGBA')
    w, h = img.size
    px = img.load()
    y0, y1 = 102, 130
    ext = [x for x in range(w) if px[x, y0 - 2][3] > 200]
    bx0, bx1 = min(ext), max(ext)
    for x in range(w):
        T = px[x, y0 - 1]; B = px[x, y1 + 1]
        for y in range(y0, y1 + 1):
            if x < bx0 - 2 or x > bx1 + 2:
                px[x, y] = (0, 0, 0, 0)
            elif bx0 + 3 <= x <= bx1 - 3:
                px[x, y] = T
            else:
                px[x, y] = T
    name, fill, stroke = SPEC[key]
    op = {'text': name, 'font': 'eHv', 'fill': fill, 'stroke': [2.5, stroke], 'stroke2': [2, '#ffffff'], 'size': 24}
    t = texedit.render_text(op, w - 8, 34)
    img.alpha_composite(t, (4, 98))
    return img


if __name__ == '__main__':
    a = s13.Archive('work/orig/grp.bin' if os.path.exists('work/orig/grp.bin') else 'work/witx/files/grp.bin')
    d = s13.lz_decompress(a.raw(IDX))
    ts = tex0.find_tex0(d)
    os.makedirs('work/tex/mm/out', exist_ok=True)
    for t in ts:
        n = t['name']
        if not n.startswith('ico_'):
            continue
        key = n[4:-1]
        img = tex0.decode(d, t)
        new = fix(img, key)
        new.save('work/tex/mm/out/%s.png' % n)
        d = tex0.encode_into(d, t, new)
    open('work/tex/mm/4686.new', 'wb').write(d)
    print('ok')
