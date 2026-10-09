#!/usr/bin/env python3
"""
make_rule_prd.py - rebuild rule.prd (386,940 bytes) for the Pokemon BW / BW2 Rule Check Tools from PokeAPI CSVs.

FORMAT (all FACT from ARM9 disassembly + compiled-in table; see report):
  0x0000  0x50 bytes   held-item whitelist: bit (itemID-1) set = item allowed; clear -> code 61  -> carried from template
  0x0050  667 records x 0x244 bytes, record N = species N (650-667 = alternate forms)
     +0x00  u16  flags            -> carried from template
     +0x02  u16  minimum legal level (code 31 below it)  -> carried from template
     +0x04  8 x u16  allowed met-location/event IDs (0 = unrestricted)  -> carried from template
     +0x14+ (move-1)  one byte per move ID 1..559 (1..0x230 accepted):
        bit0 (0x01) legal by a normal method (level-up / TM / tutor)             <- DERIVED from PokeAPI
        bit1 (0x02) egg move (flagged 180+slot if Pokemon was not hatched)        <- DERIVED from PokeAPI
        bit2 (0x04), bit4 (0x10)  event-type source flags                         <- carried from template (not in PokeAPI)
        bit6 (0x40)  'cannot be Sketched' -- only meaningful for Smeargle (flag bit3): legal unless set  <- template + bans
        bit7 (0x80) only learnable in an older game, not in BW/BW2 (160+slot)     <- DERIVED from PokeAPI
Usage:
  python3 make_rule_prd.py --csv-dir DIR --template rule_template.prd --target bw2 --out rule_bw2.prd
"""
import argparse, os, sys, csv
import numpy as np, pandas as pd

HDR, REC, NREC, SIZE = 0x50, 0x244, 667, 0x5E77C
LTM = [1, 3, 4]                                   # level-up, tutor, machine
OLDER = [5, 6, 7, 8, 9, 10, 12, 13]               # RS, E, FRLG, DP, Pt, HGSS, Colosseum, XD (can transfer forward)
EGG_VGS = {"bw": [5, 6, 7, 8, 9, 10, 11, 12, 13], "bw2": [5, 6, 7, 8, 9, 10, 11, 12, 13, 14]}
TARGET_VGS = {"bw": [11], "bw2": [11, 14]}
# Dark Void is banned through the table (a zero byte -> code 150 "can't learn"; 0x40 for Smeargle).
# Sky Drop is deliberately NOT zeroed: the tool has its own check (mode 0, move ID 507 in any slot -> code 170+slot,
# message "This Pokemon knows Sky Drop. Change this move."). Zeroing it would hide that message behind code 150.
BANNED = {464: "dark-void"}

def load(csv_dir):
    sp = pd.read_csv(os.path.join(csv_dir, "pokemon_species.csv"))
    pm = pd.read_csv(os.path.join(csv_dir, "pokemon_moves.csv"))
    pk = pd.read_csv(os.path.join(csv_dir, "pokemon.csv"))
    # alternate-form rows (pokemon_id > 10000) are merged into their species: the original species record is the
    # union of its forms' learnsets (verified on Deoxys 386, Giratina 487, Shaymin 492)
    pm = pm.assign(pokemon_id=pm.pokemon_id.map(dict(zip(pk.id, pk.species_id))))
    pm = pm[(pm.pokemon_id <= 649) & (pm.move_id <= 559)]
    parent = {int(r.id): (None if pd.isna(r.evolves_from_species_id) else int(r.evolves_from_species_id))
              for r in sp.itertuples() if r.id <= 649}
    return pm, parent

def move_sets(pm, vgs, meths):
    d = pm[pm.version_group_id.isin(vgs) & pm.pokemon_move_method_id.isin(meths)]
    M = np.zeros((668, 561), bool); M[d.pokemon_id.values, d.move_id.values] = True
    return M

EXTRA_SOURCES = {292: [291]}                       # Shedinja is created at Nincada->Ninjask evolution: it may know Ninjask's moves

