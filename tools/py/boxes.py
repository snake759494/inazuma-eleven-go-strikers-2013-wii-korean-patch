"""Detect sprite bounding boxes (alpha connected components) and save annotated preview.
python boxes.py <id> [gap]
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFilter
import s13

TEX = os.path.join(s13.ROOT, 'work', 'tex')


def detect(img, gap=3, thr=16):
    a = img.split()[3].point(lambda v: 255 if v > thr else 0)
    if gap:
        a = a.filter(ImageFilter.MaxFilter(2 * gap + 1))
    w, h = a.size
    px = a.load()
    seen = bytearray(w * h)
    boxes = []
    for y in range(h):
        for x in range(w):
            if px[x, y] and not seen[y * w + x]:
                st = [(x, y)]; seen[y * w + x] = 1
                x0 = x1 = x; y0 = y1 = y
                while st:
                    cx, cy = st.pop()
                    x0 = min(x0, cx); x1 = max(x1, cx); y0 = min(y0, cy); y1 = max(y1, cy)
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= nx < w and 0 <= ny < h and px[nx, ny] and not seen[ny * w + nx]:
                            seen[ny * w + nx] = 1; st.append((nx, ny))
                bx = [max(0, x0 - 0), max(0, y0 - 0), min(w, x1 + 1), min(h, y1 + 1)]
                if gap:
                    bx = [min(w, bx[0] + gap), min(h, bx[1] + gap), max(0, bx[2] - gap), max(0, bx[3] - gap)]
                if (bx[2] - bx[0]) * (bx[3] - bx[1]) >= 30:
                    boxes.append(bx)
    boxes.sort(key=lambda b: (b[1] // 16, b[0]))
    return boxes


if __name__ == '__main__':
    tid = int(sys.argv[1]); gap = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    img = Image.open(os.path.join(TEX, 'ui', '%04d.png' % tid)).convert('RGBA')
    bs = detect(img, gap)
    sc = max(1, 1200 // max(img.size))
    bg = Image.new('RGBA', img.size, (70, 70, 110, 255)); bg.alpha_composite(img)
    bg = bg.resize((img.width * sc, img.height * sc), Image.NEAREST)
    d = ImageDraw.Draw(bg)
    for i, b in enumerate(bs):
        d.rectangle([b[0] * sc, b[1] * sc, b[2] * sc - 1, b[3] * sc - 1], outline=(255, 0, 0))
        d.text((b[0] * sc + 1, b[1] * sc + 1), str(i), fill=(255, 255, 0))
    os.makedirs(os.path.join(TEX, 'ann'), exist_ok=True)
    bg.convert('RGB').save(os.path.join(TEX, 'ann', '%04d.png' % tid))
    json.dump(bs, open(os.path.join(TEX, 'ann', '%04d.json' % tid), 'w'))
    for i, b in enumerate(bs):
        print(i, b)
