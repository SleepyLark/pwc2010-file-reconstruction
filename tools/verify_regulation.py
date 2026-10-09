#!/usr/bin/env python3
"""
verify_regulation.py - run the BW2 tool's regulation.bin accessor functions in the emulator against a generated file.
  python3 verify_regulation.py APP.app regulation.bin
Accessor addresses (BW2 build): min-count 0x0200A86C, level rule 0x0200A880, total level 0x0200A8D8,
dup-species flag 0x0200A8F8, dup-item flag 0x0200A900, banned-species bitmap 0x0200A908, banned-item bitmap 0x0200A930.
(BW1 build: same functions 0x2C bytes lower.) The init routine turns a failing accessor into codes 500/501/502/600/601/602/603.
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu
app, regf = sys.argv[1], sys.argv[2]
raw = open(app, "rb").read(); assert raw[0x230:0x238][::-1].hex() == "000300044b394841", "need the BW2 tool"
off, _, _, size = struct.unpack_from("<4I", raw, 0x20); open("/tmp/_reg.bin", "wb").write(raw[off:off+size])
T = emu.Tool("/tmp/_reg.bin", "bw2"); reg = open(regf, "rb").read(); T.put(0x10002000, reg); R = 0x10002000
ok = True
def t(label, got, want):
    global ok; good = (bool(got) == bool(want)) if isinstance(want, bool) else got == want; ok &= good
    print(f"{'PASS' if good else 'FAIL'}  {label:58s} -> {got}")
mn, lvl, mode, tot, dsp, dit = reg[0x0A], reg[0x0C], reg[0x0D], struct.unpack_from("<H", reg, 0x0E)[0], reg[0x10], reg[0x11]
print(f"file fields: min_count={mn} level={lvl} level_mode={mode} total_level={tot} allow_dup_species={dsp} allow_dup_items={dit}")
t("min-count accessor(count = min)  -> ok (non-zero)", T.call(0x200A870, R, mn), True)
t("min-count accessor(count = min-1) -> fail (0)", T.call(0x200A870, R, mn - 1), False) if mn else None
if mode == 2:
    t(f"level rule mode 2: level {lvl} allowed", T.call(0x200A884, R, lvl), True); t(f"level rule mode 2: level {lvl+1} rejected", T.call(0x200A884, R, lvl + 1), False)
if mode == 1:
    t(f"level rule mode 1: level {lvl} allowed", T.call(0x200A884, R, lvl), True); t(f"level rule mode 1: level {lvl-1} rejected", T.call(0x200A884, R, lvl - 1), False)
if mode == 0: t("level rule mode 0: any level allowed", T.call(0x200A884, R, 100), True)
if tot: t(f"total level {tot} allowed", T.call(0x200A8DC, R, tot), True); t(f"total level {tot+1} rejected", T.call(0x200A8DC, R, tot + 1), False)
else: t("total level cap 0 = unlimited", T.call(0x200A8DC, R, 600), True)
t("dup-species flag", T.call(0x200A8FC, R), bool(dsp)); t("dup-item flag", T.call(0x200A904, R), bool(dit))
banned = [s for s in range(0, 656) if reg[0x12 + (s >> 3)] >> (s & 7) & 1]
print("banned species bits in file:", banned[:12])
for s in banned[:3]: t(f"species {s} banned bit -> accessor non-zero (code 500)", T.call(0x200A90C, R, s), True)
t("species 25 not banned -> accessor 0", T.call(0x200A90C, R, 25), 25 in banned)
bi = [i for i in range(0, 640) if reg[0x64 + (i >> 3)] >> (i & 7) & 1]
print("banned item bits in file:", bi[:12])
for i in bi[:3]: t(f"item {i} banned bit -> accessor non-zero (code 501)", T.call(0x200A934, R, i), True)
print("ALL PASS" if ok else "FAILURES"); sys.exit(0 if ok else 1)
