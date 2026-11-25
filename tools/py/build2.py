"""In-place build: writes only changed files to work/patch/files and work/patch_sys/main.dol,
keeping archive entry slots and mcb1 block layout identical to the original disc.
"""
import sys, os, json, glob, shutil
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageChops
import s13, textfmt, kor, lzopt, shtx, mkfont
from build import load_tr, enc

ROOT = s13.ROOT
W = os.path.join(ROOT, 'work')
ORIG = os.path.join(W, 'orig')
SRC = os.path.join(W, 'witx', 'files')
PF = os.path.join(W, 'patch', 'files')
PS = os.path.join(W, 'patch_sys')
T = os.path.join(W, 'text')


def fit(a, i, dec, orig_dec=None):
    hdr = not a.is_dat()
    c = s13.lz_compress(dec, header=hdr)
    if len(c) <= a.slot(i):
        return c
    c = lzopt.compress(dec, header=hdr)
    if len(c) <= a.slot(i):
        return c
    if orig_dec is not None and dec[:4] == b'SHTX':
        oi, _ = shtx.decode(orig_dec); ni, _ = shtx.decode(dec)
        oi = oi.convert('RGBA'); ni = ni.convert('RGBA')
        diff = ImageChops.difference(oi, ni).convert('L').point(lambda v: 255 if v else 0)
        for nc in (128, 64, 48, 32, 24, 16):
            q = ni.quantize(colors=nc, method=Image.Quantize.FASTOCTREE).convert('RGBA')
            res = oi.copy(); res.paste(q, (0, 0), diff)
            d2 = bytearray(shtx.encode(res, orig_dec))
            if d2[4:6] == b'FF':
                for k in range(12, len(d2), 4):
                    if d2[k + 3] == 0:
                        d2[k:k + 3] = bytes(3)
            d2 = bytes(d2)
            for fn in (lambda d: s13.lz_compress(d, header=hdr), lambda d: lzopt.compress(d, header=hdr)):
                c = fn(d2)
                if len(c) <= a.slot(i):
                    print('   ui %d fitted with %d colours' % (i, nc))
                    return c
    raise SystemExit('entry %d does not fit: %d > %d' % (i, len(c), a.slot(i)))


def main():
    for d in (PF, PS):
        if os.path.isdir(d):
            shutil.rmtree(d)
    os.makedirs(os.path.join(PF, 'movie')); os.makedirs(PS)
    tr = load_tr()
    remaps = {}
    # ---- dat
    strings = json.load(open(os.path.join(T, 'strings.json'), encoding='utf-8'))
    byf = {}
    for o in strings:
        ko = tr.get(o['src'])
        if ko is None:
            continue
        b = enc(ko)
        if b is None:
            continue
        f, off = o['id'].split(':')
        byf.setdefault(int(f), {})[int(off, 16)] = b
    a = s13.Archive(os.path.join(ORIG, 'dat.bin'))
    for f, new in sorted(byf.items()):
        a.put_raw(f, fit(a, f, textfmt.TextFile(a.get(f)).build(new)))
    remaps[4] = a.save_inplace(os.path.join(PF, 'dat.bin'))
    print('dat entries', len(a.replaced))
    # ---- ui
    u = s13.Archive(os.path.join(ORIG, 'ui.bin'))
    os.makedirs(os.path.join(W, 'ui'), exist_ok=True)
    for fi in (0, 1, 2):
        p = os.path.join(W, 'ui', '%04d.kor' % fi)
        if not os.path.exists(p):
            open(p, 'wb').write(mkfont.build(fi, u.get(fi)))
        u.put_raw(fi, fit(u, fi, open(p, 'rb').read()))
    for p in sorted(glob.glob(os.path.join(W, 'tex', 'out', '*.shtx'))):
        i = int(os.path.basename(p)[:4])
        u.put_raw(i, fit(u, i, open(p, 'rb').read(), u.get(i)))
    remaps[3] = u.save_inplace(os.path.join(PF, 'ui.bin'))
    print('ui entries', len(u.replaced))
    # ---- grp (main menu icons)
    news = glob.glob(os.path.join(W, 'tex', 'mm', '*.new')) + glob.glob(os.path.join(W, 'tex', 'grp', '*.new'))
    if news:
        g = s13.Archive(os.path.join(ORIG, 'grp.bin'))
        for p in news:
            gi = int(os.path.basename(p)[:-4])
            g.put_raw(gi, fit(g, gi, open(p, 'rb').read()))
        remaps[0] = g.save_inplace(os.path.join(PF, 'grp.bin'))
    # ---- special-move captions (scn / scn_sh)
    for ai, an in ((1, 'scn'), (2, 'scn_sh')):
        outs = sorted(glob.glob(os.path.join(W, 'cap', 'out', an + '_*.bin')))
        outs = [p for p in outs if os.path.basename(p)[len(an) + 1:-4].isdigit()]
        if not outs:
            continue
        a2 = s13.Archive(os.path.join(ORIG, an + '.bin'))
        for p in outs:
            i = int(os.path.basename(p)[len(an) + 1:-4])
            a2.put_raw(i, fit(a2, i, open(p, 'rb').read()))
        remaps[ai] = a2.save_inplace(os.path.join(PF, an + '.bin'))
        print(an, 'captions', len(outs))
    # ---- strap (not in mcb1; may grow and be relocated)
    st = s13.Archive(os.path.join(ORIG, 'strap.bin'))
    for i, t in ((0, 16), (1, 17)):
        p = os.path.join(W, 'tex', 'out', '%04d.shtx' % t)
        if os.path.exists(p):
            st.put(i, open(p, 'rb').read())
    st.save(os.path.join(PF, 'strap.bin'))
    # ---- mcb
    hits = s13.rebuild_bln_inplace(ORIG, PF, remaps)
    os.remove(os.path.join(PF, 'mcb0.bln'))
    print('mcb1 copies replaced', hits)
    # ---- movies
    for f in glob.glob(os.path.join(W, 'movie_ko', '*.mo')):
        shutil.copy(f, os.path.join(PF, 'movie', os.path.basename(f)))
    # ---- dol
    d = bytearray(open(os.path.join(ORIG, 'main.dol'), 'rb').read())
    for e in json.load(open(os.path.join(T, 'dol.json'), encoding='utf-8')):
        off = int(e['off'], 16)
        ob = e['jp'].encode('cp932')
        assert d[off:off + len(ob)] == ob, e
        nb = kor.encode(e['ko'])
        assert len(nb) <= len(ob), e
        d[off:off + len(ob)] = nb + bytes(len(ob) - len(nb))
    open(os.path.join(PS, 'main.dol'), 'wb').write(d)
    for p in sorted(glob.glob(os.path.join(PF, '**', '*'), recursive=True)):
        if os.path.isfile(p):
            q = os.path.join(SRC, os.path.relpath(p, PF))
            print('  %-40s %12d -> %12d' % (os.path.relpath(p, PF), os.path.getsize(q), os.path.getsize(p)))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
