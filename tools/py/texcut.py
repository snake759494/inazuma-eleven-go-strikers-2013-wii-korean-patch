"""Index TEXCUT files in ui.bin: records of 8 int16 (x,y,w,h,flag,?,0x8080,0x8080)."""
import sys, os, struct, json
sys.path.insert(0, os.path.dirname(__file__))
import s13
def parse(d):
    if len(d) < 16 or len(d) % 16: return None
    recs = []
    for k in range(0, len(d), 16):
        x, y, w, h, f, z, a, b = struct.unpack_from('<8h', d, k)
        if a != -32640 or b != -32640 or w <= 0 or h <= 0 or x < 0 or y < 0: return None
        recs.append((x, y, w, h))
    return recs
if __name__ == '__main__':
    a = s13.Archive(os.path.join(s13.ROOT, 'work', 'orig', 'ui.bin'))
    idx = json.load(open(os.path.join(s13.ROOT, 'work', 'tex', 'ui', 'index.json')))
    cuts = {}
    for i in range(a.count):
        if str(i) in idx: continue
        try: d = a.get(i)
        except Exception: continue
        r = parse(d)
        if r: cuts[i] = r
    json.dump(cuts, open(os.path.join(s13.ROOT, 'work', 'tex', 'texcut.json'), 'w'))
    print('texcut files', len(cuts))
