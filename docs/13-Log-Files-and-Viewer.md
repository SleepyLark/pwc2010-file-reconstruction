# 13. Log Files and the Log Viewer

The Rule Check Tool leaves a record of every check on the SD card, and a separate **Log Viewer** app displays it.
This page documents the file format, what the viewer shows, and **how the red numbers relate to the error codes**.

> **Key point for anyone reading old logs:** the **number beside a Pokémon is its error code**, but the number
> shown for the **whole team is a bitmask** (2, 4, 8, 16 or a sum), *not* a 600-series code. See
> [The party-level value](#the-party-level-value-is-a-bitmask).

## The pipeline (observed)

```
Rule Check Tool ──appends one 0x234-byte record per run──►  sdmc:logTYYMMDD.dat   (Party)
                                                            sdmc:logBYYMMDD.dat   (Battle Box)
Log Viewer      ◄──reads those two files (sdmc:logT%02d%02d%02d.dat, sdmc:logB%02d%02d%02d.dat)
```

* `YYMMDD` is the date from the DSi's clock when the check ran (`logT261004.dat` = 2026-10-04).
* **When a record is written:** after the result screen, when the user presses **A** (inferred from a key-register
  test), and only for a check that `regulation.cfg` enables: `cfg[1]` for the Battle Box log, `cfg[0]` for the Party
  log. It is **not** controlled by `cfg[0x0C]`, which governs the separate `livematch` file.
* **`livematchYYMMDD.dat` is a different file** (a separate output of the Rule Check Tool, 90-byte records). **The Log
  Viewer does not read it.** An earlier version of these notes assumed it did; the viewer's own path strings show
  otherwise.
* The writer also builds a third filename pattern, `sdmc:logYYMMDD.dat`, for any selector other than 0 or 1. It is
  not used by the two callers that exist, so its purpose is unknown.

| Program | Title ID | Notes |
|---|---|---|
| Rule Check Tool (writes logs) | `000300044b394841` (BW2), `0003000434534e41` (BW) | log writer at `0x0200AED0` (BW2) |
| **Log Viewer** | `0003000434534e42` | ~1 MB image; NitroFS holds only a `dummy.txt`; **no message table**, no species or move names |

## Record layout (verified)

A log file is a sequence of **0x234-byte (564-byte) records**; the tool **appends** one per run. The record id counts
up from 1, so a day's file holds as many records as checks were run that day (two runs → ids 1 and 2).

```
record (0x234) = header (0x24)  +  6 × entry (0x58)        0x24 + 6 × 0x58 = 0x234
```

### Header (0x24 bytes)

| Offset | Size | Field | Notes |
|---|---|---|---|
| `0x00` | u32 | **Record id** | existing records in the file + 1 (`file_size ÷ 0x234 + 1`) |
| `0x04` | u32 | **Number of Pokémon** | 6 in a full party; 2 in the sample Battle Box |
| `0x08` | 16 B | **Player name** | UTF-16LE, 8 characters |
| `0x18` | u32 | Number drawn in white on the right of the viewer | taken from save block `0x1B` + `0x18`; 0 in the sample logs |
| `0x1C` | 2 B | *uninitialised memory* | identical in every record of the sample, but not written by the tool |
| `0x1E` | u8 | **Party-level flag** | low byte of the value at `0x20`; 0 when there is no party-level problem |
| `0x20` | u32 | **Party-level bitmask** | see below |

### Entry (0x58 bytes, six per record)

Each field's *source* is the game-record field the writer reads (`0x0200D780`/`0x0200D828` getter IDs, from the
function at `0x0200A9A4`).

| Offset | Type | Field | Source (getter ID) | Notes |
|---|---|---|---|---|
| `0x00` | 11 × u16 | Nickname | `0x74` | UTF-16LE |
| `0x16` | u16 | Species | `5` | 0 = empty slot |
| `0x18` | u16 | Level | `0x9F` | |
| `0x1A` | u8 | Gender | `0x6E` | 0 male, 1 female, 2 genderless |
| `0x1B` | u8 | Nature | `0x70` | |
| `0x1C` | u8 | Friendship | `9` | |
| `0x1D` | u8 | Event/fateful flag | `0x6D` | the same flag code 33 tests |
| `0x1E` | u8 | Ball | `0x99` | |
| `0x1F` | u8 | Language | `0x0C` | |
| `0x20` | 4 × u16 | Moves | `0x36`–`0x39` | |
| `0x28` | u16 | Held item | `6` | |
| `0x2A` | u8 | Ability | `0x0A` | |
| `0x2B` | u8 | Form | `0x6F` | |
| `0x2C`–`0x37` | 6 × (IV, EV) | HP, Atk, Def, Spe, SpA, SpD | IV `0x46`–`0x4B`, EV `0x0D`–`0x12` | interleaved: IV, EV, IV, EV, … |
| `0x38` | 4 × u8 | PP | `0x42`–`0x45` | |
| `0x3C` | u8 | Hidden Power type bits | computed from IV bits | |
| `0x3D` | u8 | Hidden Power power bits | computed from IV bits | |
| `0x3E` | 6 × u16 | Battle stats (HP, Atk, Def, Spe, SpA, SpD) | `0xA2`–`0xA7` | the **computed stats**, not base stats |
| `0x4A` | u8 | Origin game (version) | `0x78` | 23 = Black 2 in the sample |
| `0x4B` | u8 | Met level | `0x9A` | |
| `0x4C` | u8 | Shiny flag | computed: `(TID ⊕ SID ⊕ PID_hi ⊕ PID_lo) < 8` | |
| `0x4D` | u8 | *uninitialised* | not written | varies between Pokémon (0 and 64 in the sample) |
| `0x4E` | u16 | Egg location | `0x96` | |
| `0x50` | u16 | Met location | `0x97` | |
| `0x52` | 2 B | *uninitialised* | not written | varies between Pokémon |
| **`0x54`** | **u32** | Error code | checker result | **the red number**; 0 = no problem |

