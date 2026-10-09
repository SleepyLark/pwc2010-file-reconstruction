#!/usr/bin/env python3
"""
validate_rule_prd.py - run candidate rule.prd tables through the REAL BW2 checker (ARM9 0x0200C418) in an emulator.
  python3 validate_rule_prd.py APP.app CSV_DIR rule_bw2.prd [--samples 1500] [--seed 1]
Needs: pip install unicorn pandas numpy
"""
import sys, os, struct, random, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import pk5, emu

CHECK, TABLE0 = 0x200C418, 0x203BECC     # BW2 build: checker entry, compiled-in slot-0 table (active before any rule.prd load)
HDR, REC, SIZE = 0x50, 0x244, 0x5E77C

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("app"); ap.add_argument("csv"); ap.add_argument("prd")
    ap.add_argument("--samples", type=int, default=1500); ap.add_argument("--seed", type=int, default=1); a = ap.parse_args()
    raw = open(a.app, "rb").read()
    if raw[0x230:0x238][::-1].hex() != "000300044b394841": sys.exit("need the PokemonBW2 Rule Check Tool .app")
    off, _, load, size = struct.unpack_from("<4I", raw, 0x20); open("/tmp/_v_arm9.bin", "wb").write(raw[off:off+size])
    T = emu.Tool("/tmp/_v_arm9.bin", "bw2")
    prd = open(a.prd, "rb").read(); assert len(prd) == SIZE
    T.put(TABLE0, prd)                                   # slot 0 is the active slot until a rule.prd load swaps buffers
    sp = pd.read_csv(os.path.join(a.csv, "pokemon_species.csv")); exp = pd.read_csv(os.path.join(a.csv, "experience.csv"))
    ab = pd.read_csv(os.path.join(a.csv, "pokemon_abilities.csv")); mv = pd.read_csv(os.path.join(a.csv, "moves.csv")).set_index("identifier").id
    xp100 = {int(r.growth_rate_id): int(r.experience) for r in exp[exp.level == 100].itertuples()}
    growth = dict(zip(sp.id, sp.growth_rate_id)); flags = {s: int.from_bytes(prd[HDR+(s-1)*REC:HDR+(s-1)*REC+2], "little") for s in range(1, 650)}
    ability = {int(p): int(g.sort_values("slot").iloc[0].ability_id) for p, g in ab[(ab.pokemon_id <= 649)&(ab.is_hidden == 0)].groupby("pokemon_id")}
    buf = 0x10001000
    def run(species, moves, **kw):
        d = dict(origin=22, met_loc=10, ball=4, lang=2, species=species, exp=xp100[growth[species]], ability=ability[species],
                 moves=tuple(moves)+(0,)*(4-len(moves)), pp=(5,)*len(moves)+(0,)*(4-len(moves))); d.update(kw)
        T.put(buf, pk5.build(**d)); return T.call(CHECK, 0, buf, 0x88, 1)
    byte = lambda s, m: prd[HDR+(s-1)*REC+0x14+m-1]
    # a species is testable only if its own control Pokemon passes (rules out legendary flags, location lists, min-level...)
    rnd = random.Random(a.seed); ok_species = []
    for s in range(1, 650):
        if s in ability:
            legal = [m for m in range(1, 560) if byte(s, m) & 1 and not byte(s, m) & 0x80 and not byte(s, m) & 0x54]
            if legal and run(s, [legal[0]]) == 0: ok_species.append(s)
    print(f"species whose clean control passes: {len(ok_species)}/649 (others have flag/event/location rules; skipped)")
    classes = collections.defaultdict(collections.Counter); anomalies = []
    EXPECT = {"A": 150, "B": 160, "C": 180, "D": 0}
    for _ in range(a.samples):
        s = rnd.choice(ok_species); m = rnd.randint(1, 559); b = byte(s, m)
        if s == 235: continue                              # Smeargle uses sketch mode; covered by spot checks
        if b & 0x54: continue                              # event-bit cells have combination rules (190/191); not tested here
        cls = "A: no bit0-4 -> expect 150" if not b & 0x1f else ("B: bit7 older-only" if b & 0x80 else ("C: egg-only (b==2)" if b == 2 else "D: ordinary legal -> expect 0"))
        got = run(s, [m]); classes[cls][got] += 1
        if got != EXPECT[cls[0]]: anomalies.append((s, mv.index[mv == m][0], f"byte={b:#04x}", got))
    print("\nverdict of the real checker, grouped by table byte class (code: count)")
    for k in sorted(classes): print(f"  {k:36s} {dict(classes[k])}")
    if anomalies: print("\nanomalies (species, move, table byte, checker verdict):", anomalies)
    # targeted spot checks
    def spot(label, s, m, want):
        got = run(s, [mv[m]]); print(f"  {'PASS' if got == want else 'FAIL'}  {label:46s} -> {got} (expected {want})")
    print("\nspot checks")
    spot("Pikachu + Hyper Beam (not learnable)", 25, "hyper-beam", 150)
    spot("Pikachu + Thunderbolt (TM)", 25, "thunderbolt", 0)
    spot("Pikachu + Sky Drop (not learnable at all)", 25, "sky-drop", 150)
    sd = [s for s in ok_species if byte(s, 507) & 0x1f and s != 235]     # species the table lets learn Sky Drop
    res = {s: run(s, [507]) for s in sd}
    print(f"  {'PASS' if all(v == 170 for v in res.values()) else 'FAIL'}  every table-legal Sky Drop learner ({len(sd)} testable species) -> native code 170: {sorted(set(res.values()))}")
    spot("Pidgeot + Fly (HM)", 18, "fly", 0)
    spot("Bulbasaur + Dark Void (banned/not learnable)", 1, "dark-void", 150)
    spot("Blastoise + Surf (HM)", 9, "surf", 0)
    spot("Smeargle + Steamroller (Sketch)", 235, "steamroller", 0)
    spot("Smeargle + Sky Drop (native check 170)", 235, "sky-drop", 170)
    spot("Smeargle + Dark Void (banned)", 235, "dark-void", 150)
    spot("Smeargle + Chatter (unsketchable)", 235, "chatter", 150)
    spot("Smeargle + Snarl (TM95)", 235, "snarl", 0)

if __name__ == "__main__": main()
