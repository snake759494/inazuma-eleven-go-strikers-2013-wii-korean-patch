import sys, json, glob, os, re
C = re.compile(r'#(?:[A-Za-z]{1,2}-?[0-9]*|=)')
def codes(s):
    return sorted(m.group() for m in C.finditer(s))
tot = 0
for p in glob.glob('work/text/in/*.json'):
    n = os.path.basename(p)[:-5]; op = 'work/text/out/%s.json' % n
    out = json.load(open(op, encoding='utf8')); ch = 0
    for e in json.load(open(p, encoding='utf8')):
        k = str(e['k']); ko = out.get(k)
        if ko is None or codes(e['src']) == codes(ko):
            continue
        new = ko
        for m in C.finditer(e['src']):
            c = m.group(); after = e['src'][m.end():m.end() + 1]
            if after and '０' <= after <= '９':
                i = new.find(c)
                while i >= 0:
                    j = i + len(c)
                    while j < len(new) and '0' <= new[j] <= '9':
                        new = new[:j] + chr(ord(new[j]) + 0xFEE0) + new[j + 1:]; j += 1
                    i = new.find(c, j)
        if codes(e['src']) == codes(new):
            out[k] = new; ch += 1
        else:
            print('UNFIXED', n, k, repr(e['src'][:50]), repr(ko[:50]))
    if ch:
        json.dump(out, open(op, 'w', encoding='utf8'), ensure_ascii=False, indent=0); print(n, 'fixed', ch); tot += ch
print('total', tot)
