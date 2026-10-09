# 8. Error Codes

The red number beside a Pokémon or party in the log is the **error code** produced by the Rule Check Tool. This page
lists every code, the **exact message the app shows for it**, what triggers it, and which file decides it.

*Source of truth:* message text is read from the app's own `data/message_E.dat`, and each code→message pairing is
the output of the app's own routine (ARM9 `0x020082CC`), run for every code. Nothing here was copied from a
secondary document. The machine-readable version is [`error_codes.csv`](error_codes.csv).

## How to read a code

* **One code per Pokémon.** The checker stops at the **first** failing test, so a Pokémon with several problems
  shows only the earliest one. Fix it and re-check; the next may appear.
* **Codes below 500 are per Pokémon** and come from the app's built-in logic, steered by `rule.prd`.
* **500–502 are per Pokémon**, from `regulation.bin`, and appear only on Pokémon that passed every earlier check.
* **600–603 are whole-party rules** from `regulation.bin`. **In the log and in the Log Viewer they appear as a bitmask (2, 4, 8, 16, or a sum), not as 600–603**; see below.
* **Move-slot suffix.** Codes `120`, `150`, `160`, `170`, `180` are *base + slot − 1*: `150` = slot 1, `151` = slot 2,
  `152` = slot 3, `153` = slot 4. Duplicate-move codes `131`–`133` mean *slot 2 / 3 / 4 repeats an earlier slot*.
* **`0`** means no problem was found for that Pokémon; **`-1`** marks an empty slot.

### What the Log Viewer shows

The viewer has no message table; it prints **numbers only**.

* **Beside a Pokémon:** the code from this page, exactly as listed (31, 150, 212, …).
* **For the whole team:** a **bitmask**, because the log stores the team-level problems as bits, not as 600–603:

| Viewer shows | Condition | Equivalent code |
|---|---|---|
| **2** | two Pokémon of the same species | 600 |
| **4** | two Pokémon holding the same item | 601 |
| **8** | total level above the limit | 602 |
| **16** | fewer Pokémon than the minimum | 603 |
| sums | several at once, e.g. **6** = 2 + 4, **18** = 2 + 16, **30** = all four | |

Confirmed on a real DSi: a 2-Pokémon Battle Box checked against a minimum of 3 showed **16**. Full details in
[Log Files and Viewer](13-Log-Files-and-Viewer).

### Status column

**verified** = triggered in the emulator by a constructed input; **unreachable** = the test exists in code but cannot
occur with this app's inputs; **not observed** = the message exists but no code path producing it was found;
**read-only** = seen in disassembly, not triggered. See [Methodology](02-Methodology).

## Quick lookup

| Number | Meaning in one line |
|---|---|
| 10 | Bad Egg |
| 20 | Species number out of range |
| 22 | Shiny of a shiny-locked species |
| 30 / 31 | Level outside 1–100 / below the species' minimum level |
| 32 | Invalid form |
| 33 | Event Pokémon missing its event flag |
| 50 / 51 / 52 | Bad ball / must be a Poké Ball / hatched in the wrong ball |
| 60 / 62 / 64 | Bad ability / Hidden Ability not yet available / ability–gender pairing |
| 61 | Unobtainable held item |
| 90 | Total EVs above 510 |
| 120 | Move number out of range |
| 131–133 | Same move twice |
| 140 / 141 | Empty move slot |
| 150–153 | Knows a move it can't learn |
| 160–163 | Move only learnable in an older game |
| **170–173** | **Knows Sky Drop (banned)** |
| 180–183 | Egg move, but not hatched from an egg |
| 190 / 191 | Illegal combination of event moves |
| 200 | Nature out of range |
| 210 / 211 / 212 | Bad met location (Mystery Zone / hatched in old game / not in allowed list) |
| 500 / 501 / 502 | Banned species / banned item / level rule broken |
| 600 / 601 / 602 / 603 | Duplicate species / duplicate item / total level too high / too few Pokémon. **The log viewer shows 2 / 4 / 8 / 16** |

