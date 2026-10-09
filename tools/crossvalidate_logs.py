#!/usr/bin/env python3
"""
crossvalidate_logs.py - compare the emulated checker with a REAL DSi run.

Every Pokemon in a logT/logB file is rebuilt from its log entry and fed to the emulated BW2 checker with a chosen
rule.prd; the emulator's verdict is compared with the error code the DSi itself wrote into the log.

  python3 crossvalidate_logs.py APP.app POKEAPI_CSV rule.prd logT....dat [logB....dat ...]

Fields that the log does not contain (PID, TID/SID, OT, nickname) are filled with neutral values; none of them takes
part in the checks that matter for the codes seen so far (the shiny test only applies to a few shiny-locked species).
Exit status 0 only if every Pokemon agrees.
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, pk5, emu
from read_logs import parse_file

def main():
    app, csv_dir, prd, *logs = sys.argv[1:]
    raw = open(app, "rb").read(); assert raw[0x230:0x238][::-1].hex() == "000300044b394841", "need the BW2 tool .app"
    off, _, _, size = struct.unpack_from("<4I", raw, 0x20); open("/tmp/_xv.bin", "wb").write(raw[off:off + size])
    T = emu.Tool("/tmp/_xv.bin", "bw2"); T.put(0x203BECC, open(prd, "rb").read())
    sp = pd.read_csv(f"{csv_dir}/pokemon_species.csv"); ex = pd.read_csv(f"{csv_dir}/experience.csv")
    gr = dict(zip(sp.id, sp.growth_rate_id)); EXP = {(int(r.growth_rate_id), int(r.level)): int(r.experience) for r in ex.itertuples()}
    total = agree = 0
    for f in logs:
        for r in parse_file(f):
            for e in r["entries"]:
                if e["empty"]: continue
                iv, ev = e["ivs"], e["evs"]
                b = pk5.build(species=e["species"], item=e["item"], exp=EXP[(int(gr[e["species"]]), e["level"])], friend=e["friendship"],
                              ability=e["ability"], lang=e["language"], evs=tuple(ev[k] for k in ("hp", "atk", "df", "spe", "spa", "spd")),
                              moves=tuple(e["moves"]), pp=tuple(e["pp"]), ivs=tuple(iv[k] for k in ("hp", "atk", "df", "spe", "spa", "spd")),
                              form=e["form"], gender=1 if e["gender"] == 1 else 0, genderless=1 if e["gender"] == 2 else 0,
                              nature=e["nature"], origin=e["version"], met_loc=e["met_location"], egg_loc=e["egg_location"], ball=e["ball"],
                              met_level=e["met_level"], fateful=1 if e["fateful_flag"] else 0)
                T.put(0x10001000, b); got = T.call(0x200C418, 0, 0x10001000, 0x88, 1)
                total += 1; agree += (got == e["code"])
                print(f"{'OK  ' if got == e['code'] else 'DIFF'} {os.path.basename(f)} record {r['id']} slot {e['slot']} species {e['species']:3d} Lv{e['level']:3d}: "
                      f"DSi logged {e['code']:3d}  emulator {got:4d}")
    print(f"\n{agree}/{total} Pokemon agree with the real DSi log using {os.path.basename(prd)}")
    sys.exit(0 if agree == total else 1)

if __name__ == "__main__":
    main()
