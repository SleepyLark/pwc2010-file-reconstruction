#!/usr/bin/env python3
"""
read_logs.py - decode the logB / logT files written by the Rule Check Tool (and read by the Log Viewer).

  python3 read_logs.py logT261004.dat logB261004.dat
  python3 read_logs.py logT261004.dat --names-csv POKEAPI_CSV_DIR      # species and move names
  python3 read_logs.py logT261004.dat --csv out.csv                    # flat table
  python3 read_logs.py logT261004.dat --anonymize                      # hide player name and nicknames
  python3 read_logs.py logT261004.dat --sanitize-to DIR                # write a shareable copy

FILE FORMAT (all verified: see docs/13-Log-Files-and-Viewer.md)
  A log file is a sequence of 0x234-byte records. The Rule Check Tool APPENDS one record per run.
  logT = Party (up to 6 Pokemon), logB = Battle Box.  Filename: logT/logB + YYMMDD (the DSi clock's date).
  record  = 0x24-byte header + 6 x 0x58-byte Pokemon entries
  header  : +0x00 u32 record id (1-based, = records already in the file + 1)
            +0x04 u32 number of Pokemon
            +0x08 16 bytes player name (UTF-16LE, 8 chars)
            +0x18 u32 box/party number (drawn in white on the right of the viewer)
            +0x1C 2 bytes  uninitialised memory
            +0x1E u8  party-level flag  (= low byte of the value below, 0 if none)
            +0x20 u32 PARTY-LEVEL BITMASK  (NOT a 600-series code, see PARTY_BITS)
  entry   : see ENTRY_FIELDS; +0x54 u32 = the ERROR CODE shown in red by the viewer
"""
import struct, sys, os, csv, json, argparse

REC, HDR_SZ, ENT_SZ = 0x234, 0x24, 0x58
HDR = struct.Struct("<I I 16s I 2s B B I")
ENT = struct.Struct("<11H H H 6B 4H H 2B 12B 4B 2B 6H 4B 2H 2s I")
assert HDR.size == HDR_SZ and ENT.size == ENT_SZ and HDR_SZ + 6 * ENT_SZ == REC

# party-level bitmask written by the Rule Check Tool (init routine ORs these into one word)
PARTY_BITS = {0x02: (600, "two Pokemon of the same species"),
              0x04: (601, "two Pokemon holding the same item"),
              0x08: (602, "total level above the limit"),
              0x10: (603, "fewer Pokemon than the minimum")}

def u16str(words):
    out = ""
    for w in words:
        if w in (0, 0xFFFF): break
        out += chr(w)
    return out

def parse_entry(raw):
    r = ENT.unpack(raw)
    nick = u16str(r[0:11]); v = list(r[11:])
    (species, level, gender, nature, friendship, fateful, ball, language, m1, m2, m3, m4, item, ability, form,
     hpiv, hpev, atkiv, atkev, defiv, defev, speiv, speev, spaiv, spaev, spdiv, spdev, pp1, pp2, pp3, pp4, hpt, hpp,
     s_hp, s_atk, s_def, s_spe, s_spa, s_spd, version, met_level, shiny, resid3, egg_loc, met_loc, resid4, code) = v
    return dict(nickname=nick, species=species, level=level, gender=gender, nature=nature, friendship=friendship,
                fateful_flag=fateful, ball=ball, language=language, moves=[m1, m2, m3, m4], item=item, ability=ability, form=form,
                ivs=dict(hp=hpiv, atk=atkiv, df=defiv, spe=speiv, spa=spaiv, spd=spdiv),
                evs=dict(hp=hpev, atk=atkev, df=defev, spe=speev, spa=spaev, spd=spdev), pp=[pp1, pp2, pp3, pp4],
                hidden_power_type_bits=hpt, hidden_power_power_bits=hpp,
                stats=dict(hp=s_hp, atk=s_atk, df=s_def, spe=s_spe, spa=s_spa, spd=s_spd),
                version=version, met_level=met_level, shiny=shiny, egg_location=egg_loc, met_location=met_loc, code=code)