## Per-Pokémon codes

| Code | Message shown | Cause | Decided by | Status |
|---|---|---|---|---|
| **-1** | There are no Pokémon in the party or Battle Box. | slot is empty (no Pokemon stored there) *(shown as 'no Pokemon' only when no slot holds a Pokemon (inference))* | init | read-only |
| **0** | OK | no problem found for this Pokemon | - | verified |
| **10** | There is a Bad Egg in the party or the Battle Box. | Bad Egg: the Bad Egg flag (sanity word bit 2) is set, or the stored checksum does not match the data | checker | verified |
| **20** | Invalid Pokémon: Pokémon No. value is out of range. | species number is 0 or above 649 | checker | verified |
| **21** | This Pokémon hasn't been distributed yet. | message exists; no return site found in the BW2 code path | ? | not observed |
| **22** | There is no shiny version of this Pokémon. | species is shiny-locked (flag 0x0002) and the Pokemon is shiny | rule.prd | verified |
| **23** | Ineligible Pokémon. | species flag 0x80 (mode 4) / 0x100 (mode 1) / 0x200 (mode 2). The BW2 tool always uses mode 0, so never evaluated *(semantics verified by calling the checker with mode 1)* | rule.prd | unreachable |
| **30** | Level outside of 1 to 100. | level is not in 1..100 (mode != 4) *(tested via a party-form record with level 0 and 101)* | checker | verified |
| **31** | This Pokémon can't be obtained at this level. | level is below the species' minimum legal level (record+2) | rule.prd | verified |
| **32** | This Pokémon's form No. is invalid. | form number is above the species' maximum form (record+3, signed) | rule.prd | verified |
| **33** | Limited distribution Pokémon, but flag isn't set. | species flag 0x0004 (limited distribution) and the event/fateful flag is not set | rule.prd | verified |
| **50** | Illegal Pokémon is in a ball it shouldn't be in. | ball ID is outside 1..25 | checker | verified |
| **51** | This Pokémon must be in an ordinary Poké Ball. | species flag 0x0010 requires an ordinary Poke Ball (ID 4) and the ball is different | rule.prd | verified |
| **52** | Pokémon hatched from an Egg must be in a Poké Ball. | egg location is set (hatched) and the ball is not a Poke Ball (ID 4) | checker | verified |
| **60** | Pokémon has illegal Ability | ability is not one of the species' abilities (with exceptions for a few form species) | checker | verified |
| **61** | This Pokémon's has an unobtainable held item. | held item ID above 625, or the item's bit is clear in rule.prd's 80-byte item whitelist (mode 0 also rejects item 225) | rule.prd | verified |
| **62** | This Pokémon can't be found with this Ability yet. | species flag 0x0400 and the ability is the species' Hidden Ability *(the BW1-era template sets 0x0400 on 645/649 species; rule_bw2.prd clears it by default)* | rule.prd | verified |
| **64** | Illegal Ability/gender pairing for this Pokémon. | species flag 0x1000 with Hidden Ability and gender field 0x6E non-zero *(no species carries flag 0x1000 in the compiled-in table)* | rule.prd | unreachable |
| **70** | Invalid country code. | message exists; no return site found in the BW2 code path | ? | not observed |
| **80–85** | Illegal Pokémon: Value for EV parameter exceeds 255 | an EV value is above 255 (one code per stat) *(EV is stored in one byte, so a stored record cannot exceed 255)* | checker | unreachable |
| **90** | Illegal Pokémon: Total EV value exceeds 510. | total EVs above 510 | checker | verified |
| **100–105** | Illegal Pokémon: Power's random value out of range | an IV ('Power's random value') is out of range (one code per stat) *(IV is stored in 5 bits, so a stored record cannot exceed 31)* | checker | unreachable |
| **120–123** | Illegal Pokémon: Move No. value exceeds range. | move ID in slot N (120 = slot 1) is above 560 *(verified for slot 1)* | checker | verified |
| **131–133** | Illegal Pokémon: It has two of the same move. | a move repeats an earlier slot: 131 = slot 2, 132 = slot 3, 133 = slot 4 | checker | verified |
| **140** | Illegal Pokémon: First move slot is empty. | move slot 1 is empty | checker | verified |
| **141** | Illegal Pokémon: Second or third move slot is empty. | an empty move slot is followed by a filled one | checker | verified |
| **150–153** | Illegal Pokémon: Knows a move that it can't learn. | the move in slot N (150 = slot 1) has no legal-source bit (0x01..0x10) for this species *(verified for all four slots)* | rule.prd | verified |
| **160–163** | Illegal: BW Pokémon has moves only in old version. | slot N has an older-game-only move (byte bit 0x80) on a Pokemon that did not come through Poke Transfer (modes 0-2) *(verified for slot 1)* | rule.prd | verified |
| **170–173** | This Pokémon knows Sky Drop. Change this move. | slot N (170 = slot 1) holds Sky Drop (move 507). Mode 0 only; evaluated after the learnability checks *(only reached if the table says the species can learn Sky Drop; otherwise 150)* | checker | verified |
| **180–183** | Illegal Pokémon: Knows Egg Moves, but not from Egg. | slot N has an egg-only move (byte bit 0x02, no other source) and the Pokemon was not hatched (egg location = 0) *(verified for slot 1)* | rule.prd | verified |
| **190** | Illegal: Combination of moves unlearnable (XD). | an XD-only move (byte bit 0x10) together with an egg-only move *(only for transferred Pokemon (met location 30001), otherwise 160 fires first)* | rule.prd | verified |
| **191** | Illegal: Combination of moves unlearnable (Dist.). | a distribution-only move (byte bit 0x04) together with an egg-only move *(only for transferred Pokemon (met location 30001), otherwise 160 fires first)* | rule.prd | verified |
| **200** | Illegal Pokémon: Nature value exceeds range. | nature value above 25 | checker | verified |
| **201** | Illegal Pokémon: Gender value exceeds range. | gender does not match the species' gender ratio *(toggling the stored gender/genderless bits never triggered it; gender appears to be derived)* | checker | not observed |
| **210** | Illegal Pokémon: Hatched or caught in Mystery Zone. | met location is non-zero but not a valid location ID ('Mystery Zone') | checker | verified |
| **211** | Ltd. Pokémon in old game. Poké Transit not used. NG. | species flag 0x0020, egg location set, and met location not in {30001, 30010-30013, 30014, 73} | rule.prd | verified |
| **212** | Illegal Pokémon: Invalid birthplace or place caught. | species has an allowed-location list (record+4, up to 8 x u16) and the met location is not in it | rule.prd | verified |
| **230** | Illegal Pokémon: Invalid Simple Chat in held mail. | message exists; no return site found in the BW2 code path | ? | not observed |

