# 5. `regulation.bin`

The **tournament's rulebook**: which species and items are banned, level limits, and whether duplicates are allowed.
It is read whole into memory and used through a family of tiny accessor functions, so its layout can be read
directly from those functions. **Every accessor below was run in an emulator against a generated file**
(`tools/verify_regulation.py`) and behaved as described.

## Field map

| Offset | Size | Meaning | Used by | Failure code |
|---|---|---|---|---|
| `0x00`–`0x09` | 10 | *never read* (name/ID/version? unknown) | | |
| `0x0A` | u8 | **Minimum number of Pokémon.** OK if `count >= byte` | `0x0200A870` | 603 |
| `0x0B` | u8 | *never read* | | |
| `0x0C` | u8 | **Level threshold** | `0x0200A884` | 502 |
| `0x0D` | u8 | **Level rule mode:** `0` none · `1` level ≥ threshold · `2` level ≤ threshold | `0x0200A884` | 502 |
| `0x0E` | u16 LE | **Total-level cap** over the whole team; `0` = unlimited | `0x0200A8DC` | 602 |
| `0x10` | u8 | **Allow duplicate species:** non-zero skips the duplicate-species test | `0x0200A8FC` | 600 |
| `0x11` | u8 | **Allow duplicate items:** non-zero skips the duplicate-item test | `0x0200A904` | 601 |
| `0x12`–`0x63` | 82 B | **Banned-species bitmap.** Bit *n* set = species *n* banned (`byte[0x12 + n>>3] >> (n&7)`) | `0x0200A90C` | 500 |
| `0x64`–`0xB3` | 80 B | **Banned-item bitmap.** Bit *n* set = item *n* banned | `0x0200A934` | 501 |

* Bitmaps are indexed by the number directly (bit 0 is unused), unlike the `rule.prd` item whitelist, which uses
  `itemID − 1`.
* The file is read with **no length check**. A file shorter than `0xB4` bytes would make the item bitmap read past
  the buffer, so the generator writes **180 bytes (`0xB4`)**. That size is my choice (80 bytes covers item IDs up to
  639); the true original size is unknown.
* Inferred (consistent with the message text, not run on hardware): "set bit = banned" because the accessor's
  non-zero result produces message 38/39 ("can't be used", "unusable item").

## When these rules are applied

The init routine applies them **only to Pokémon that passed every `rule.prd` check** (code 0). So a banned Pokémon
that also has an illegal move shows the move's code first. Codes 500–502 are per-Pokémon; 600–603 are party-wide
(stored in separate slots of the result structure).

## Duplicate checks (observed)

* Species: the six species numbers are compared pairwise; empty slots hold `650` (`0x28A`) and are ignored.
* Items: compared pairwise; "no item" is ignored.
* Both are skipped when the corresponding byte (`0x10` / `0x11`) is non-zero.

## Generating a file

```bash
python3 tools/pwc2010_tool.py make-reg regulation.bin \
    --min-count 3 --level-mode 2 --level 50 --total-level 0 \
    --ban-species 150,151,493 --ban-items 1,2
python3 tools/verify_regulation.py APP.app regulation.bin     # emulated accessor checks
```

Species/item numbers are the **in-game** numbers (national dex for species; the game's item ID for items).

## Example: 2013 VGC-style rules (Double Battle, Lv 50)

Roughly: `--level-mode 2 --level 50` (Lv ≤ 50 after the game's own Lv-50 cap; note that VGC *reduces* higher levels
rather than rejecting them, so you may prefer `--level-mode 0`), `--min-count 4`, no duplicate species or items
(leave bytes `0x10`/`0x11` zero), and the banned species from the rules text (Mewtwo, Mew, Lugia, Ho-Oh, Celebi,
Kyogre, Groudon, Rayquaza, Jirachi, Deoxys, Dialga, Palkia, Giratina, Phione, Manaphy, Darkrai, Shaymin, Arceus,
Victini, Reshiram, Zekrom, Kyurem, Keldeo, Meloetta, Genesect). *This is a suggested starting point; the original
tournament file was not available to compare.*

Ready-to-run command for that banned list (national dex numbers: Mewtwo 150, Mew 151, Lugia 249, Ho-Oh 250,
Celebi 251, Kyogre 382, Groudon 383, Rayquaza 384, Jirachi 385, Deoxys 386, Dialga 483, Palkia 484, Giratina 487,
Phione 489, Manaphy 490, Darkrai 491, Shaymin 492, Arceus 493, Victini 494, Reshiram 643, Zekrom 644, Kyurem 646,
Keldeo 647, Meloetta 648, Genesect 649):

```bash
python3 tools/pwc2010_tool.py make-reg regulation.bin --min-count 4 --level-mode 0 \
  --ban-species 150,151,249,250,251,382,383,384,385,386,483,484,487,489,490,491,492,493,494,643,644,646,647,648,649
```

Sky Drop and Dark Void are **not** handled here; they are move rules (see [Rebuilding rule.prd](07-Rebuilding-rule-prd)).
