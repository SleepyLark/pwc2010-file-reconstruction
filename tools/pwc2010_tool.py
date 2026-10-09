#!/usr/bin/env python3
"""
pwc2010_tool.py - helper for analysing the "PWC2010 Rule Check Tool" (title 0003000434534e41).

Everything here is derived from static analysis of the decrypted TWL image (00000000.app).
Each constant carries the address it came from. "FACT" = read directly from code/data,
"INFERENCE" = interpretation that still needs a hardware test.

Usage:
  python3 pwc2010_tool.py selftest   00000000.app
  python3 pwc2010_tool.py extract    00000000.app  rule_template.prd
  python3 pwc2010_tool.py inspect    rule_template.prd [species_no ...]
  python3 pwc2010_tool.py make-cfg   regulation.cfg  [--party] [--box] [--livematch] [--carts IRBO,IRAO,...]
  python3 pwc2010_tool.py make-reg   regulation.bin  [--min-count N] [--level-mode 0|1|2 --level N]
                                     [--total-level N] [--allow-dup-species] [--allow-dup-items]
                                     [--ban-species 150,151] [--ban-items 1,2]
"""
import argparse, struct, sys

ARM9_ROM_OFF, ARM9_LOAD = 0x4000, 0x2004000         # FACT: NTR header 0x20 / 0x28
# per-application constants, keyed by DSi title ID (header 0x230). Only the addresses differ between the two builds.
APPS = {
    "0003000434534e41": dict(name="PWC2010 Rule Check Tool (BW)",  arm9_size=0x108BE0, rule_buf=0x0203BC4C),
    "000300044b394841": dict(name="PokemonBW2 Rule Check Tool",    arm9_size=0x108E60, rule_buf=0x0203BECC),
}
CURRENT = {}                                         # filled by load_arm9()

# --- rule.prd (FACT: the loader memcpy's the whole file into this static buffer) -----------
RULE_BUF_ADDR = 0x0203BC4C                          # slot 0 (compiled-in); slot 1 = +RULE_SIZE; overwritten per app in load_arm9()
RULE_SIZE     = 0x5E77C                             # FACT: slot stride in 0x0200B250/0x0200B320
RULE_HDR      = 0x50                                # FACT: record(1) = base + 1*0x244 - 0x1F4; also holds the item whitelist bitmap
RULE_REC      = 0x244                               # FACT: 'mov r0,#0x244; mul' at 0x0200B4B4 / 0x0200B294
RULE_NREC     = (RULE_SIZE - RULE_HDR) // RULE_REC  # = 667, remainder 0 (verified in selftest)

# --- regulation.cfg: cartridge gate (FACT: emulated routine at 0x02008998 in both builds) ---
# game code (ROM header +0x0C, read from 0x02FFFA80) -> cfg index, or None = always allowed
CART_GATE = {
    "IRBO": 5, "IRAO": 5, "IRBJ": 4, "IRAJ": 4, "IRBF": 6, "IRAF": 6, "IRBI": 7, "IRAI": 7,
    "IRBS": 8, "IRAS": 8, "IRBD": 9, "IRAD": 9, "IRBK": 10, "IRAK": 10,
    "IRBE": None, "IRAE": None, "IRBP": None, "IRAP": None,
}
# BW2 build: identical routine, game codes IRD*/IRE* (verified by emulating 0x02008998 over every IRxx code)
CART_GATE.update({"IRDO": 5, "IREO": 5, "IRDJ": 4, "IREJ": 4, "IRDF": 6, "IREF": 6, "IRDI": 7, "IREI": 7,
                  "IRDS": 8, "IRES": 8, "IRDD": 9, "IRED": 9, "IRDK": 10, "IREK": 10,
                  "IRDE": None, "IREE": None, "IRDP": None, "IREP": None})

def load_arm9(path):
    d = open(path, "rb").read()
    global RULE_BUF_ADDR
    off, entry, load, size = struct.unpack_from("<4I", d, 0x20)
    tid = d[0x230:0x238][::-1].hex()
    if tid not in APPS: sys.exit(f"unknown title ID {tid}; expected one of {list(APPS)}")
    app = APPS[tid]
    if (off, load, size) != (ARM9_ROM_OFF, ARM9_LOAD, app["arm9_size"]):
        sys.exit(f"unexpected ARM9 header {off:#x} {load:#x} {size:#x} for {app['name']}")
    RULE_BUF_ADDR = app["rule_buf"]; CURRENT.update(app)
    print(f"[{app['name']}] rule table buffer at {RULE_BUF_ADDR:#010x}")
    return d[off:off + size]

def rule_slot0(arm9):
    o = RULE_BUF_ADDR - ARM9_LOAD
    return arm9[o:o + RULE_SIZE]

def cmd_selftest(a):
    arm9 = load_arm9(a.app)
    ok = True
    def chk(name, cond):
        nonlocal ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name)
    for s in (b"sdmc:regulation.cfg", b"sdmc:regulation.bin", b"sdmc:rule.prd"):
        chk(f"string present: {s.decode()}", s in arm9)
    chk("RULE_SIZE == RULE_HDR + 667*0x244", RULE_HDR + 667 * RULE_REC == RULE_SIZE and RULE_NREC == 667)
    s0 = rule_slot0(arm9); s1 = arm9[RULE_BUF_ADDR - ARM9_LOAD + RULE_SIZE:][:RULE_SIZE]
    chk("slot 0 is populated (>10k non-zero bytes)", sum(1 for b in s0 if b) > 10000)
    chk("slot 1 is all zero in the file", not any(s1))
    mvcount = lambda sp: sum(1 for b in s0[RULE_HDR+(sp-1)*RULE_REC+0x14:RULE_HDR+sp*RULE_REC] if b)
    chk("Caterpie(10) has far fewer move bytes than Butterfree(12)", mvcount(10) < 10 < 50 < mvcount(12))
    rec = lambda n: s0[RULE_HDR+(n-1)*RULE_REC:RULE_HDR+n*RULE_REC]
    chk("Bulbasaur/Ivysaur move areas identical", rec(1)[0x14:] == rec(2)[0x14:])
    chk("record+2 is 1 (Bulbasaur), 16 (Ivysaur), 32 (Venusaur) -> looks like min legal level (INFERENCE)",
        (rec(1)[2], rec(2)[2], rec(3)[2]) == (1, 16, 32))
    print("ALL PASS" if ok else "SOME CHECKS FAILED"); sys.exit(0 if ok else 1)

