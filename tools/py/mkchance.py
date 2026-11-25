"""ui 850: random/shuffle/roulette chance ribbons -> Korean (inpaint + per-glyph rotated text)."""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import s13, shtx
os.chdir(s13.ROOT)
FONT = 'NanumSquareNeo-eHv.ttf'
# (erase bbox, left-centre, right-centre, glyph height, text)
B = [((62, 14, 420, 122), (112, 92), (392, 42), 50, '랜덤 찬스!'),
     ((40, 168, 420, 252), (88, 222), (398, 205), 48, '셔플 찬스!'),
     ((40, 312, 430, 395), (88, 362), (408, 336), 50, '룰렛 찬스!')]


def glyph(ch, h):
    S = 4
    f = ImageFont.truetype(FONT, h * S)
    bb = f.getbbox(ch)
    w = max(bb[2] - bb[0], h * S // 3) + 40 * S
    H = h * S + 40 * S
    m = Image.new('L', (w, H)); ImageDraw.Draw(m).text((20 * S - bb[0], 20 * S + (h * S - (bb[3] - bb[1])) // 2 - bb[1]), ch, font=f, fill=255)
    def grow(img, r):
        while r > 0:
            k = min(r, 6); img = img.filter(ImageFilter.MaxFilter(2 * k + 1)); r -= k
        return img
    red = grow(m, int(h * 0.09 * S)); dark = grow(red, int(h * 0.05 * S))
    out = Image.new('RGBA', (w, H))
    out.paste((88, 40, 0, 255), (0, 0), dark)
    out.paste((248, 40, 0, 255), (0, 0), red)
    grad = Image.new('RGBA', (w, H))
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        t = min(1, max(0, (y - 20 * S) / (h * S)))
        c = tuple(int(a + (b - a) * t) for a, b in zip((250, 250, 170), (248, 120, 50)))
        gd.line([(0, y), (w, y)], fill=c + (255,))
    out.paste(grad, (0, 0), m)
    return out.resize((w // S, H // S), Image.LANCZOS), (bb[2] - bb[0]) / S


def main():
    orig = s13.Archive('work/orig/ui.bin').get(850)
    img, _ = shtx.decode(orig); img = img.convert('RGBA')
    a = np.array(img)
    for box, L, R, h, text in B:
        x0, y0, x1, y1 = box
        sub = a[y0:y1, x0:x1]
        r, g, b = sub[..., 0].astype(int), sub[..., 1].astype(int), sub[..., 2].astype(int)
        m = ((r >= 230) & ~((g > 200) & (b < 120) & (r > 240) & False)).astype(np.uint8) * 255
        m = cv2.dilate(m, np.ones((11, 11), np.uint8))
        rgb = cv2.inpaint(np.ascontiguousarray(sub[..., :3]), m, 6, cv2.INPAINT_TELEA)
        al = cv2.inpaint(np.ascontiguousarray(np.where(m > 0, 0, sub[..., 3]).astype(np.uint8)), m, 6, cv2.INPAINT_TELEA)
        al = np.where(al < 200, 0, 255).astype(np.uint8)
        a[y0:y1, x0:x1, :3] = np.where(m[..., None] > 0, rgb, sub[..., :3])
        a[y0:y1, x0:x1, 3] = np.where(m > 0, al, sub[..., 3])
    img = Image.fromarray(a)
    for box, L, R, h, text in B:
        ang = math.atan2(R[1] - L[1], R[0] - L[0])
        gl = [glyph(c, h) if c != ' ' else None for c in text]
        widths = [g[1] + h * 0.12 if g else h * 0.3 for g in gl]
        tot = sum(widths); span = math.hypot(R[0] - L[0], R[1] - L[1])
        sc = min(1.45, span / tot)
        d = (span - tot * sc) / 2
        for g, w in zip(gl, widths):
            w *= sc
            if g:
                gi = g[0]
                if sc != 1: gi = gi.resize((max(1, int(gi.width * sc)), max(1, int(gi.height * sc))), Image.LANCZOS)
                gi = gi.rotate(-math.degrees(ang), Image.BICUBIC, expand=True)
                cx = L[0] + math.cos(ang) * (d + w / 2); cy = L[1] + math.sin(ang) * (d + w / 2)
                img.alpha_composite(gi, (int(cx - gi.width / 2), int(cy - gi.height / 2)))
            d += w
    img.save('work/tex/prev/0850_ko.png')
    os.makedirs('work/tex/out', exist_ok=True)
    open('work/tex/out/0850.shtx', 'wb').write(shtx.encode(img, orig))


if __name__ == '__main__':
    main()