## Regulation codes (`regulation.bin`)

| Code | Message shown | Cause | Decided by | Status |
|---|---|---|---|---|
| **500** | This Pokémon can't be used so please change Pokémon. | species bit set in the banned-species bitmap (bytes 0x12-0x63) *(accessor verified in emulator; only evaluated if the Pokemon passed every rule.prd check)* | regulation.bin | verified |
| **501** | Holding an unusable item, please change items. | held item bit set in the banned-item bitmap (bytes 0x64-0xB3) *(accessor verified in emulator)* | regulation.bin | verified |
| **502** | Lv violates tournament rules. Change Pokémon. | level rule: mode (byte 0x0D) 1 = level must be >= byte 0x0C, mode 2 = level must be <= byte 0x0C *(accessor verified in emulator)* | regulation.bin | verified |
| **600** | Can't have two of the same Pokémon. Change Pokémon. | two Pokemon of the same species (skipped when byte 0x10 is non-zero) *(party/box-wide; accessor verified)* **(log viewer shows 2)** | regulation.bin | verified |
| **601** | Another Pokémon has the same item. Change items. | two Pokemon holding the same item (skipped when byte 0x11 is non-zero) *(party/box-wide; accessor verified)* **(log viewer shows 4)** | regulation.bin | verified |
| **602** | Total Lv exceeds regulation Please change Pokémon. | sum of levels above the cap (u16 at 0x0E; 0 = no cap) *(party/box-wide; accessor verified)* **(log viewer shows 8)** | regulation.bin | verified |
| **603** | Check number of Pokémon. Too few for the battle. | fewer Pokemon than the minimum (byte 0x0A) *(party/box-wide; accessor verified)* **(log viewer shows 16)** | regulation.bin | verified |

