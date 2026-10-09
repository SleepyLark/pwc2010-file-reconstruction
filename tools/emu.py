import struct
from unicorn import *
from unicorn.arm_const import *
class Tool:
    def __init__(self,arm9path,fn):
        a9=open(arm9path,"rb").read()
        self.fn=fn
        self.mu=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        self.mu.mem_map(0x2000000,0x400000); self.mu.mem_write(0x2004000,a9)
        self.mu.mem_map(0x10000000,0x10000)
        self.mu.hook_add(UC_HOOK_MEM_READ_UNMAPPED|UC_HOOK_MEM_WRITE_UNMAPPED|UC_HOOK_MEM_FETCH_UNMAPPED,self._unm)
        self.snap=None
    def _unm(self,uc,acc,addr,size,val,ud):
        pg=addr&~0xfff
        try: uc.mem_map(pg,0x1000)
        except UcError: pass
        return True
    def call(self,addr,*args,count=3_000_000):
        mu=self.mu
        for i,v in enumerate(args[:4]): mu.reg_write(UC_ARM_REG_R0+i,v)
        mu.reg_write(UC_ARM_REG_SP,0x2380000); mu.reg_write(UC_ARM_REG_LR,0x10008000)
        mu.mem_write(0x10008000,b"\x00\x00\xa0\xe1"*4)  # nops sentinel
        mu.emu_start(addr,0x10008000,count=count)
        r=mu.reg_read(UC_ARM_REG_R0); return r-(1<<32) if r&0x80000000 else r
    def put(self,addr,b): self.mu.mem_write(addr,b)
