import struct
BP=[0,1,2,3, 0,1,3,2, 0,2,1,3, 0,3,1,2, 0,2,3,1, 0,3,2,1, 1,0,2,3, 1,0,3,2, 2,0,1,3, 3,0,1,2, 2,0,3,1, 3,0,2,1,
    1,2,0,3, 1,3,0,2, 2,1,0,3, 3,1,0,2, 2,3,0,1, 3,2,0,1, 1,2,3,0, 1,3,2,0, 2,3,1,0, 3,2,1,0]
def _crypt(buf,seed):
    out=bytearray(buf)
    for i in range(0,len(out),2):
        seed=(seed*0x41C64E6D+0x6073)&0xffffffff
        w=struct.unpack_from("<H",out,i)[0]^(seed>>16)
        struct.pack_into("<H",out,i,w)
    return out
def utf16(s,n): b=s.encode("utf-16le")[:n*2]; return b.ljust(n*2,b"\xff") if False else (b+b"\xff\xff"+b"\xff\xff"*(n-len(b)//2-1))[:n*2]
def build(species=25,item=0,tid=12345,sid=54321,exp=125000,friend=70,ability=9,lang=2,evs=(0,)*6,
          moves=(85,98,0,0),pp=(15,30,0,0),ivs=(31,)*6,egg=False,form=0,gender=0,nature=0,
          pid=0x12345678,origin=20,met_loc=1,egg_loc=0,ball=4,met_level=5,ot="TEST",nick="TEST",
          ppups=(0,0,0,0),fateful=0,genderless=0,bad_checksum=False,bad_egg=False,corrupt_checksum=False,pokerus=0):
    A=bytearray(32);B=bytearray(32);C=bytearray(32);D=bytearray(32)
    struct.pack_into("<HHHHIBBBB",A,0,species,item,tid,sid,exp,friend,ability,0,lang)
    for i,e in enumerate(evs): A[0x10+i]=e&0xff          # 0x18..0x1D
    for i in range(4): struct.pack_into("<H",B,i*2,moves[i]); B[8+i]=pp[i]; B[12+i]=ppups[i]
    iv=0
    for i,v in enumerate(ivs): iv|=(v&31)<<(5*i)
    if egg: iv|=1<<30
    struct.pack_into("<I",B,16,iv)
    B[0x18]=(fateful&1)|((1 if gender==1 else 0)<<1)|((genderless&1)<<2)|((form&31)<<3)  # 0x40
    B[0x19]=nature                                                                     # 0x41
    C[0:24]=utf16(nick,12); C[0x17]=origin                                             # 0x5F
    D[0:16]=utf16(ot,8)
    struct.pack_into("<HH",D,0x16,egg_loc,met_loc)                                     # 0x7E,0x80
    D[0x1A]=pokerus; D[0x1B]=ball; D[0x1C]=met_level&0x7f                              # 0x82..0x84
    blocks=[bytes(A),bytes(B),bytes(C),bytes(D)]
    body=b"".join(blocks)
    cks=sum(struct.unpack("<64H",body))&0xffff
    sv=((pid>>13)&31)%24
    # stored block at position BP[sv*4+k] holds logical block k (inverse of PKHeX decrypt)
    stored=[None]*4
    for k in range(4): stored[BP[sv*4+k]]=blocks[k]
    sanity=0x0004 if bad_egg else 0                      # u16 @0x04, bit 2 = Bad Egg flag (verified: app returns code 10)
    if bad_checksum: cks^=0xBEEF                          # stored checksum != sum of the data; data is encrypted with the STORED
    enc=_crypt(b"".join(stored),cks)                      # value, so it still decodes cleanly (verified: app returns code 10)
    if corrupt_checksum: cks^=0xBEEF                      # DEPRECATED: scrambles the data; result is unpredictable (garbage codes)
    return struct.pack("<IHH",pid,sanity,cks)+bytes(enc)
