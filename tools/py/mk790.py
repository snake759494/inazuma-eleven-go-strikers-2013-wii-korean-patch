"""ui 790: tutorial picture move name 'ハンターズネット' -> 헌터스 넷."""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import s13, shtx
os.chdir(s13.ROOT)
orig = s13.Archive('work/orig/ui.bin').get(790)
img, _ = shtx.decode(orig); img = img.convert('RGBA')
a = np.array(img)
H, W = a.shape[:2]
poly = np.zeros((H, W), np.uint8)
cv2.fillPoly(poly, [np.array([(40, 78), (70, 150), (305, 64), (292, 2)], np.int32)], 255)
cv2.circle(poly, (160, 107), 12, 0, -1)
r, g, b = [a[..., i].astype(int) for i in range(3)]
lum = (r * 3 + g * 6 + b) // 10
sat = np.max(a[..., :3], 2).astype(int) - np.min(a[..., :3], 2)
m = poly.copy()
m = cv2.dilate(m, np.ones((3, 3), np.uint8))
a[..., :3] = cv2.inpaint(np.ascontiguousarray(a[..., :3]), m, 5, cv2.INPAINT_TELEA)
img = Image.fromarray(a)
S = 4
f = ImageFont.truetype('NanumSquareNeo-eHv.ttf', 40 * S)
t = '헌터스 넷'
bb = f.getbbox(t)
cw, ch = bb[2] - bb[0] + 24 * S, bb[3] - bb[1] + 24 * S
mk = Image.new('L', (cw, ch)); ImageDraw.Draw(mk).text((12 * S - bb[0], 12 * S - bb[1]), t, font=f, fill=255)
o = mk
for _ in range(3): o = o.filter(ImageFilter.MaxFilter(7))
lay = Image.new('RGBA', (cw, ch)); lay.paste((0, 0, 0, 255), (0, 0), o); lay.paste((255, 255, 255, 255), (0, 0), mk)
lay = lay.resize((cw // S, ch // S), Image.LANCZOS).rotate(24, Image.BICUBIC, expand=True)
img.alpha_composite(lay, (int(166 - lay.width / 2), int(78 - lay.height / 2)))
img.save('work/tex/prev/0790_ko.png')
open('work/tex/out/0790.shtx', 'wb').write(shtx.encode(img, orig))