def chain_union(M, parent):                        # an evolved form may know anything its pre-evolutions learned
    N = M.copy()
    for s in range(1, 650):
        p = parent.get(s)
        while p:
            N[s] |= M[p]; p = parent.get(p)
    for s, srcs in EXTRA_SOURCES.items():
        for x in srcs: N[s] |= N[x]
    return N

def derive(csv_dir, target):
    pm, parent = load(csv_dir)
    A5 = chain_union(move_sets(pm, TARGET_VGS[target], LTM), parent)
    O = chain_union(move_sets(pm, OLDER, LTM), parent)
    EGG = chain_union(move_sets(pm, EGG_VGS[target], [2]), parent)
    b = (A5 | O).astype(np.uint8) | (EGG.astype(np.uint8) << 1) | ((O & ~A5 & ~EGG).astype(np.uint8) << 7)
    return b

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", required=True); ap.add_argument("--template", required=True)
    ap.add_argument("--target", choices=["bw", "bw2"], default="bw2"); ap.add_argument("--out", required=True)
    ap.add_argument("--events", choices=["template", "none"], default="template",
                    help="carry the template's event-source bits (2,4,6) -- PokeAPI has no event-move data")
    ap.add_argument("--hidden-abilities", choices=["allow", "template"], default=None,
                    help="species flag 0x400 makes a Hidden Ability return code 62. Template sets it on 645/649 species (BW1-era). "
                         "Default: allow for --target bw2 (2013 VGC permitted Dream World abilities), template for --target bw")
    ap.add_argument("--report", help="write per-cell differences vs template to this CSV")
    a = ap.parse_args()
    tpl = open(a.template, "rb").read()
    if len(tpl) != SIZE: sys.exit(f"template must be {SIZE} bytes, got {len(tpl)}")
    out = bytearray(tpl)
    D = derive(a.csv_dir, a.target)
    ban = dict(BANNED)
    diffs = []
    names = pd.read_csv(os.path.join(a.csv_dir, "moves.csv")).set_index("id").identifier
    for s in range(1, NREC + 1):
        base = HDR + (s - 1) * REC + 0x14
        for m in range(1, 560):
            old = tpl[base + m - 1]
            if s <= 649:
                new = int(D[s, m])
                if a.events == "template": new |= old & 0x54
                if a.events == "template" and old & 0x54: new |= old       # keep the original's full byte where event bits apply
            else:
                new = old if a.events == "template" else old & ~0x54        # alternate forms: carried
            sketch_mode = int.from_bytes(tpl[HDR + (s - 1) * REC: HDR + (s - 1) * REC + 2], "little") & 8   # Smeargle only
            if sketch_mode:
                # flag bit3 species: accessor 0x0200B2A0 treats a move as legal UNLESS byte bit6 (0x40) is set
                if m == 555 and D[:, 555].any(): new = 0      # Snarl is a BW/BW2 TM (PokeAPI machines.csv), so Smeargle may Sketch it
            if m in ban: new = 0x40 if sketch_mode else 0     # a plain 0 would leave the move legal for a sketch-mode species
            out[base + m - 1] = new
            if new != old: diffs.append((s, m, names.get(m, m), old, new))
    ha = a.hidden_abilities or ("allow" if a.target == "bw2" else "template")
    if ha == "allow":
        for sp_ in range(1, NREC + 1):
            o = HDR + (sp_ - 1) * REC
            f = int.from_bytes(out[o:o + 2], "little") & ~0x400
            out[o:o + 2] = f.to_bytes(2, "little")
    print(f"hidden abilities: {ha}")
    open(a.out, "wb").write(out)
    print(f"wrote {a.out} ({len(out)} bytes); cells changed vs template: {len(diffs)}")
    if a.report:
        with open(a.report, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["species", "move_id", "move", "template_byte", "new_byte"]); w.writerows(diffs)

if __name__ == "__main__":
    main()
