#!/usr/bin/env python3
"""
make_testcase.py - build the illegal-party test case for the PokemonBW2 Rule Check Tool and VERIFY every expected
error code by running the app's own checker (ARM9 0x0200C418 -> 0x0200D070 -> 0x0200B430) in an emulator.

  python3 make_testcase.py APP.app [--prd rule.prd] [--out DIR]

Without --prd the table compiled into the app (slot 0, the active buffer before any rule.prd load) is used.
Needs: pip install unicorn
Output: DIR/party/*.pk5 (6 files = one illegal party), DIR/extended/*.pk5, DIR/manifest.csv
The .pk5 files are 136-byte stored Gen-5 Pokemon, synthetic, generated here (no game data inside).
"""
import sys, os, csv, struct, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pk5, emu

CHECK, TO_PARTY, GETTER = 0x200C418, 0x200D070, 0x200D828       # BW2 build addresses
TABLE0 = 0x203BECC
BASE = dict(origin=22, met_loc=10, ball=4, lang=2)              # met_loc 10 passes the location check (swept: 10/30/60/100 ok; 1/2000 fail)

def exp_medfast(n): return n ** 3
def exp_medslow(n): return max(0, 6 * n ** 3 // 5 - 15 * n * n + 100 * n - 140)
def exp_slow(n): return int(1.25 * n ** 3)

# (file, folder, label, kwargs, expected_code, short explanation)
CASES = [
 # ---- the six-Pokemon illegal party ---------------------------------------------------------------------------
 ("slot1_ivysaur_lv10.pk5", "party", "Ivysaur Lv10 (below its minimum legal level 16)",
    dict(species=2, exp=exp_medslow(10), ability=65, moves=(33, 0, 0, 0), pp=(35, 0, 0, 0)), 31, "below minimum level (rule.prd record+2)"),
 ("slot2_mew_no_flag.pk5", "party", "Mew Lv50 without the fateful/event flag",
    dict(species=151, exp=exp_medslow(50), ability=28, moves=(33, 0, 0, 0), pp=(35, 0, 0, 0)), 33, "limited-distribution species without event flag"),
 ("slot3_pikachu_hyperbeam.pk5", "party", "Pikachu knows Hyper Beam in slot 2 (not learnable)",
    dict(moves=(85, 63, 0, 0), pp=(15, 5, 0, 0), exp=exp_medfast(50)), 151, "move not learnable, slot 2"),
 ("slot4_pikachu_dupe_move.pk5", "party", "Pikachu with Thunderbolt in slots 1 and 2",
    dict(moves=(85, 85, 0, 0), pp=(15, 15, 0, 0), exp=exp_medfast(50)), 131, "duplicate move (slot 2 repeats slot 1)"),
 ("slot5_pikachu_bad_ball.pk5", "party", "Pikachu in invalid ball ID 26",
    dict(ball=26, exp=exp_medfast(50)), 50, "ball ID outside 1-25"),
 ("slot6_charizard_sky_drop.pk5", "party", "Charizard knows Sky Drop (banned)",
    dict(species=6, exp=exp_medslow(50), ability=66, moves=(507, 0, 0, 0), pp=(5, 0, 0, 0)), 170, "native Sky Drop check (mode 0)"),
 # ---- control + extended --------------------------------------------------------------------------------------
 ("control_legal_pikachu.pk5", "extended", "CONTROL: legal Pikachu Lv50 (must return 0)", dict(exp=exp_medfast(50)), 0, "no error"),
 ("e01_first_move_empty.pk5", "extended", "Move in slot 2 only; slot 1 empty", dict(moves=(0, 98, 0, 0), pp=(0, 30, 0, 0), exp=exp_medfast(50)), 140, "first move slot empty"),
 ("e02_gap_in_moves.pk5", "extended", "Slot 2 empty, slot 3 filled", dict(moves=(85, 0, 98, 0), pp=(15, 0, 30, 0), exp=exp_medfast(50)), 141, "empty slot before a filled one"),
 ("e03_dupe_move_1_3.pk5", "extended", "Quick Attack in slots 1 and 3", dict(moves=(98, 85, 98, 0), pp=(30, 15, 30, 0), exp=exp_medfast(50)), 132, "duplicate move (slot 3 repeats an earlier slot)"),
 ("e04_pikachu_sky_drop.pk5", "extended", "Pikachu with Sky Drop (it can never learn it)", dict(moves=(507, 98, 0, 0), pp=(5, 30, 0, 0), exp=exp_medfast(50)), 150, "unlearnable move is caught by rule.prd BEFORE the native Sky Drop check"),
 ("e05_move_id_out_of_range.pk5", "extended", "Move ID 600 (> 560)", dict(moves=(600, 98, 0, 0), pp=(10, 30, 0, 0), exp=exp_medfast(50)), 120, "move ID out of range"),
 ("e06_ev_total_over_510.pk5", "extended", "EVs 255 in every stat (total 1530)", dict(evs=(255,) * 6, exp=exp_medfast(50)), 90, "total EV > 510"),
 ("e07_nature_out_of_range.pk5", "extended", "Nature value 40", dict(nature=40, exp=exp_medfast(50)), 200, "nature > 25"),
 ("e08_invalid_form.pk5", "extended", "Pikachu form 5", dict(form=5, exp=exp_medfast(50)), 32, "form above the species' maximum form"),
 ("e09_unobtainable_item.pk5", "extended", "Holding item ID 700", dict(item=700, exp=exp_medfast(50)), 61, "item ID > 625"),
 ("e10_species_zero.pk5", "extended", "Species 0", dict(species=0, exp=exp_medfast(50)), 20, "species out of range"),
 ("e11a_bad_checksum.pk5", "extended", "Stored checksum does not match the data", dict(bad_checksum=True, exp=exp_medfast(50)), 10, "'Bad Egg' via checksum mismatch"),
 ("e11b_bad_egg_flag.pk5", "extended", "Bad Egg flag set (sanity word bit 2)", dict(bad_egg=True, exp=exp_medfast(50)), 10, "'Bad Egg' via flag"),
 ("e12_mewtwo_lv50.pk5", "extended", "Mewtwo Lv50 (below its table minimum)", dict(species=150, exp=exp_slow(50), ability=46, moves=(33, 0, 0, 0), pp=(35, 0, 0, 0)), 31, "below minimum level"),
 ("e13_older_only_move.pk5", "extended", "Bulbasaur with Headbutt (#29): older-game-only move, native Pokemon",
    dict(species=1, exp=exp_medslow(50), ability=65, moves=(29, 0, 0, 0), pp=(15, 0, 0, 0)), 160, "table byte has bit 0x80"),
 ("e14_egg_move_not_hatched.pk5", "extended", "Charmander with Bite (egg-only move), not hatched",
    dict(species=4, exp=exp_medslow(50), ability=66, moves=(44, 0, 0, 0), pp=(25, 0, 0, 0)), 180, "egg-only move, egg location = 0"),
 ("e15_xd_move_plus_egg_move.pk5", "extended", "Pidgeotto: XD-only Refresh + egg-only Feint Attack, transferred (met location 30001)",
    dict(species=17, exp=exp_medslow(50), ability=51, moves=(287, 185, 0, 0), pp=(20, 20, 0, 0), met_loc=30001), 190, "XD-only move combined with egg-only move"),
 ("e16_dist_move_plus_egg_move.pk5", "extended", "Charmander: distribution-only Quick Attack + egg-only Bite, transferred",
    dict(species=4, exp=exp_medslow(50), ability=66, moves=(98, 44, 0, 0), pp=(30, 25, 0, 0), met_loc=30001), 191, "distribution-only move combined with egg-only move"),
 ("e17_unown_hatched_wrong_place.pk5", "extended", "Unown hatched (egg location set) with met location 10",
    dict(species=201, exp=exp_medfast(50), ability=26, moves=(237, 0, 0, 0), pp=(15, 0, 0, 0), egg_loc=60002), 211, "limited species hatched without Poke Transfer"),
 ("e18_articuno_wrong_place.pk5", "extended", "Articuno caught at location 10 (not in its allowed list)",
    dict(species=144, exp=exp_slow(70), ability=46, moves=(58, 0, 0, 0), pp=(10, 0, 0, 0)), 212, "met location not in the species' allowed list"),
]

def build(kw):
    d = dict(BASE); d.update(kw)
    d.setdefault("moves", (85, 98, 0, 0)); d.setdefault("pp", (15, 30, 0, 0))
    return pk5.build(**d)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("app"); ap.add_argument("--prd"); ap.add_argument("--out", default=".")
    a = ap.parse_args()
    raw = open(a.app, "rb").read()
    if raw[0x230:0x238][::-1].hex() != "000300044b394841": sys.exit("not the PokemonBW2 Rule Check Tool app")
    off, _, load, size = struct.unpack_from("<4I", raw, 0x20)
    open("/tmp/_bw2_arm9.bin", "wb").write(raw[off:off + size]); T = emu.Tool("/tmp/_bw2_arm9.bin", "bw2")
    table = "table compiled into the app"
    if a.prd:
        T.put(TABLE0, open(a.prd, "rb").read()); table = os.path.basename(a.prd)
    for d in ("party", "extended"): os.makedirs(os.path.join(a.out, d), exist_ok=True)
    buf, b220 = 0x10001000, 0x10004000
    rows, bad = [], 0
    for f, folder, label, kw, exp, text in CASES:
        data = build(kw); open(os.path.join(a.out, folder, f), "wb").write(data)
        T.put(buf, data); got = T.call(CHECK, 0, buf, 0x88, 1); lvl = T.call(GETTER, buf, 0x9F, 0)
        T.put(buf, data); T.call(TO_PARTY, buf, b220, max(1, min(100, lvl)))      # party records are 0xDC bytes: convert, then re-check
        got_party = T.call(CHECK, 0, b220, 0xDC, 0)
        if "bad_checksum" in f or "bad_egg" in f: got_party = "skipped"          # converter output of a corrupt record is not meaningful
        elif got_party != exp: bad += 1
        if got != exp: bad += 1
        rows.append([f"{folder}/{f}", label, lvl, exp, got, got_party, text])
    with open(os.path.join(a.out, "manifest.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "what_is_wrong", "level_per_tool", "expected_code", "emulated_stored_0x88", "emulated_party_0xDC", "explanation"]); w.writerows(rows)
    for r in rows: print(f"{r[0]:48s} lvl={r[2]!s:>3} expect={r[3]:>3} stored={r[4]!s:>4} party={r[5]!s:>7}")
    print(f"table used: {table}")
    print("ALL EXPECTED CODES CONFIRMED" if not bad else f"MISMATCHES: {bad}")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
