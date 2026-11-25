import sys
from PIL import Image, ImageDraw
out = sys.argv[1]; ids = [int(x) for x in sys.argv[2:]]
S = 2; W, H = 328 * S, 184 * S
sh = Image.new('RGB', (W * 2, H * ((len(ids) + 1) // 2)))
for k, i in enumerate(ids):
    im = Image.open('work/tex/ui/%04d.png' % i).convert('RGB').resize((W, H), Image.NEAREST)
    d = ImageDraw.Draw(im)
    for x in range(0, 328, 20): d.line([(x * S, 0), (x * S, H)], fill=(0, 255, 255) if x % 100 else (255, 0, 255))
    for y in range(0, 184, 20): d.line([(0, y * S), (W, y * S)], fill=(0, 255, 255) if y % 100 else (255, 0, 255))
    d.text((4, 4), str(i), fill=(255, 0, 0))
    sh.paste(im, ((k % 2) * W, (k // 2) * H))
sh.save(out)
