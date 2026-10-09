#!/usr/bin/env python3
"""
build_error_table.py - generate the error-code reference for the PokemonBW2 Rule Check Tool from the app itself.

  python3 build_error_table.py APP.app OUT_DIR

What it does (everything except the KNOWLEDGE dictionary comes straight from the binary):
  1. extracts data/message_E.dat from the NitroFS (66 lines, UTF-16LE; '@' is a line-break marker in the on-screen text)
  2. runs the app's own code->message-index routine (ARM9 0x020082CC) in an emulator for every code -1..700
  3. scans the checker (0x0200B430-0x0200C418) for every instruction that sets a return code, so addresses are reproducible
  4. merges the hand-written KNOWLEDGE table (trigger conditions, data source, verification status)
Writes OUT_DIR/error_codes.csv and OUT_DIR/message_bank_E.txt
Needs: pip install unicorn capstone
"""
import sys, os, re, csv, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_SP, UC_ARM_REG_LR

def nitrofs(d):
    fnt, _ = struct.unpack_from("<2I", d, 0x40); fat, fatsz = struct.unpack_from("<2I", d, 0x48)
    fats = [struct.unpack_from("<2I", d, fat + 8 * i) for i in range(fatsz // 8)]; names = {}
    def walk(did, path):
        off, fid, _p = struct.unpack_from("<IHH", d, fnt + 8 * (did & 0xfff)); p = fnt + off
        while True:
            t = d[p]; p += 1
            if t == 0: break
            ln = t & 0x7f; nm = d[p:p+ln].decode(); p += ln
            if t & 0x80: sub = struct.unpack_from("<H", d, p)[0]; p += 2; walk(sub, path + nm + "/")
            else: names[fid] = path + nm; fid += 1
    walk(0xF000, "/")
    return {names[i]: d[s:e] for i, (s, e) in enumerate(fats) if i in names}

# code -> (who decides, trigger, data source, status).  status: verified (emulator) / read (code only) / unreachable / not-observed
V, RD, UN, NO = "verified", "read-only", "unreachable", "not observed"
K = {}
def put(codes, who, trigger, src, status, note=""):
    for c in (codes if isinstance(codes, (list, tuple, range)) else [codes]): K[c] = (who, trigger, src, status, note)
put(-1, "init", "slot is empty (no Pokemon stored there)", "save data", RD, "shown as 'no Pokemon' only when no slot holds a Pokemon (inference)")
put(0, "-", "no problem found for this Pokemon", "-", V)
put(10, "checker", "Bad Egg: the Bad Egg flag (sanity word bit 2) is set, or the stored checksum does not match the data", "save data", V)
put(20, "checker", "species number is 0 or above 649", "save data", V)
put(21, "?", "message exists; no return site found in the BW2 code path", "-", NO)
put(22, "rule.prd", "species is shiny-locked (flag 0x0002) and the Pokemon is shiny", "rule.prd record+0 flags", V)
put(23, "rule.prd", "species flag 0x80 (mode 4) / 0x100 (mode 1) / 0x200 (mode 2). The BW2 tool always uses mode 0, so never evaluated", "rule.prd record+0 flags", UN, "semantics verified by calling the checker with mode 1")
put(30, "checker", "level is not in 1..100 (mode != 4)", "save data", V, "tested via a party-form record with level 0 and 101")
put(31, "rule.prd", "level is below the species' minimum legal level (record+2)", "rule.prd record+2", V)
put(32, "rule.prd", "form number is above the species' maximum form (record+3, signed)", "rule.prd record+3", V)
put(33, "rule.prd", "species flag 0x0004 (limited distribution) and the event/fateful flag is not set", "rule.prd record+0 flags", V)
put(50, "checker", "ball ID is outside 1..25", "save data", V)
put(51, "rule.prd", "species flag 0x0010 requires an ordinary Poke Ball (ID 4) and the ball is different", "rule.prd record+0 flags", V)
put(52, "checker", "egg location is set (hatched) and the ball is not a Poke Ball (ID 4)", "save data", V)
put(60, "checker", "ability is not one of the species' abilities (with exceptions for a few form species)", "app species data", V)
put(61, "rule.prd", "held item ID above 625, or the item's bit is clear in rule.prd's 80-byte item whitelist (mode 0 also rejects item 225)", "rule.prd bytes 0x00-0x4F", V)
put(62, "rule.prd", "species flag 0x0400 and the ability is the species' Hidden Ability", "rule.prd record+0 flags", V, "the BW1-era template sets 0x0400 on 645/649 species; rule_bw2.prd clears it by default")
put(64, "rule.prd", "species flag 0x1000 with Hidden Ability and gender field 0x6E non-zero", "rule.prd record+0 flags", UN, "no species carries flag 0x1000 in the compiled-in table")
put(70, "?", "message exists; no return site found in the BW2 code path", "-", NO)
put(range(80, 86), "checker", "an EV value is above 255 (one code per stat: 80 HP, 81 Atk, 82 Def, 83 Spe, 84 SpA, 85 SpD)", "save data", UN, "EV is stored in one byte, so a stored record cannot exceed 255; stat order inferred from the getter field order 0x0D-0x12")
put(90, "checker", "total EVs above 510", "save data", V)
put(range(100, 106), "checker", "an IV ('Power's random value') is out of range (one code per stat: 100 HP, 101 Atk, 102 Def, 103 Spe, 104 SpA, 105 SpD)", "save data", UN, "IV is stored in 5 bits, so a stored record cannot exceed 31; stat order inferred from the getter field order 0x46-0x4B")
put(range(120, 124), "checker", "move ID in slot N (120 = slot 1) is above 560", "save data", V, "verified for slot 1")
put(range(131, 134), "checker", "a move repeats an earlier slot: 131 = slot 2, 132 = slot 3, 133 = slot 4", "save data", V)
put(140, "checker", "move slot 1 is empty", "save data", V)
put(141, "checker", "an empty move slot is followed by a filled one", "save data", V)
put(range(150, 154), "rule.prd", "the move in slot N (150 = slot 1) has no legal-source bit (0x01..0x10) for this species", "rule.prd record move bytes", V, "verified for all four slots")
put(range(160, 164), "rule.prd", "slot N has an older-game-only move (byte bit 0x80) on a Pokemon that did not come through Poke Transfer (modes 0-2)", "rule.prd record move bytes", V, "verified for slot 1")
put(range(170, 174), "checker", "slot N (170 = slot 1) holds Sky Drop (move 507). Mode 0 only; evaluated after the learnability checks", "fixed in code", V, "only reached if the table says the species can learn Sky Drop; otherwise 150")
put(range(180, 184), "rule.prd", "slot N has an egg-only move (byte bit 0x02, no other source) and the Pokemon was not hatched (egg location = 0)", "rule.prd record move bytes", V, "verified for slot 1")
put(190, "rule.prd", "an XD-only move (byte bit 0x10) together with an egg-only move", "rule.prd record move bytes", V, "only for transferred Pokemon (met location 30001), otherwise 160 fires first")
put(191, "rule.prd", "a distribution-only move (byte bit 0x04) together with an egg-only move", "rule.prd record move bytes", V, "only for transferred Pokemon (met location 30001), otherwise 160 fires first")
put(200, "checker", "nature value above 25", "save data", V)
put(201, "checker", "gender does not match the species' gender ratio", "app species data", NO, "toggling the stored gender/genderless bits never triggered it; gender appears to be derived")
put(210, "checker", "met location is non-zero but not a valid location ID ('Mystery Zone')", "app location table", V)
put(211, "rule.prd", "species flag 0x0020, egg location set, and met location not in {30001, 30010-30013, 30014, 73}", "rule.prd flags + save data", V)
put(212, "rule.prd", "species has an allowed-location list (record+4, up to 8 x u16) and the met location is not in it", "rule.prd record+4..+0x13", V)
put(230, "?", "message exists; no return site found in the BW2 code path", "-", NO)
put(500, "regulation.bin", "species bit set in the banned-species bitmap (bytes 0x12-0x63)", "regulation.bin", V, "accessor verified in emulator; only evaluated if the Pokemon passed every rule.prd check")
put(501, "regulation.bin", "held item bit set in the banned-item bitmap (bytes 0x64-0xB3)", "regulation.bin", V, "accessor verified in emulator")
put(502, "regulation.bin", "level rule: mode (byte 0x0D) 1 = level must be >= byte 0x0C, mode 2 = level must be <= byte 0x0C", "regulation.bin", V, "accessor verified in emulator")
put(600, "regulation.bin", "two Pokemon of the same species (skipped when byte 0x10 is non-zero)", "regulation.bin", V, "party/box-wide; accessor verified. The LOG stores bit 0x02 (viewer shows 2)")
put(601, "regulation.bin", "two Pokemon holding the same item (skipped when byte 0x11 is non-zero)", "regulation.bin", V, "party/box-wide; accessor verified. The LOG stores bit 0x04 (viewer shows 4)")
put(602, "regulation.bin", "sum of levels above the cap (u16 at 0x0E; 0 = no cap)", "regulation.bin", V, "party/box-wide; accessor verified. The LOG stores bit 0x08 (viewer shows 8)")
put(603, "regulation.bin", "fewer Pokemon than the minimum (byte 0x0A)", "regulation.bin", V, "party/box-wide; accessor verified; CONFIRMED ON REAL HARDWARE (2-Pokemon Battle Box logged value 16). The LOG stores bit 0x10 (viewer shows 16)")

def main():
    app, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
    raw = open(app, "rb").read(); assert raw[0x230:0x238][::-1].hex() == "000300044b394841", "need the PokemonBW2 Rule Check Tool .app"
    fs = nitrofs(raw); msgs = fs["/data/message_E.dat"].decode("utf-16le").split("\n")
    open(os.path.join(out, "message_bank_E.txt"), "w", encoding="utf-8").write("\n".join(f"{i}\t{m}" for i, m in enumerate(msgs)))
    off, _, load, size = struct.unpack_from("<4I", raw, 0x20); a9 = raw[off:off+size]; open("/tmp/_et.bin", "wb").write(a9)
    T = emu.Tool("/tmp/_et.bin", "bw2"); mu = T.mu
    def msg_index(code):
        mu.reg_write(UC_ARM_REG_R0, code & 0xffffffff); mu.reg_write(UC_ARM_REG_SP, 0x2380000); mu.reg_write(UC_ARM_REG_LR, 0x10008000)
        mu.mem_write(0x10008000, b"\x00\x00\xa0\xe1" * 4); mu.emu_start(0x20082CC, 0x10008000, count=200)
        r = mu.reg_read(UC_ARM_REG_R0); return r - (1 << 32) if r & 0x80000000 else r
    # return sites inside the checker: instructions that load a constant (or base + register) into r0 before leaving
    md = Cs(CS_ARCH_ARM, CS_MODE_ARM); md.skipdata = True; sites = {}
    ins = list(md.disasm(a9[0x200B430 - 0x2004000:0x200C418 - 0x2004000], 0x200B430))
    for k, i in enumerate(ins):
        m = re.match(r"(mov|add)\w*? r0, (?:\w+, )?#(0x[0-9a-f]+|\d+)$", f"{i.mnemonic} {i.op_str}")
        if m and any("pop" in f"{j.mnemonic}" for j in ins[k+1:k+4]): sites.setdefault(int(m.group(2), 0), []).append(i.address)
    rows = []
    for code in sorted(K):
        idx = msg_index(code); text = msgs[idx].replace("@", " ") if 0 <= idx < len(msgs) and idx != code else ""
        if code == 0: idx, text = 1, msgs[1].replace("@", " ")
        who, trig, src, status, note = K[code]
        base = max([b for b in sites if b <= code and code - b <= 5] or [-1])
        addr = "" if status in (NO,) and code not in (201,) or code in (-1, 0) or code >= 500 else ", ".join(f"0x{a:08X}" for a in sites.get(code, sites.get(base, [])))
        shown = {600: 2, 601: 4, 602: 8, 603: 16}.get(code, code)     # party-level conditions are logged as a bitmask
        rows.append([code, idx if text else "", text, who, trig, src, status, addr, shown, note])
    with open(os.path.join(out, "error_codes.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["code", "message_index", "message_text_english", "decided_by", "trigger_condition", "data_source", "status", "code_address_bw2_build", "value_shown_in_log_viewer", "notes"]); w.writerows(rows)
    print(f"wrote {len(rows)} codes to {out}/error_codes.csv; messages: {len(msgs)}")
    unmapped = [r[0] for r in rows if not r[2] and r[0] not in (-1,)]
    print("codes without a message from the app's routine:", unmapped)

if __name__ == "__main__":
    main()