def cmd_extract(a):
    data = rule_slot0(load_arm9(a.app)); open(a.out, "wb").write(data)
    print(f"wrote {a.out}: {len(data)} bytes (compiled-in slot-0 table; see caveats in report)")

def cmd_inspect(a):
    d = open(a.prd, "rb").read()
    print(f"size={len(d)} (expected {RULE_SIZE}) {'OK' if len(d)==RULE_SIZE else 'MISMATCH'}")
    bm = d[:RULE_HDR]
    clear = [n for n in range(1, RULE_HDR*8+1) if not (bm[(n-1)>>3] >> ((n-1)&7)) & 1]
    print(f"held-item whitelist (0x00-0x4F): {len(clear)} items NOT allowed (bit = itemID-1); first few item IDs: {clear[:12]}")
    for s in (a.species or [1, 10, 12, 150, 151, 494]):
        if not 1 <= s <= RULE_NREC: print(f"species {s}: out of range 1..{RULE_NREC}"); continue
        r = d[RULE_HDR+(s-1)*RULE_REC:RULE_HDR+s*RULE_REC]
        fl, w2, w4 = struct.unpack_from("<HHH", r, 0)
        w2, mxform = r[2], struct.unpack_from('<b', r, 3)[0]
        nz = sum(1 for b in r[0x14:] if b)
        print(f"species {s:3d}: flags={fl:#06x} min_level={w2} max_form={mxform} first_allowed_location={w4:#06x} move-bytes-set={nz}")

def cmd_make_cfg(a):
    cfg = bytearray(13)                              # highest index read by code is 0x0C
    cfg[0] = 1 if a.party else 0                     # FACT: must be exactly 1 (cmp #1 @0x02006560)
    cfg[1] = 1 if a.box else 0                       # FACT: must be exactly 1 (cmp #1 @0x020054E0)
    cfg[0xC] = 1 if a.livematch else 0               # FACT: any non-zero (cmp #0 @0x020077D4)
    for code in (a.carts.split(",") if a.carts else []):
        idx = CART_GATE[code.strip().upper()]
        if idx is not None: cfg[idx] = 1
    open(a.out, "wb").write(cfg); print(f"wrote {a.out}: {cfg.hex(' ')}")

def bitmap(ids, nbytes):
    b = bytearray(nbytes)
    for i in ids: b[i >> 3] |= 1 << (i & 7)
    return b

def cmd_make_reg(a):
    reg = bytearray(0xB4)                            # 0x64 + 80 bytes item bitmap (my sizing, INFERENCE)
    reg[0x0A] = a.min_count                          # FACT: 0x0200A844: ok if count >= byte
    reg[0x0C] = a.level; reg[0x0D] = a.level_mode    # FACT: 0x0200A858: mode 0 none, 1 level>=x, 2 level<=x
    struct.pack_into("<H", reg, 0x0E, a.total_level) # FACT: 0x0200A8B0: 0 = unlimited, else sum(levels)<=x
    reg[0x10] = 1 if a.allow_dup_species else 0      # FACT: 0x0200A8D0: non-zero skips duplicate-species test
    reg[0x11] = 1 if a.allow_dup_items else 0        # FACT: 0x0200A8D8: non-zero skips duplicate-item test
    sp = [int(x) for x in a.ban_species.split(",") if x]; it = [int(x) for x in a.ban_items.split(",") if x]
    reg[0x12:0x64] = bitmap(sp, 0x52)                # FACT: 0x0200A8E0 tests bit <species> -> code 500
    reg[0x64:0xB4] = bitmap(it, 0x50)                # FACT: 0x0200A908 tests bit <item>    -> code 501
    open(a.out, "wb").write(reg); print(f"wrote {a.out}: {len(reg)} bytes")

def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="c", required=True)
    s = sub.add_parser("selftest"); s.add_argument("app"); s.set_defaults(f=cmd_selftest)
    s = sub.add_parser("extract"); s.add_argument("app"); s.add_argument("out"); s.set_defaults(f=cmd_extract)
    s = sub.add_parser("inspect"); s.add_argument("prd"); s.add_argument("species", nargs="*", type=int); s.set_defaults(f=cmd_inspect)
    s = sub.add_parser("make-cfg"); s.add_argument("out")
    for f in ("--party", "--box", "--livematch"): s.add_argument(f, action="store_true")
    s.add_argument("--carts", default=""); s.set_defaults(f=cmd_make_cfg)
    s = sub.add_parser("make-reg"); s.add_argument("out")
    s.add_argument("--min-count", type=int, default=0); s.add_argument("--level", type=int, default=0)
    s.add_argument("--level-mode", type=int, default=0, choices=(0, 1, 2)); s.add_argument("--total-level", type=int, default=0)
    s.add_argument("--allow-dup-species", action="store_true"); s.add_argument("--allow-dup-items", action="store_true")
    s.add_argument("--ban-species", default=""); s.add_argument("--ban-items", default=""); s.set_defaults(f=cmd_make_reg)
    a = p.parse_args(); a.f(a)

if __name__ == "__main__":
    main()
