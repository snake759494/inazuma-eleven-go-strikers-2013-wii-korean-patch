"""Build Korean patched files into work/witx and produce ISO.
usage: python build.py [--noiso]
"""
import sys, os, json, glob, re, shutil, subprocess, struct
sys.path.insert(0, os.path.dirname(__file__))
import s13, textfmt, kor, extract

ROOT = s13.ROOT
W = os.path.join(ROOT, 'work')
ORIG = os.path.join(W, 'orig')
OUTF = os.path.join(W, 'witx', 'files')
T = os.path.join(W, 'text')


def load_tr():
    tr = {}
    for p in glob.glob(os.path.join(T, 'in', '*.json')):
        name = os.path.basename(p)[:-5]
        op = os.path.join(T, 'out', name + '.json')
        if not os.path.exists(op):
            continue
        src = json.load(open(p, encoding='utf-8'))
        out = json.load(open(op, encoding='utf-8'))
        for e in src:
            k = str(e['k'])
            if k in out and out[k].strip() != '' or (k in out and e['src'].strip() == ''):
                tr[e['src']] = out[k]
    # manual overrides
    mp = os.path.join(T, 'manual.json')
    if os.path.exists(mp):
        tr.update(json.load(open(mp, encoding='utf-8')))
    return tr


def enc(s):
    try:
        return kor.encode(s)
    except UnicodeEncodeError as e:
        bad = ''.join(c for c in s if c not in kor.IDX and not _cp(c))
        print('  ENC FAIL', repr(s[:40]), bad)
        return None


def _cp(c):
    try:
        c.encode('cp932'); return True
    except UnicodeEncodeError:
        return False


def build_dat(tr):
    strings = json.load(open(os.path.join(T, 'strings.json'), encoding='utf-8'))
    byfile = {}
    miss = 0
    for o in strings:
        ko = tr.get(o['src'])
        if ko is None:
            if not o['src'].startswith('@'):
                miss += 1
            continue
        b = enc(ko)
        if b is None:
            continue
        f, off = o['id'].split(':')
        byfile.setdefault(int(f), {})[int(off, 16)] = b
    print('untranslated strings:', miss)
    a = s13.Archive(os.path.join(ORIG, 'dat.bin'))
    only = os.environ.get('ONLY')
    for f, new in sorted(byfile.items()):
        if os.environ.get('NOTEXT') or (only and str(f) not in only.split(',')):
            continue
        d = a.get(f)
        t = textfmt.TextFile(d)
        nd = t.build(new)
        a.put(f, nd)
        print('  dat %d: %d strings, %d -> %d bytes' % (f, len(new), len(d), len(nd)))
    return a.save(os.path.join(OUTF, 'dat.bin'))


def build_ui():
    import mkfont
    a = s13.Archive(os.path.join(ORIG, 'ui.bin'))
    for fi in (() if os.environ.get('NOFONT') else (0, 1, 2)):
        p = os.path.join(W, 'ui', '%04d.kor' % fi)
        if not os.path.exists(p):
            open(p, 'wb').write(mkfont.build(fi, a.get(fi)))
        a.put(fi, open(p, 'rb').read())
    # texture replacements: work/tex/out/<index>.bin (decompressed SHTX)
    for p in sorted(glob.glob(os.path.join(W, 'tex', 'out', '*.shtx'))):
        i = int(os.path.basename(p).split('.')[0])
        a.put(i, open(p, 'rb').read())
    return a.save(os.path.join(OUTF, 'ui.bin'))


def build_dol():
    p = os.path.join(T, 'dol.json')
    d = bytearray(open(os.path.join(ORIG, 'main.dol'), 'rb').read())
    if os.path.exists(p):
        for e in json.load(open(p, encoding='utf-8')):
            off = int(e['off'], 16)
            ob = e['jp'].encode('cp932')
            assert d[off:off + len(ob)] == ob, e
            nb = kor.encode(e['ko'])
            if len(nb) > len(ob):
                print('  DOL too long', e['ko']); continue
            d[off:off + len(ob)] = nb + b'\0' * (len(ob) - len(nb))
    open(os.path.join(W, 'witx', 'sys', 'main.dol'), 'wb').write(d)


def main():
    tr = load_tr()
    print('translations loaded', len(tr))
    remaps = {4: build_dat(tr), 3: build_ui()}
    st = s13.Archive(os.path.join(ORIG, 'strap.bin'))
    for i, t in ((0, 16), (1, 17)):
        p = os.path.join(W, 'tex', 'out', '%04d.shtx' % t)
        if os.path.exists(p):
            st.put(i, open(p, 'rb').read())
    remaps[5] = st.save(os.path.join(OUTF, 'strap.bin'))
    mm = os.path.join(W, 'tex', 'mm', '4686.new')
    if os.path.exists(mm):
        gr = s13.Archive(os.path.join(ORIG, 'grp.bin'))
        gr.put(4686, open(mm, 'rb').read())
        remaps[0] = gr.save(os.path.join(OUTF, 'grp.bin'))
    # grp/scn/... unchanged: identity remap
    for f in glob.glob(os.path.join(W, 'movie_ko', '*.mo')):
        shutil.copy(f, os.path.join(OUTF, 'movie', os.path.basename(f)))
    hits = s13.rebuild_bln(ORIG, OUTF, remaps)
    print('bln copies updated:', hits)
    build_dol()
    if '--noiso' not in sys.argv:
        iso = os.path.join(W, 'patched.iso')
        if os.path.exists(iso):
            os.remove(iso)
        subprocess.check_call([os.path.join(ROOT, 'tools', 'wit', 'wit.exe'), 'copy', 'witx', 'patched.iso', '--iso', '-q'], cwd=W)
        print('ISO built', os.path.getsize(iso))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
