"""Generate spec for face+name textures (192x128) : name label at bottom right."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
import s13, boxes

ROOT = s13.ROOT
os.chdir(ROOT)
g = json.load(open('work/text/glossary_players.json', encoding='utf8'))
fix = {'シニスキー': '시니스키'}
A = json.load(open('work/tex/catalog_a.json', encoding='utf8')) + json.load(open('work/tex/catalog_b.json', encoding='utf8'))
spec = {}
report = []
for e in A:
    if not (1354 <= e['id'] <= 1743):
        continue
    ko = fix.get(e['jp']) or g.get(e['jp']) or e['ko']
    ko = ko.replace('　', ' ')
    img = Image.open('work/tex/ui/%04d.png' % e['id']).convert('RGBA')
    al = img.split()[3]
    rows = [y for y in range(80, 128) if any(al.getpixel((x, y)) > 40 for x in range(128, 192))]
    # find the last empty-row gap: name block is the run after it
    start = None
    for y in range(127, 80, -1):
        if y in rows and (y - 1) not in rows:
            start = y; break
    bb = None
    if start is not None:
        reg = img.crop((128, start, 192, 128)).split()[3].point(lambda v: 255 if v > 40 else 0)
        b = reg.getbbox()
        if b and b[3] - b[1] <= 18:
            bb = (b[0], b[1] + start - 98, b[2], b[3] + start - 98)
    if not bb:
        report.append((e['id'], 'no label'))
        continue
    x0, y0, x1, y1 = bb[0] + 128, bb[1] + 98, bb[2] + 128, bb[3] + 98
    cx = (x0 + x1) // 2
    # allow wider area for Korean
    half = max((x1 - x0) // 2 + 3, 26)
    bx0 = max(100, cx - half); bx1 = min(192, cx + half)
    if bx1 - bx0 < 2 * half:
        if bx0 == 100: bx1 = min(192, bx0 + 2 * half)
        else: bx0 = max(100, bx1 - 2 * half)
    spec[str(e['id'])] = [
        {'box': [max(128, x0 - 1), y0, min(192, x1 + 1), y1], 'clear': 'alpha'},
        {'box': [bx0, y0, bx1, y1], 'clear': 'none', 'text': ko, 'font': 'eHv', 'size': 14,
         'fill': '#ffffff', 'stroke': [1.6, '#000000']}]
json.dump(spec, open('work/tex/spec_names.json', 'w', encoding='utf8'), ensure_ascii=False, indent=0)
print(len(spec), report)