## Messages that are not error codes

| Index | Text | Where it appears |
|---|---|---|
| 44 | Pokémon Black or White 2 is not the inserted cartridge. | Cartridge gate failed |
| 45 | No problems were found in any of the checks. | All clear screen |
| 46–49 | Save Pokémon data to this SD card? / saved / Yes / No | Save prompt |
| 50–61 | Result-screen titles and button labels | UI |
| 62 | Invalid number of Pokémon. | purpose not confirmed |
| 64 | The SD card could not be saved. | Save error |

## Order in which the checks run

The checker (BW2 `0x0200B430`) evaluates in this order; the first failure wins. Addresses are the return sites.

| Order | Code | Address | Order | Code | Address |
|---|---|---|---|---|---|
| 1 | 10 Bad Egg | `0x0200B464` | 15 | 150+ can't learn | `0x0200BBEC` |
| 2 | 20 species | `0x0200B4B4` | 16 | 160+ older-only | `0x0200BCA0` |
| 3 | 22 shiny-locked | `0x0200B514` | 17 | 180+ egg move | `0x0200BCD0` |
| 4 | 30 level range | `0x0200B598` | 18 | 190 / 191 combos | `0x0200BD38` / `BD88` |
| 5 | 31 min level | `0x0200B5CC` | 19 | 210 location | `0x0200BDD4` |
| 6 | 33 event flag | `0x0200B608` | 20 | 212 location list | `0x0200BE34` |
| 7 | 50 ball range | `0x0200B63C` | 21 | 211 hatched/transfer | `0x0200BEA8` |
| 8 | 51 ordinary ball | `0x0200B698` | 22 | 32 form | `0x0200BED8` |
| 9 | 52 hatched ball | `0x0200B6B0` | 23 | 80–85 EV per stat | `0x0200BF0C`… |
| 10 | 60 ability | `0x0200B780` | 24 | 90 EV total | `0x0200C09C` |
| 11 | 61 item | `0x0200B7B8`… | 25 | 100–105 IV | `0x0200C0D0`… |
| 12 | 120+ move range | `0x0200B880` | 26 | 62 / 64 hidden ability | `0x0200C218` / `C284` |
| 13 | 131–133 duplicate | `0x0200B8BC` | 27 | **170+ Sky Drop** | `0x0200C2FC` |
| 14 | 140 / 141 empty slot | `0x0200B8EC` / `B918` | 28 | 200 nature, 201 gender | `0x0200C328`, `0x0200C364`… |

Practical consequences: a Pokémon with Sky Drop **and** an unlearnable move shows 150, not 170; a Hidden Ability
problem (62) is only seen after every move check has passed; Sky Drop is only reached if the table says the species
can learn it, otherwise 150.

## Reproducing this page

```bash
python3 tools/build_error_table.py BW2.app docs          # regenerates error_codes.csv and message_bank_E.txt
python3 tools/verify_error_codes.py BW2.app POKEAPI_CSV data/generated/rule_bw.prd --out docs/verification_rule_bw.csv
python3 tools/verify_regulation.py  BW2.app data/generated/regulation.bin
python3 tools/read_logs.py logT261004.dat logB261004.dat      # decode real logs, codes translated to messages
```

(`rule_bw.prd` is used for verification because it keeps the Hidden-Ability flag that code 62 depends on.)
