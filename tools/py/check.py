"""Validate translations: python check.py <name>   (reads work/text/in/<name>.json and work/text/out/<name>.json)
out json format: {"<k>": "<korean>", ...}
"""
import sys, json, re, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CODE = re.compile(r'#(?:[A-Za-z]{1,2}-?\d*#?=?|=)|%-?\d*[sd]')


def codes(s):
    out = []
    for m in CODE.finditer(s):
        c = m.group()
        if c.startswith('#R') and not re.match(r'#R[mxez]-?\d', c):
            continue
        out.append(c)
    return sorted(out)


def width(line):
    line = CODE.sub('', line)
    w = 0
    for ch in line:
        w += 1 if ord(ch) < 0x80 or 0xFF61 <= ord(ch) <= 0xFF9F else 2
    return w


def lines(s):
    return re.split(r'\n|#n', s)


def ks_ok(ch):
    if '가' <= ch <= '힣':
        try:
            ch.encode('euc-kr')
            return True
        except UnicodeEncodeError:
            return False
    return True


def sjis_ok(ch):
    if '가' <= ch <= '힣':
        return True
    try:
        ch.encode('cp932')
        return True
    except UnicodeEncodeError:
        return False


def check(src, ko):
    errs = []
    if codes(src) != codes(ko):
        errs.append('control codes differ: src=%s ko=%s' % (codes(src), codes(ko)))
    bad = []
    if bad:
        errs.append('hangul not in KS X 1001 (use other word): %s' % ''.join(bad))
    bad = [c for c in ko if not sjis_ok(c)]
    if bad:
        errs.append('character not available in font: %s' % ''.join(bad))
    if re.search(r'[぀-ヺ一-鿿]', ko):
        errs.append('japanese kana/kanji remain')
    sl, kl = lines(src), lines(ko)
    if len(kl) > len(sl):
        errs.append('more lines than source (%d>%d)' % (len(kl), len(sl)))
    mw = max(width(l) for l in sl)
    for l in kl:
        if width(l) > max(mw, 4):
            errs.append('line too wide %d > %d: %s' % (width(l), mw, CODE.sub('', l)))
    return errs


def main(name):
    src = json.load(open(os.path.join(ROOT, 'work/text/in/%s.json' % name), encoding='utf-8'))
    out = json.load(open(os.path.join(ROOT, 'work/text/out/%s.json' % name), encoding='utf-8'))
    n = 0
    missing = 0
    for e in src:
        k = str(e['k'])
        if k not in out:
            missing += 1
            continue
        errs = check(e['src'], out[k])
        if errs:
            n += 1
            print('[%s] %s\n   -> %s\n   ! %s' % (k, e['src'].replace('\n', '\\n'), out[k].replace('\n', '\\n'), ' | '.join(errs)))
    print('TOTAL', len(src), 'missing', missing, 'with errors', n)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main(sys.argv[1])
