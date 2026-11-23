import json,os,re
R='work/text'
a=json.load(open(R+'/strings.json',encoding='utf-8'))
def cat(n,o):
    f=int(o['id'].split(':')[0])
    if f==79: return 'g2_moves'
    if f==87: return 'credits'
    if f in (7,) or 19<=f<=73: return 'g3_names'
    if f!=1: return 'misc'
    if 6072<=n<7155: return 'g1_players'
    if 4905<=n<6072: return 'g2_moves'
    if 985<=n<1154 or 1673<=n<1733 or 2813<=n<3010 or 4006<=n<4173 or 7155<=n<7213: return 'g3_names'
    return 'main'
seen={};groups={}
for n,o in enumerate(a):
    s=o['src']
    if s.startswith('@'): continue
    if s in seen: continue
    c=cat(n,o); seen[s]=c
    groups.setdefault(c,[]).append({'k':len(seen)-1,'src':s})
os.makedirs(R+'/in',exist_ok=True);os.makedirs(R+'/out',exist_ok=True)
allu=[]
for c,l in groups.items():
    print(c,len(l),sum(len(x['src']) for x in l))
# split main and misc into chunks
def dump(name,l):
    json.dump([{'k':x['k'],'src':x['src']} for x in l],open(R+'/in/%s.json'%name,'w',encoding='utf-8'),ensure_ascii=False,indent=0)
for c in ('g1_players','g2_moves','g3_names','credits'):
    dump(c,groups[c])
rest=groups['main']+groups.get('misc',[])
N=8;sz=(len(rest)+N-1)//N
for i in range(N): dump('m%d'%i,rest[i*sz:(i+1)*sz]); print('m%d'%i,len(rest[i*sz:(i+1)*sz]),sum(len(x['src']) for x in rest[i*sz:(i+1)*sz]))
json.dump(seen,open(R+'/src_keys.json','w',encoding='utf-8'),ensure_ascii=False)