def parse_file(path):
    d = open(path, "rb").read()
    if len(d) % REC: print(f"warning: {path}: size {len(d)} is not a multiple of {REC}", file=sys.stderr)
    recs = []
    for i in range(len(d) // REC):
        o = i * REC; h = HDR.unpack_from(d, o)
        ents = []
        for s in range(6):
            raw = d[o + HDR_SZ + s * ENT_SZ:o + HDR_SZ + (s + 1) * ENT_SZ]
            e = parse_entry(raw); e["slot"] = s + 1; e["empty"] = (e["species"] == 0); ents.append(e)
        recs.append(dict(index=i, id=h[0], count=h[1], player=u16str(struct.unpack("<8H", h[2])), number_on_right=h[3],
                         flag=h[5], party_mask=h[7], entries=ents))
    return recs

def load_messages(here):
    p = os.path.join(here, "..", "docs", "error_codes.csv"); m = {}
    if os.path.exists(p):
        for row in csv.DictReader(open(p, encoding="utf-8")):
            m[int(row["code"])] = row["message_text_english"]
    return m

def load_names(csv_dir):
    import pandas as pd
    sn = pd.read_csv(os.path.join(csv_dir, "pokemon_species_names.csv")); sn = sn[sn.local_language_id == 9].set_index("pokemon_species_id").name
    mn = pd.read_csv(os.path.join(csv_dir, "move_names.csv")); mn = mn[mn.local_language_id == 9].set_index("move_id").name
    return sn.to_dict(), mn.to_dict()

def decode_mask(mask):
    return [(c, t) for bit, (c, t) in PARTY_BITS.items() if mask & bit], mask & ~0x1E

def sanitize(path, outdir):
    d = bytearray(open(path, "rb").read())
    for i in range(len(d) // REC):
        o = i * REC
        d[o + 8:o + 24] = b"P\0L\0A\0Y\0E\0R\0\0\0\0\0"             # player name
        d[o + 0x1C:o + 0x1E] = b"\0\0"                              # uninitialised
        for s in range(6):
            e = o + HDR_SZ + s * ENT_SZ
            if struct.unpack_from("<H", d, e + 0x16)[0]:
                d[e:e + 22] = b"\xff\xff" * 11; d[e:e + 2] = b"\0\0"      # nickname cleared
            d[e + 0x4D] = 0; d[e + 0x52:e + 0x54] = b"\0\0"          # uninitialised bytes
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "sample_" + os.path.basename(path)); open(out, "wb").write(d); return out

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+"); ap.add_argument("--names-csv"); ap.add_argument("--csv"); ap.add_argument("--json")
    ap.add_argument("--anonymize", action="store_true"); ap.add_argument("--sanitize-to")
    a = ap.parse_args(); here = os.path.dirname(os.path.abspath(__file__))
    msgs = load_messages(here); sn, mn = load_names(a.names_csv) if a.names_csv else ({}, {})
    flat = []; alljson = {}
    for f in a.files:
        recs = parse_file(f); kind = "Party (logT)" if "logT" in os.path.basename(f) else "Battle Box (logB)" if "logB" in os.path.basename(f) else "log"
        alljson[f] = recs
        print(f"\n=== {os.path.basename(f)}  [{kind}]  {len(recs)} record(s)")
        for r in recs:
            who = "<hidden>" if a.anonymize else repr(r["player"])
            conds, extra = decode_mask(r["party_mask"])
            print(f"- record id {r['id']}: player {who}, {r['count']} Pokemon, box number {r['number_on_right']}")
            if r["party_mask"]:
                txt = "; ".join(f"{c} ({t})" for c, t in conds) + (f"; unknown bits {extra:#x}" if extra else "")
                print(f"    PARTY-LEVEL: value shown by the viewer = {r['party_mask']}  ->  {txt}")
            else:
                print("    party-level: none")
            for e in r["entries"]:
                if e["empty"]: continue
                nm = sn.get(e["species"], f"#{e['species']}"); mv = ", ".join(str(mn.get(m, m)) for m in e["moves"] if m)
                nick = "" if a.anonymize else f" '{e['nickname']}'"
                code = e["code"]; text = "ok" if code == 0 else f"CODE {code}: {msgs.get(code, '(message table not found)')}"
                print(f"    slot {e['slot']}: {nm}{nick} Lv{e['level']}  moves [{mv}]  ->  {text}")
                flat.append(dict(file=os.path.basename(f), record_id=r["id"], slot=e["slot"], species=e["species"], level=e["level"],
                                 code=code, message=msgs.get(code, "") if code else "", party_mask=r["party_mask"]))
        if a.sanitize_to: print("  sanitized copy:", sanitize(f, a.sanitize_to))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(flat[0].keys()) if flat else ["file"]); w.writeheader(); w.writerows(flat)
        print("wrote", a.csv)
    if a.json: json.dump(alljson, open(a.json, "w"), indent=1); print("wrote", a.json)

if __name__ == "__main__":
    main()
