"""Extract all translatable strings to work/text/strings.json"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(__file__))
import textfmt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILES = [1, 3, 5, 7, 19, 25, 33, 35, 37, 39, 49, 51, 55, 57, 59, 61, 63, 65, 71, 73, 79, 87, 113]
# also scan all odd files for team names etc
JP = re.compile(r'[぀-ヿ一-鿿！-～]')

RUBY = re.compile(r'#R(?![mxe]-?\d)(?:#=)?((?:#[a-zA-Z]+-?\d*#?=?|[^()#])+?)\(([^()]*)\)')


def strip_ruby(s):
    def rep(m):
        base = m.group(1)
        base = re.sub(r'#x-?\d+', '', base)
        return base
    return RUBY.sub(rep, s)


def main():
    out = []
    for i in range(1, 130, 2):
        p = os.path.join(ROOT, 'work', 'dat', '%03d.bin' % i)
        d = open(p, 'rb').read()
        try:
            t = textfmt.TextFile(d)
        except Exception:
            continue
        if i == 117:
            continue  # NG word list
        for k in sorted(t.targets):
            if k >= t.end:
                continue
            try:
                e = d.index(b'\0', k)
                s = d[k:e].decode('cp932')
            except Exception:
                continue
            if not JP.search(s):
                continue
            if any(ord(c) < 0x20 and c not in '\n' for c in s):
                continue
            out.append({'id': '%d:%x' % (i, k), 'jp': s, 'src': strip_ruby(s)})
    os.makedirs(os.path.join(ROOT, 'work', 'text'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'work', 'text', 'strings.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    uniq = {}
    for o in out:
        uniq.setdefault(o['src'], []).append(o['id'])
    print('strings', len(out), 'unique', len(uniq), 'chars', sum(len(k) for k in uniq))
    from collections import Counter
    print(Counter(o['id'].split(':')[0] for o in out))


if __name__ == '__main__':
    main()