Empty slots are zero-filled. The "uninitialised" fields vary from Pokémon to Pokémon in real logs, which is why they
look like noise: the buffer is allocated without being cleared.

## The party-level value is a bitmask

The Rule Check Tool keeps one word for team-wide problems and **ORs a bit into it** for each failed rule:

| Bit | Condition | Equivalent on-screen code | Logged / shown as |
|---|---|---|---|
| `0x02` | two Pokémon of the same species | 600 | **2** |
| `0x04` | two Pokémon holding the same item | 601 | **4** |
| `0x08` | total level above the limit | 602 | **8** |
| `0x10` | fewer Pokémon than the minimum | 603 | **16** |

That word is written to the header at `0x20` (and its low byte to `0x1E`), and the viewer prints it as a decimal.
Combinations simply add up:

| Viewer shows | Meaning |
|---|---|
| 2 / 4 / 8 / 16 | one rule broken |
| 6 | same species **and** same item (600 + 601) |
| 18 | same species and too few Pokémon (600 + 603) |
| 24 | total level and too few (602 + 603) |
| 30 | all four |

The tool's own result screen shows the *message* for these (via codes 600–603); the log only keeps the bitmask.

**Confirmed on real hardware:** a Battle Box with 2 Pokémon, checked with a `regulation.bin` whose minimum is 3,
logged `0x10` in both header fields. (That confirms byte `0x0A` of `regulation.bin` on a real DSi.)

## What the Log Viewer draws (observed)

* The viewer has **no message table**, so it can only draw numbers.
* Its number routine (`0x02007594`) divides by 10 repeatedly (`0x66666667` magic constant): a plain **decimal**
  printout, in red (`0x801F`).
* For each record it draws the player/box name from `+0x08`, then, **only if the flag byte at `+0x1E` is non-zero**,
  the value at `+0x20`. (If that value were 0 it would fall back to the first non-zero entry code in the record; with
  this writer the two are set together, so that fallback is not reached.)
* Each Pokémon's `+0x54` is drawn as a number; value 0 draws nothing. The viewer has a special case for the value
  **10** (Bad Egg) whose visual effect was not decoded.
* The white number on the right is the value at `+0x18`.

So: **to learn what a red number means, use [Error Codes](08-Error-Codes)**: look the number up directly for a
Pokémon, and decode it as a sum of bits for the team.

## Real-hardware evidence

Two files from a real DSi run (`logT261004.dat`, `logB261004.dat`) were available. Each holds two records (two runs
on that day). The files used were the configuration files generated by this project (`regulation.cfg` enabling the
Party, Battle Box and logging; `regulation.bin` with minimum team size 3; `rule_bw2.prd`).

| Pokémon (from the log) | DSi logged | Meaning |
|---|---|---|
| 5 ordinary Pokémon (Zorua, Joltik, Servine, Magneton, Unfezant) | **0** | no problem |
| Mewtwo Lv 50, one move | **31** | can't be obtained at this level |
| Magikarp Lv 1 with Pound | **150** | knows a move it can't learn (slot 1) |
| Palkia Lv 100 (Cherish Ball, met location 40001) | **212** | not in the species' allowed-location list |
| Dialga Lv 100 (same) | **212** | same |
| Battle Box with 2 Pokémon | party-level **16** | fewer Pokémon than the minimum |

### Cross-validation against the emulator

Every Pokémon in the logs was rebuilt from its entry and run through the **emulated** checker
(`tools/crossvalidate_logs.py`):

| Table loaded in the emulator | Agreement with the DSi |
|---|---|
| **`rule_bw2.prd`** | **16 / 16** |
| `rule_bw.prd` or the table compiled into the app | 14 / 16, disagreeing on Dialga (160 vs the logged 212) |

Dialga knows **Draco Meteor**, a Black 2 / White 2 move-tutor move. The older table treats it as an older-game-only
move (160); the BW2 table treats it as native, and the DSi's verdict matches the BW2 table. This is hardware
confirmation of the BW2 tutor reconstruction (see [Rebuilding rule.prd](07-Rebuilding-rule-prd)), as well as of the
config files loading, the minimum-level rule (31), the location-list rule (212) and `regulation.bin`'s minimum count.

**What it does not cover:** the logged Pokémon were the user's own, not the synthetic test files; a banned-species
(500), banned-item (501), level-rule (502), duplicate (600/601) or total-level (602) failure has not been seen on
hardware; the cartridge gate and Hidden Ability code 62 were not exercised.

## Tools

```bash
# decode logs, with codes translated to messages (names optional)
python3 tools/read_logs.py logT261004.dat logB261004.dat --names-csv POKEAPI_CSV
python3 tools/read_logs.py logT261004.dat --csv out.csv --anonymize

# replay a real DSi log through the emulated checker
python3 tools/crossvalidate_logs.py BW2.app POKEAPI_CSV data/generated/rule_bw2.prd \
        testcases/hardware_logs/sample_logT261004.dat testcases/hardware_logs/sample_logB261004.dat
```

`read_logs.py --sanitize-to DIR` writes a shareable copy with the player name, nicknames and uninitialised bytes
removed. **Raw logs contain the player's name and Pokémon nicknames**, so share only sanitized copies;
`testcases/hardware_logs/` holds the sanitized sample.

