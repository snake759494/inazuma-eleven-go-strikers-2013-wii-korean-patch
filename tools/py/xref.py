import sys,struct,os
sys.argv_save=sys.argv[1:]; sys.argv=['x']
exec(open(os.path.join(os.path.dirname(__file__),'ppcdis.py'),encoding='utf8').read().split("for name in")[0])
import bisect
fs=sorted((v,n,s) for n,(v,s) in syms.items())
keys=[x[0] for x in fs]
def owner(a):
    i=bisect.bisect_right(keys,a)-1; return fs[i][1] if i>=0 else '?'
text=[s for s in f.iter_segments() if s['p_type']=='PT_LOAD' and s['p_flags']&1]
for t in sys.argv_save:
    tgt=syms[t][0] if t in syms else int(t,16)
    for seg in text:
        d=seg.data();base=seg['p_vaddr']
        for o in range(0,len(d)-3,4):
            w=struct.unpack_from('>I',d,o)[0]
            if (w>>26)==18 and (w&3)==1:
                li=w&0x03FFFFFC
                if li&0x02000000: li-=0x04000000
                if base+o+li==tgt: print(t,hex(base+o),owner(base+o))
