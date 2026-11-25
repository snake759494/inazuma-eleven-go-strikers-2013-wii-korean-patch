"""Tutorial picture overlays (ui 748-806, 328x184): speech bubbles / move names -> Korean.
Each item: (box x0,y0,x1,y1 to erase, mode, text, style)
mode 'fill:#rrggbb' fills box (bubble interior) ; 'inpaint' inpaints box.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import s13, shtx
os.chdir(s13.ROOT)
F = 'NanumSquareNeo-eHv.ttf'
BUB = dict(fill=(20, 20, 20), stroke=None, slant=0)
YEL = dict(fill=(255, 220, 40), stroke=(60, 30, 0), slant=0)
CAP = dict(fill=(255, 220, 60), stroke=(150, 20, 0), slant=0.15)
SPEC = {
 748: [((64, 6, 118, 26), 'fill', '좋아!', YEL), ((257, 10, 306, 32), 'fill', '막아라!', BUB)],
 758: [((128, 64, 172, 81), 'fill', '가자!', BUB)],
 763: [((118, 113, 160, 130), 'fill', '가자!', BUB)],
 766: [((100, 37, 162, 55), 'fill', '받아라!', BUB)],
 768: [((88, 31, 136, 49), 'fill', '맡겨!', BUB), ((185, 33, 234, 50), 'fill', '받아라!', BUB)],
 782: [((134, 6, 180, 25), 'fill', '좋아!', YEL)],
 785: [((40, 145, 142, 168), 'inpaint', '슛 체인', CAP)],
 787: [((5, 136, 130, 158), 'inpaint', '슛 체인', CAP), ((150, 40, 312, 150), 'inpaint', '사이드와인더', dict(fill=(255, 255, 255), stroke=(0, 0, 0), slant=0.0, rot=12))],
 789: [((92, 37, 140, 55), 'fill', '맡겨!', BUB), ((40, 145, 142, 168), 'inpaint', '슛 블록', CAP)],
 793: [((80, 74, 192, 92), 'inpaint', '대국왕화', dict(fill=(255, 220, 40), stroke=(40, 30, 10), slant=0))],
 794: [((86, 37, 136, 52), 'fill', '받아라!', BUB)],
 797: [((50, 92, 186, 140), 'inpaint', '찰나 부스트', dict(fill=(255, 255, 255), stroke=(0, 0, 0), slant=0.1))],
 799: [((84, 17, 146, 38), 'fill', '올라가!', BUB), ((222, 82, 284, 112), 'inpaint', '공격 업!', dict(fill=(255, 80, 120), stroke=(255, 255, 120), slant=0))],
 800: [((84, 17, 146, 38), 'fill', '내려가!', BUB), ((222, 82, 284, 112), 'inpaint', '수비 업!', dict(fill=(60, 140, 255), stroke=(200, 255, 255), slant=0))],
 806: [((60, 127, 110, 147), 'fill', '흔들어!', dict(fill=(255, 230, 40), stroke=(30, 60, 160), slant=0)), ((60, 34, 80, 40), 'fill', '흔들어!', dict(fill=(255, 230, 40), stroke=None, slant=0))],
}


def text_img(t, w, h, st):
    S = 4
    size = h * S
    f = ImageFont.truetype(F, size)
    bb = f.getbbox(t)
    sw = max(1, int(h * 0.12)) * S if st['stroke'] else 0
    cw, ch = bb[2] - bb[0] + 2 * sw + 8, bb[3] - bb[1] + 2 * sw + 8
    m = Image.new('L', (cw, ch)); ImageDraw.Draw(m).text((sw + 4 - bb[0], sw + 4 - bb[1]), t, font=f, fill=255)
    out = Image.new('RGBA', (cw, ch))
    if sw:
        o = m; k = sw
        while k > 0:
            s = min(k, 6); o = o.filter(ImageFilter.MaxFilter(2 * s + 1)); k -= s
        out.paste(st['stroke'] + (255,), (0, 0), o)
    out.paste(st['fill'] + (255,), (0, 0), m)
    if st.get('slant'):
        sh = st['slant']; out = out.transform((int(cw + ch * sh), ch), Image.AFFINE, (1, sh, -ch * sh, 0, 1, 0), Image.BICUBIC)
    if st.get('rot'):
        out = out.rotate(st['rot'], Image.BICUBIC, expand=True)
    out = out.crop(out.getbbox())
    sc = min(w / out.width, h / out.height)
    return out.resize((max(1, int(out.width * sc)), max(1, int(out.height * sc))), Image.LANCZOS)


def main():
    a0 = s13.Archive('work/orig/ui.bin')
    for i, items in SPEC.items():
        orig = a0.get(i)
        img, _ = shtx.decode(orig); img = img.convert('RGBA')
        a = np.array(img)
        for (x0, y0, x1, y1), mode, t, st in items:
            sub = a[y0:y1, x0:x1]
            if mode == 'fill':
                px = sub[..., :3].reshape(-1, 3).astype(int)
                lum = px.sum(1)
                bg = np.median(px[lum > np.percentile(lum, 60)], 0).astype(np.uint8)
                if st is YEL:
                    bg = np.array([255, 255, 255], np.uint8)
                    bgm = px[lum > 600]
                    if len(bgm): bg = np.median(bgm, 0).astype(np.uint8)
                sub[..., :3] = bg
            else:
                m = np.full(sub.shape[:2], 255, np.uint8)
                big = a[max(0, y0 - 8):y1 + 8, max(0, x0 - 8):x1 + 8, :3].copy()
                mm = np.zeros(big.shape[:2], np.uint8); oy, ox = y0 - max(0, y0 - 8), x0 - max(0, x0 - 8)
                mm[oy:oy + (y1 - y0), ox:ox + (x1 - x0)] = 255
                big = cv2.inpaint(np.ascontiguousarray(big), mm, 7, cv2.INPAINT_TELEA)
                a[max(0, y0 - 8):y1 + 8, max(0, x0 - 8):x1 + 8, :3] = big
        img = Image.fromarray(a)
        for (x0, y0, x1, y1), mode, t, st in items:
            pad = 1
            ti = text_img(t, x1 - x0 - 2 * pad, y1 - y0 - 2 * pad, st)
            img.alpha_composite(ti, (x0 + (x1 - x0 - ti.width) // 2, y0 + (y1 - y0 - ti.height) // 2))
        img.save('work/tex/prev/%04d_ko.png' % i)
        open('work/tex/out/%04d.shtx' % i, 'wb').write(shtx.encode(img, orig))
    print('done', len(SPEC))


if __name__ == '__main__':
    main()
