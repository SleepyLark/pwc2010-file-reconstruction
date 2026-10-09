# 9. Test Cases

`testcases/bw2_illegal_party/` contains **26 synthetic Gen-5 Pokémon** (`.pk5`, 136-byte stored format) designed to
trigger specific error codes, plus `manifest.csv` listing each file's expected code. Every expected code was
reproduced by running the app's own checker in an emulator, on **both** the 136-byte stored path (Battle Box) and
the 220-byte party path (Party).

```
party/       six files = one illegal party, each Pokémon wrong in a different way
extended/    the control + 19 further single-problem cases
manifest.csv file, what is wrong, level the app computed, expected code, emulated results
```

## The illegal party (`party/`)

| Slot file | What is wrong | Code | Message |
|---|---|---|---|
| `slot1_ivysaur_lv10` | Ivysaur at Lv 10 (it evolves at 16) | **31** | This Pokémon can't be obtained at this level. |
| `slot2_mew_no_flag` | Mew without the event flag | **33** | Limited distribution Pokémon, but flag isn't set. |
| `slot3_pikachu_hyperbeam` | Hyper Beam in slot 2 | **151** | Illegal Pokémon: Knows a move that it can't learn. |
| `slot4_pikachu_dupe_move` | Thunderbolt twice (slots 1 and 2) | **131** | Illegal Pokémon: It has two of the same move. |
| `slot5_pikachu_bad_ball` | Ball ID 26 | **50** | Illegal Pokémon is in a ball it shouldn't be in. |
| `slot6_charizard_sky_drop` | Knows Sky Drop | **170** | This Pokémon knows Sky Drop. Change this move. |

## Extended cases (`extended/`)

`control_legal_pikachu` must return **0**. The others cover: empty first move slot (140), gap in move slots (141),
duplicate in slot 3 (132), Pikachu + Sky Drop (**150**, because it can never learn it), move ID 600 (120), EVs
255×6 (90), nature 40 (200), invalid form (32), held item 700 (61), species 0 (20), **two kinds of Bad Egg** (10),
Mewtwo below its minimum level (31), an older-game-only move (160), an egg move without hatching (180), an XD move plus
an egg move (190), a distribution move plus an egg move (191), a hatched Unown in the wrong place (211), and an
Articuno caught at a forbidden location (212). Details are in `manifest.csv`.

Codes **62** (Hidden Ability) and the 500–603 regulation codes depend on which table/`regulation.bin` is loaded, so
they have no fixed file: see the notes below.

## Design rules for the cases

1. **One problem per Pokémon.** Everything else about the Pokémon is legal, so the expected code is unambiguous.
2. **Use a legal control.** `control_legal_pikachu` proves the harness can return 0; without it a "pass" could be an
   accident.
3. **Check the record decodes as intended.** The builder is validated through the app's own getter (see
   [Methodology](02-Methodology)).
4. **Remember the evaluation order.** A case only shows its code if no earlier check fails
   ([Error Codes](08-Error-Codes)). That is why the Sky Drop case uses Charizard, a species the table lets learn
   Sky Drop: Pikachu would stop at 150.

## Getting the Pokémon into a save

The tool reads the **cartridge's save data**, so the files must be placed in a Black 2 / White 2 save (a PKHeX-style
editor can import `.pk5` into party or box slots, then write the save back to the cartridge or a flash-cart save).
**This step has not been verified for these files**; the real-DSi run used the user's own Pokémon. Notes:

* Metadata used by the cases: origin game White 2 (22), met location 10 (passes the location check), Poké Ball ID 4.
* A save editor may "fix" some invalid values on import (in the real log, a Mewtwo that had been built for met location 10 and White 2 appeared with met location 14 and origin Black 2). Check each Pokémon after importing.
* Cases 190, 191 need met location **30001** (Poké Transfer); case 211 needs an egg location; these are set in the files.

## Using other tables

```bash
# verify against the table compiled into the app (default)
python3 tools/make_testcase.py BW2.app --out testcases/bw2_illegal_party
# verify against a generated table
python3 tools/make_testcase.py BW2.app --prd data/generated/rule_bw2.prd --out /tmp/check
```

Both runs print `ALL EXPECTED CODES CONFIRMED` for the shipped case list (also confirmed for `rule_bw.prd`).

### Hidden Ability (code 62)

Under the template flags (`rule_bw.prd`), a Pikachu with Lightning Rod returns **62**; under `rule_bw2.prd`
(Hidden Abilities allowed) the same Pokémon passes. `tools/verify_error_codes.py` demonstrates the 62 case against
`rule_bw.prd`.

## Hardware results so far

One real DSi run is available (see [Log Files and Viewer](13-Log-Files-and-Viewer)). It used the project's
generated `regulation.cfg`, `regulation.bin` (minimum team size 3) and `rule_bw2.prd`, but **the user's own Pokémon,
not the synthetic `.pk5` files**, so the test files themselves have not yet been confirmed. What the run did confirm:

| Check | Result on the DSi |
|---|---|
| The three files load and drive a check; Party and Battle Box both checked; logging works | **Confirmed** (`logT` and `logB` were written) |
| Minimum level rule (code 31) | **Confirmed**: Mewtwo Lv 50 → 31 |
| Learnable-move rule (code 150) | **Confirmed**: Magikarp Lv 1 with Pound → 150 |
| Allowed-location list (code 212) | **Confirmed**: Palkia and Dialga → 212 |
| BW2 tutor moves treated as native | **Confirmed**: Dialga (Draco Meteor) did **not** get 160 |
| `regulation.bin` minimum count (byte `0x0A`) | **Confirmed**: 2 Pokémon vs minimum 3 → team value 16 |
| Emulator vs hardware | **16 / 16 Pokémon agree** with `rule_bw2.prd` |

## Remaining hardware test plan

| # | Setup | Expected | If it differs |
|---|---|---|---|
| 1 | Import the six `party/` Pokémon into a Black 2 / White 2 save and check the party | Red codes 31, 33, 151, 131, 50, 170 | The test files did not survive import: re-inspect each Pokémon; otherwise the table is wrong |
| 2 | The control Pokémon in a slot | That slot is clean | Environment or save-import problem |
| 3 | `regulation.bin` banning species 25, with the control Pokémon | Code **500** on the control only | The `0x12` species bitmap offset is wrong |
| 4 | Two Pokémon of the same species and no `0x10` clause byte | Team value **2** in the viewer | The duplicate-species bit or byte `0x10` is wrong |
| 5 | A Pokémon with a Hidden Ability under `rule_bw.prd` | Code **62** | Flag `0x0400` semantics are wrong |
