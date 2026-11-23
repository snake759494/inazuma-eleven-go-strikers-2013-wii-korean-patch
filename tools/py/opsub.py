"""Replace burned-in Japanese OP lyrics with Korean.
usage: python opsub.py <in.mkv> <out.mkv> <ffmpeg.exe>
Pipes raw RGB frames through PIL.
"""
import sys, os, subprocess, json
from PIL import Image, ImageFilter, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
import texedit

W, H, FPS = 640, 480, 24
Y0, Y1 = 384, 432
LINES = [  # (ref time, korean)
    (13.0, '차례차례로'),
    (15.5, '세상은 바뀌어 가'),
    (19.0, '아무도 본 적 없는 신기술이'),
    (21.5, '또 어딘가에서 태어나고 있어'),
    (25.0, '좁은 시야로는 넓은 세상을 다 볼 수 없어'),
    (28.0, '모르는 일, 새로운 일에 도전하고 싶어!'),
    (31.0, '호기심 안테나! 수신 중인 데이터!'),
    (33.5, '뭐가 만들어질까? 기대해!'),
    (36.5, '「모여서 뭘 만들까?」'),
    (39.5, '상상만 해도 두근두근! 콩닥콩닥!'),
    (44.0, '온 세상이 깜짝 놀랄 시대를 만들자!'),
    (47.0, '기대돼! 이제 곧이야!'),
    (50.5, '뉴 스타일로 꿈이 반짝반짝! 번쩍번쩍!'),
    (55.0, '새 시대! 다 함께 만들어 보자!'),
    (62.5, '왔다 왔다 왔다 왔다 왔다 왔다!'),
    (70.0, '만들자 빙글빙글 빙글빙글 빙글!'),
    (75.25, '만들자 빙글빙글!'),
    (78.0, '「새로운 것」이 온다!!!'),
]
NEG = [60.0, 60.5, 63.0, 66.0, 71.0, 71.5, 74.5]  # "Come on!" (English, keep)
LOGO = [(2.6, 11.0), (87.4, 91.0)]
LOGO_Y = 400
KY = 446
LOGO_TEXT = '이나즈마 일레븐 GO 스트라이커즈 2013'


def mask(img):
    """white text pixels with dark outline nearby in lyric band"""
    band = img.crop((0, Y0, W, Y1)).convert('RGB')
    px = band.load()
    w, h = band.size
    out = set()
    for y in range(0, h, 1):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
            if min(r, g, b) > 220:
                for dx, dy in ((3, 0), (-3, 0), (0, 3), (0, -3)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < w and 0 <= yy < h:
                        r2, g2, b2 = px[xx, yy]
                        if r2 + g2 + b2 < 150:
                            out.add((x // 4, y // 4))
                            break
    return out


def iou(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def frames(path, ff):
    p = subprocess.Popen([ff, '-loglevel', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield Image.frombytes('RGB', (W, H), b)


def main(inp, out, ff, ref=None):
    if ref:
        return main_ref(inp, out, ff, ref)
    # pass 1: templates
    want = {round(t * FPS): i for i, (t, _) in enumerate(LINES)}
    negw = {round(t * FPS) for t in NEG}
    tmpl = {}; neg = []
    allm = []
    for fi, im in enumerate(frames(inp, ff)):
        m = mask(im)
        allm.append(m)
        if fi in want:
            tmpl[want[fi]] = m
        if fi in negw:
            neg.append(m)
    # classify
    cls = []
    for m in allm:
        best, bi = 0, -1
        for i, t in tmpl.items():
            v = iou(m, t)
            if v > best:
                best, bi = v, i
        nb = max([iou(m, t) for t in neg] or [0])
        cls.append(bi if best > 0.25 and best > nb else -1)
    # smooth: fill 1-2 frame gaps
    for k in range(1, len(cls) - 2):
        if cls[k] == -1 and cls[k - 1] != -1 and (cls[k + 1] == cls[k - 1] or cls[k + 2] == cls[k - 1]):
            cls[k] = cls[k - 1]
    # per line: union bbox of masks (in 4px cells) + ruby band
    boxes = {}
    for k, c in enumerate(cls):
        if c < 0: continue
        for (x, y) in allm[k]:
            b = boxes.setdefault(c, [999, 999, -1, -1])
            b[0] = min(b[0], x); b[1] = min(b[1], y); b[2] = max(b[2], x); b[3] = max(b[3], y)
    segs = []
    for k, c in enumerate(cls):
        if segs and segs[-1][2] == c and segs[-1][1] == k - 1:
            segs[-1][1] = k
        else:
            segs.append([k, k, c])
    json.dump({'segs': [s for s in segs if s[2] >= 0], 'boxes': boxes}, open(out + '.json', 'w'))
    print([(s[0] / FPS, s[1] / FPS, s[2]) for s in segs if s[2] >= 0])
    write(inp, out, ff, cls, boxes, 1.0, 0)


def main_ref(inp, out, ff, ref):
    j = json.load(open(ref))
    n = sum(1 for _ in frames(inp, ff))
    cls = [-1] * n
    for a0, z, c in j['segs']:
        for k in range(a0, min(n, z + 1)): cls[k] = c
    boxes = {int(k): v for k, v in j['boxes'].items()}
    write(inp, out, ff, cls, boxes, 1.0, -44)


def write(inp, out, ff, cls, boxes, sy, oy):
    # pre-render korean
    rend = {}
    for i, (_, ko) in enumerate(LINES):
        op = {'text': ko, 'font': 'eHv', 'fill': '#fff8c8', 'stroke': [2, '#000000'], 'size': 20}
        rend[i] = texedit.render_text(op, 620, 30)
    logo = texedit.render_text({'text': LOGO_TEXT, 'font': 'eHv', 'fill': ['#fff7a0', '#ffc400'], 'stroke': [2, '#0a2a8a'], 'stroke2': [1.5, '#ffffff'], 'size': 19}, 460, 28)
    # pass 2: write
    enc = subprocess.Popen([ff, '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
                            '-i', inp, '-map', '0:v', '-map', '1:a', '-c:v', 'ffv1', '-c:a', 'copy', out], stdin=subprocess.PIPE)
    for fi, im in enumerate(frames(inp, ff)):
        c = cls[fi]
        t = fi / FPS
        if c >= 0:
            r = rend[c]
            y = int(oy + KY * sy) - r.height // 2
            im = im.convert('RGBA')
            im.alpha_composite(r, ((W - r.width) // 2, y))
            im = im.convert('RGB')
        for a, z in LOGO:
            if a <= t <= z:
                im = im.convert('RGBA')
                im.alpha_composite(logo, ((W - logo.width) // 2, int(oy + LOGO_Y * sy)))
                im = im.convert('RGB')
        enc.stdin.write(im.tobytes())
    enc.stdin.close()
    enc.wait()


if __name__ == '__main__':
    main(*sys.argv[1:5])
