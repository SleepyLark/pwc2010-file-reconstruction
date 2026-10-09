# 12. Open Questions

Everything here is **unknown, untested, or deliberately simplified**. Each item says how it could be resolved.

## Unverified on hardware

| Question | Why it matters | How to resolve |
|---|---|---|
| Do the generated `regulation.cfg`, `regulation.bin` and `rule.prd` work on a DSi? | **Largely yes**: one real run agrees with the emulator on 16/16 Pokémon ([details](13-Log-Files-and-Viewer)). Not yet seen on hardware: codes 500–502, 600–602 (team values 2, 4, 8), code 62, the cartridge gate | Run the [remaining hardware test plan](09-Test-Cases) |
| Does a failed cartridge gate behave as described (screen, wait for a button, exit)? | Inferred from code flow, not observed | `cfg[5] = 0` with a Japanese cartridge |
| Does a save editor preserve the test Pokémon's fields (met location 30001, egg location, event flag)? | The test case depends on those fields surviving import | Import, then re-inspect each Pokémon |
| Does the **BW1 (PWC2010)** checker behave identically to BW2? | The checker was emulated only in the BW2 build. Layout and cartridge-gate logic were confirmed identical in both builds; the BW1 checker is about 0x218 bytes smaller and was **not run** | Port the addresses (see [Tools](10-Tools-and-Reproducing)) and rerun `verify_error_codes.py` |

## About the original data

| Question | Notes |
|---|---|
| Is the table compiled into each app identical to the real tournament `rule.prd`? | Unknown. It is byte-identical across BW and BW2, which suggests a BW1-era development table. It may differ from what was distributed. |
| What is the true size and content of the original `regulation.bin`? | Bytes `0x00`–`0x09`, `0x0B`, `0x0F` are never read, and the code does no length check, so the original size cannot be derived from the app. |
| Was Snarl's exclusion in the original table intentional? | PokeAPI lists it as TM95 in BW and BW2. I treated it as an omission and made it legal. |

## Unnamed or unexplained fields

| Field | Observation |
|---|---|
| Species flags `0x0040`, `0x0800` | Set on some species (e.g. Victini `0x0CC2`; Rufflet, Braviary, Tornadus, Thundurus `0x0800`) but **no checker effect found** |
| Species flag `0x1000` | Referenced by code 64 but **set on no species** in the compiled-in table |
| Modes 1–4 | Reachable only through code paths this tool does not call. Mode 3 uses a 0x70-byte record format whose source is unknown |
| Codes **21**, **70**, **230** | Messages exist ("not distributed yet", "invalid country code", "invalid Simple Chat in held mail"), but no return site was found in the code path the BW2 tool uses; they may belong to modes 3/4 |
| Code **201** (gender) | The test exists, but toggling the stored gender and genderless bits never triggered it. Gender appears to be derived from the species and PID |
| Codes **80–85**, **100–105** | EV/IV range checks that cannot trigger on a stored record (one-byte and 5-bit fields) |
| Message 62, "Invalid number of Pokémon" | No code maps to it; purpose not confirmed |

## About the logs and the log viewer

Mostly resolved: see [Log Files and Viewer](13-Log-Files-and-Viewer). Still open:

* The 90-byte `livematch` record layout (the writer is known; the Log Viewer does not read it).
* The source of the white number at log offset `+0x18` (0 in every sample), and the purpose of the third filename
  pattern `logYYMMDD.dat`.
* The viewer's special treatment of the value **10** (Bad Egg).
* Whether the viewer behaves differently for codes 500–502 or for team values above 16 (only 16 has been seen).
* Whether the viewer shows anything for records whose party-level flag is 0 but whose Pokémon have codes (from the
  code, Pokémon numbers are drawn independently of the header).

## Simplifications in the rebuild

| Simplification | Effect | Better approach |
|---|---|---|
| Event-move bits (`0x04`, `0x10`, `0x40`) come from the template | BW2-era events are missing | Build an event-move list from a documented distribution database and set bit `0x04` for those cells |
| Hidden Abilities allowed for **all** species in the BW2 build | A few species whose Hidden Ability was never obtainable would be accepted | Derive per-species availability from Dream World data and clear `0x0400` only for those |
| Minimum levels, maximum forms, allowed-location lists copied from the template | Not updated for BW2 legendaries/events | Derive from encounter and event data |
| Item whitelist copied from the template | Matches PokeAPI's holdable items except Safari Ball and Cherish Ball (checked via PokeAPI's gen-5 item IDs, assuming they equal the in-game IDs) | Confirm on hardware with a held Safari Ball |
| Alternate-form records (650–667) carried over unchanged | Fine for ≤ 649 as requested; not regenerated | Map each to its PokeAPI form and regenerate |
| `regulation.bin` is written at 180 bytes | Size chosen to cover the item bitmap | Compare against an original if one turns up |
| Rock Climb treated as legal (92 cells) | The original has those cells empty | Decide per tournament rule and patch |

## Ideas for further work

1. Decode the livematch record and the log writers, then document the log formats alongside the error codes.
2. Replace the carried-over event bits with an independent data source.
3. Run the whole verification suite against the BW1 build.
4. Build a small standalone log reader that prints the message beside each code (the CSV already contains everything needed).
