"""grp.bin 3D textures with Japanese: clubroom sign (3931 GDS_kanban), traditional scoreboard (3808 MP15_scoreboard00)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import s13, tex0
os.chdir(s13.ROOT)
OUT = 'work/tex/grp'; os.makedirs(OUT, exist_ok=True)
JOBS = {3931: ('GDS_kanban', [((8, 6, 56, 122), '축구부', 'NanumMyeongjo', (40, 22, 10), True)]),
        3808: ('MP15_scoreboard00', [((8, 46, 74, 128), '전', 'brush', (20, 20, 20), False)])}


def font(kind, size):
    for f in ('SeoulHangangEB.ttf',):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)


def main():
    a = s13.Archive('work/orig/grp.bin')
    for i, (name, items) in JOBS.items():
        d = s13.lz_decompress(a.raw(i))
        t = [t for t in tex0.find_tex0(d) if t.get('name') == name][0]
        img = tex0.decode(d, t).convert('RGBA')
        arr = np.array(img)
        for (x0, y0, x1, y1), text, fk, col, vert in items:
            sub = arr[y0:y1, x0:x1, :3]
            lum = sub.astype(int).sum(2)
            m = (lum < np.percentile(lum, 50) - 40).astype(np.uint8) * 255
            m = cv2.dilate(m, np.ones((5, 5), np.uint8))
            arr[y0:y1, x0:x1, :3] = cv2.inpaint(np.ascontiguousarray(sub), m, 5, cv2.INPAINT_TELEA)
        img = Image.fromarray(arr)
        dr = ImageDraw.Draw(img)
        for (x0, y0, x1, y1), text, fk, col, vert in items:
            w, h = x1 - x0, y1 - y0
            if vert:
                ch = h // len(text)
                f = font(fk, int(min(w, ch) * 0.95))
                for k, c in enumerate(text):
                    bb = f.getbbox(c)
                    dr.text((x0 + (w - (bb[2] - bb[0])) // 2 - bb[0], y0 + k * ch + (ch - (bb[3] - bb[1])) // 2 - bb[1]), c, font=f, fill=col + (255,))
            else:
                f = font(fk, int(min(w, h) * 0.9))
                bb = f.getbbox(text)
                dr.text((x0 + (w - (bb[2] - bb[0])) // 2 - bb[0], y0 + (h - (bb[3] - bb[1])) // 2 - bb[1]), text, font=f, fill=col + (255,))
        img.save('work/tex/prev/grp_%d.png' % i)
        open('%s/%d.new' % (OUT, i), 'wb').write(tex0.encode_into(d, t, img))
    print('ok')


if __name__ == '__main__':
    main()
