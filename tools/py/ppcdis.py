import sys,capstone
from elftools.elf.elffile import ELFFile
E=r'D:/wii/이나즈마일레븐Go_스트라이커2013/work/witx/files/InazumaWii.elf'
f=ELFFile(open(E,'rb'))
syms={};addr2={}
for s in f.get_section_by_name('.symtab').iter_symbols():
    if s['st_value']: syms[s.name]=(s['st_value'],s['st_size']); addr2.setdefault(s['st_value'],s.name)
def read(va,n):
    for seg in f.iter_segments():
        if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=va<seg['p_vaddr']+seg['p_filesz']:
            return seg.data()[va-seg['p_vaddr']:va-seg['p_vaddr']+n]
md=capstone.Cs(capstone.CS_ARCH_PPC,capstone.CS_MODE_32|capstone.CS_MODE_BIG_ENDIAN|getattr(capstone,"CS_MODE_PS",0))
md.skipdata=True
for name in sys.argv[1:]:
    va,sz=syms[name]; print('==',name,hex(va))
    for i in md.disasm(read(va,sz),va):
        c=''
        if i.mnemonic in('bl','b') :
            t=int(i.op_str,16); c=addr2.get(t,'')
        print(hex(i.address),i.mnemonic,i.op_str,c)
