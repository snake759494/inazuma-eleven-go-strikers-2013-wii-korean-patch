import struct,sys
sys.path.insert(0,__import__('os').path.dirname(__file__))
import s13
W,H=24,25
def load(d):
    n=struct.unpack_from('<I',d)[0];offs=list(struct.unpack_from('<%dI'%n,d,4))
    so=sorted(set(offs))+[len(d)]
    nxt={so[i]:so[i+1] for i in range(len(so)-1)}
    return [d[o:nxt[o]] for o in offs]
def glyph_px(raw):
    g=s13.lz_decompress(raw)
    px=[]
    for i in range(W*H):
        b=g[i//2] if i//2<len(g) else 0
        v=(b&0xF) if i%2==0 else (b>>4)
        px.append(v)
    return px
def kuten(ch):
    b=ch.encode('cp932');
    if len(b)==1: return None
    s1,s2=b
    row=(s1-0x81)*2 if s1<0xA0 else (s1-0xC1)*2
    if s2>=0x9F: row+=1; col=s2-0x9F
    else: col=s2-0x40 if s2<0x80 else s2-0x41
    return row*94+col
