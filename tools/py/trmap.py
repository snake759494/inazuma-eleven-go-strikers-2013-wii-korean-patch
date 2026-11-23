import json, glob, os
def load():
    tr = {}
    for p in glob.glob('work/text/in/*.json'):
        n = os.path.basename(p)[:-5]
        op = 'work/text/out/%s.json' % n
        if not os.path.exists(op): continue
        out = json.load(open(op, encoding='utf8'))
        for e in json.load(open(p, encoding='utf8')):
            if str(e['k']) in out: tr[e['src']] = out[str(e['k'])]
    return tr
