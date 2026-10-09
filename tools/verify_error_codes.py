#!/usr/bin/env python3
"""
verify_error_codes.py - trigger each error code in the REAL PokemonBW2 Rule Check Tool checker (emulated) and report.
  python3 verify_error_codes.py APP.app CSV_DIR rule.prd [--out verification.csv]
Mode 0 is the only mode the BW2 tool passes to the checker (both the Battle Box and Party passes).
"""
import sys, os, struct, argparse, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, pk5, emu
H, R = 0x50, 0x244
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("app"); ap.add_argument("csv"); ap.add_argument("prd"); ap.add_argument("--out", default="verification.csv"); a = ap.parse_args()
    raw = open(a.app, "rb").read(); assert raw[0x230:0x238][::-1].hex() == "000300044b394841", "need BW2 tool .app"
    off, _, _, size = struct.unpack_from("<4I", raw, 0x20); open("/tmp/_ec_arm9.bin", "wb").write(raw[off:off+size])
    T = emu.Tool("/tmp/_ec_arm9.bin", "bw2"); prd = open(a.prd, "rb").read(); T.put(0x203BECC, prd)
    sp = pd.read_csv(f"{a.csv}/pokemon_species.csv"); xp = pd.read_csv(f"{a.csv}/experience.csv"); ab = pd.read_csv(f"{a.csv}/pokemon_abilities.csv")
    mv = pd.read_csv(f"{a.csv}/moves.csv").set_index("identifier").id
    x100 = {int(r.growth_rate_id): int(r.experience) for r in xp[xp.level == 100].itertuples()}; gr = dict(zip(sp.id, sp.growth_rate_id))
    abil = {}
    for p, g in ab[ab.pokemon_id <= 649].groupby("pokemon_id"):
        g = g.sort_values("slot"); abil[int(p)] = (int(g[g.is_hidden == 0].iloc[0].ability_id), int(g[g.is_hidden == 1].iloc[0].ability_id) if (g.is_hidden == 1).any() else None)
    flags = lambda s: int.from_bytes(prd[H+(s-1)*R:H+(s-1)*R+2], "little"); byte = lambda s, m: prd[H+(s-1)*R+0x14+m-1]
    buf = 0x10001000
    def mk(ref, **kw):
        species = kw.pop("species", ref)          # lookups (exp/ability/moves) use the reference species; the record gets `species`
        d = dict(origin=22, met_loc=10, ball=4, lang=2, species=species, exp=x100[gr[ref]], ability=abil[ref][0], moves=(0, 0, 0, 0), pp=(0,)*4)
        if "moves" not in kw:
            leg = [m for m in range(1, 560) if byte(ref, m) & 1 and not byte(ref, m) & 0xD4]; d["moves"] = (leg[0], 0, 0, 0); d["pp"] = (5, 0, 0, 0)
        d.update(kw); return pk5.build(**d)
    def run(b, mode=0): T.put(buf, b); return T.call(0x200C418, mode, buf, 0x88, 1)
    rows = []
    def case(code, label, builder, mode=0, note=""):
        got = run(builder, mode); rows.append([code, label, got, "PASS" if got == code else "DIFFERENT", note]); print(f"{'PASS' if got==code else 'DIFF':5s} expect {code:>3} got {got:>4}  {label}  {note}")
    pika = 25; hi = lambda s: abil[s][1]
    case(10, "stored checksum does not match the data", mk(pika, bad_checksum=True))
    case(10, "Bad Egg flag (sanity word bit 2)", mk(pika, bad_egg=True))
    case(20, "species 0", mk(pika, species=0))
    case(22, "shiny Victini (shiny-locked)", mk(494, exp=int(1.25*50**3), ability=32, tid=1000, sid=1000 ^ 0x1234 ^ 0x5678, pid=0x12345678))
    case(23, "Arceus checked in mode 1 (BW2 tool never uses mode 1)", mk(493, exp=x100[gr[493]], ability=121), mode=1, note="semantics only; unreachable in mode 0")
    case(31, "Ivysaur Lv10", mk(2, exp=560, ability=65, moves=(33,0,0,0), pp=(35,0,0,0)))
    case(32, "Pikachu form 5", mk(pika, form=5))
    case(33, "Mew without event flag", mk(151, exp=117360, ability=28, moves=(33,0,0,0), pp=(35,0,0,0)))
    case(50, "ball ID 26", mk(pika, ball=26))
    bs = next(s for s in range(1, 650) if flags(s) & 0x10 and s in abil)
    case(51, f"flag-0x10 species #{bs} in a Great Ball", mk(bs, ball=3))
    case(52, "egg location set + Great Ball (hatched-from-egg path)", mk(pika, ball=3, egg_loc=60002), note="exploratory")
    case(60, "ability ID 0", mk(pika, ability=0))
    case(61, "held item 700 (>625)", mk(pika, item=700))
    # header bitmap = held-item whitelist?
    cleared = [i for i in range(1, 626) if not (prd[(i-1)>>3] >> ((i-1)&7)) & 1][:3]; setb = [i for i in range(1, 626) if (prd[(i-1)>>3] >> ((i-1)&7)) & 1][:3]
    for i in cleared[:2]: case(61, f"held item {i} (header-bitmap bit CLEAR)", mk(pika, item=i), note="whitelist test")
    for i in setb[:2]:
        got = run(mk(pika, item=i)); rows.append([0, f"held item {i} (header-bitmap bit SET)", got, "PASS" if got == 0 else "DIFFERENT", "whitelist test"]); print(f"{'PASS' if got==0 else 'DIFF':5s} expect   0 got {got:>4}  held item {i} (header-bitmap bit SET)")
    if hi(pika): case(62, "Pikachu with Hidden Ability", mk(pika, ability=hi(pika)), note="flag 0x400 on 645 species")
    case(90, "EVs 255 x6", mk(pika, evs=(255,)*6))
    case(120, "move ID 600", mk(pika, moves=(600,0,0,0), pp=(5,0,0,0)))
    case(131, "move slots 1+2 identical", mk(pika, moves=(85,85,0,0), pp=(15,15,0,0)))
    case(132, "move slots 1+3 identical", mk(pika, moves=(98,85,98,0), pp=(30,15,30,0)))
    case(133, "move slots 1+4 identical", mk(pika, moves=(85,98,57,85), pp=(15,30,15,15)))
    case(140, "slot 1 empty", mk(pika, moves=(0,98,0,0), pp=(0,30,0,0)))
    case(141, "gap: slot 2 empty, slot 3 filled", mk(pika, moves=(85,0,98,0), pp=(15,0,30,0)))
    for slot in range(4):
        mvs = [85, 98, 87, 129]; mvs[slot] = 63
        case(150 + slot, f"Hyper Beam in slot {slot+1}", mk(pika, moves=tuple(mvs), pp=(5,)*4))
    # 160/180: pick species/moves from the loaded table so the test follows whatever table is under test
    s160 = next((x for x in range(1, 650) if x in abil and not flags(x) & 0x7FF & ~0x410 and any(byte(x, m) & 0x81 == 0x81 and not byte(x, m) & 0x7e for m in range(1, 560))), None)
    if s160:
        m160 = next(m for m in range(1, 560) if byte(s160, m) & 0x81 == 0x81 and not byte(s160, m) & 0x7e)
        case(160, f"species #{s160} knows older-game-only move #{m160} (byte bit 0x80)", mk(s160, moves=(m160, 0, 0, 0), pp=(5, 0, 0, 0)))
    s180 = next((x for x in range(1, 650) if x in abil and (flags(x) & ~0x400) == 0 and any(byte(x, m) == 2 for m in range(1, 560))), None)
    if s180:
        m180 = next(m for m in range(1, 560) if byte(s180, m) == 2)
        case(180, f"species #{s180} knows egg-only move #{m180}, egg location = 0", mk(s180, moves=(m180, 0, 0, 0), pp=(5, 0, 0, 0)))
    case(190, "Pidgeotto: XD-only move 287 + egg-only move 185, met location 30001 (Poke Transfer)", mk(17, moves=(287, 185, 0, 0), pp=(5, 5, 0, 0), met_loc=30001))
    case(191, "Charmander: distribution-only move 98 + egg-only move 44, met location 30001", mk(4, moves=(98, 44, 0, 0), pp=(5, 5, 0, 0), met_loc=30001))
    sd = next(x for x in range(1, 650) if x in abil and byte(x, 507) & 0x1f and not flags(x) & 0x7FF & ~0x410 and x != 235)
    case(170, f"species #{sd} knows Sky Drop (native check, mode 0)", mk(sd, moves=(507, 0, 0, 0), pp=(5, 0, 0, 0)))
    # party-form level checks (code 30): convert to the 0xDC party record, then force the level
    for lv in (0, 101):
        T.put(buf, mk(pika)); T.call(0x200D070, buf, 0x10004000, lv); got = T.call(0x200B430, 0x10004000, 0)
        rows.append([30, f"party-form record with level {lv}", got, "PASS" if got == 30 else "DIFFERENT", "checker 0x0200B430 called directly"]); print(f"{'PASS' if got==30 else 'DIFF':5s} expect  30 got {got:>4}  party-form record with level {lv}")
    case(200, "nature 40", mk(pika, nature=40))
    case(210, "met location 1 (invalid)", mk(pika, met_loc=1))
    s212 = next(s for s in range(1, 650) if s in abil and int.from_bytes(prd[H+(s-1)*R+4:H+(s-1)*R+6], "little") and not flags(s) & 0x4 and flags(s) & 0x400)
    case(212, f"species #{s212} caught at location not in its allowed list", mk(s212, ability=abil[s212][0]))
    s211 = next(x for x in range(1, 650) if x in abil and flags(x) & 0x20 and not int.from_bytes(prd[H+(x-1)*R+4:H+(x-1)*R+6], "little") and not flags(x) & 0x6)
    case(211, f"species #{s211} (flag 0x20) with egg location set, met location 10", mk(s211, egg_loc=60002))
    pd.DataFrame(rows, columns=["expected_code", "test", "checker_returned", "result", "note"]).to_csv(a.out, index=False)
if __name__ == "__main__": main()
