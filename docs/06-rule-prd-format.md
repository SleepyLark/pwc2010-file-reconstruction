# 6. `rule.prd` Format

`rule.prd` is **not parsed**. The loader `memcpy`s the whole file into a static buffer and the checker indexes it
in place. The format is therefore exactly the memory layout the code expects.

**Total size: `0x5E77C` = 386,940 bytes** = `0x50` + 667 × `0x244`, with no remainder. (The size was *predicted* from
the record layout and then matched the buffer constant in the loader.)

```
0x00000  +--------------------------+
         | item whitelist  (0x50 B) |   bit (itemID-1) set = item allowed
0x00050  +--------------------------+
         | record  1  (0x244 B)     |   species 1  (Bulbasaur)
         | record  2                |
         |  ...                     |
         | record 649               |   species 649 (Genesect)
         | record 650-667           |   alternate forms (see below)
0x5E77C  +--------------------------+
```

Record *N* starts at `0x50 + (N−1) × 0x244`.

## Item whitelist (bytes `0x00`–`0x4F`)

Bit `(itemID − 1)` of the 80 bytes (640 bits). The checker (BW2 `0x0200B314`) looks up the Pokémon's **held item**:

* item ID above 625 → code 61 without consulting the table
* bit **clear** → code 61 ("unobtainable held item")
* bit **set** → allowed
* extra rules in mode 0: item 225 is always rejected.

**Verified:** items with a clear bit (5, 16) returned 61, items with a set bit (1, 2) passed.
Cross-check against PokeAPI: of 223 gen-5 held items, the whitelist accepts 221 and rejects only **Safari Ball**
and **Cherish Ball**. So it looks like a deliberate tournament rule, not an omission.

## Record layout (0x244 bytes)

| Offset | Size | Field | Used for |
|---|---|---|---|
| `+0x00` | u16 | **Species flags** (table below) | codes 22, 23, 33, 51, 62, 64, 211 and Smeargle's rule |
| `+0x02` | u8 | **Minimum legal level** | code 31 |
| `+0x03` | s8 | **Maximum form number** | code 32 |
| `+0x04` | 8 × u16 | **Allowed met-location IDs**; `0` ends the list; first entry `0` = unrestricted | code 212 |
| `+0x14 + (move−1)` | 1 B per move | **Move legality byte**, move IDs 1…560 | codes 150–191 |

`0x14 + 560 = 0x244`, so the move array fills the rest of the record exactly.

### Species flags (`+0x00`)

| Bit | Observed effect | Code |
|---|---|---|
| `0x0002` | Shiny-locked: a shiny of this species is rejected | 22 |
| `0x0004` | Limited distribution: requires the event/fateful flag | 33 |
| `0x0008` | **Sketch mode** (Smeargle only; see below) | : |
| `0x0010` | Must be in an ordinary Poké Ball (ID 4) | 51 |
| `0x0020` | Hatched Pokémon must have a Poké Transfer-style met location | 211 |
| `0x0080` / `0x0100` / `0x0200` | "Ineligible" in mode 4 / 1 / 2 (never used by this tool) | 23 |
| `0x0400` | **Hidden Ability not yet obtainable** | 62 |
| `0x1000` | Hidden Ability + gender restriction | 64 |
| `0x0040`, `0x0800` | present in the table, **no effect found** | : |

In the compiled-in table `0x0400` is set on **645 of 649** species (a launch-era assumption that Dream World
abilities did not exist yet). See [Rebuilding rule.prd](07-Rebuilding-rule-prd) for how the generator handles it.

### Move legality byte

The checker takes the byte `b` for (species, move) and applies, in this order:

| Test on `b` | Meaning of the bit | Result |
|---|---|---|
| `b & 0x1F == 0` | no legal source at all | **150 + slot** |
| `b & 0x80` (modes 0–2, and not transferred) | learnable **only in an older game** | **160 + slot** |
| `b & ~0x02 == 0` and the Pokémon was **not hatched** | egg-only move | **180 + slot** |
| a move with only `0x10` **and** a move with only `0x02` | XD-only + egg-only | **190** |
| a move with only `0x04` **and** a move with only `0x02` | distribution-only + egg-only | **191** |

So the bits mean:

| Bit | Value | Meaning | Derivable from PokeAPI? |
|---|---|---|---|
| 0 | `0x01` | learnable by level-up / TM / tutor | **Yes** |
| 1 | `0x02` | egg move | **Yes** |
| 2 | `0x04` | distribution (event) move | No |
| 4 | `0x10` | XD-only move | Partly (XD/Colosseum data) |
| 6 | `0x40` | "cannot be Sketched" (Smeargle only) | table only |
| 7 | `0x80` | learnable only in an older generation | **Yes** |

Bit 3 (`0x08`) is never set in the table.

Slot numbering: `150` = move slot 1, `151` = slot 2, … `153` = slot 4. Duplicate-move codes use a different rule
(see [Error Codes](08-Error-Codes)).

### Smeargle (sketch mode)

For a species whose flag word has bit `0x0008` (only Smeargle, #235), the accessor `0x0200B2A0` returns
**"legal unless byte bit `0x40` is set"**, so any other move passes. The nine `0x40` cells in the table are Struggle,
Chatter, Techno Blast, Relic Song, Secret Sword, Freeze Shock, Ice Burn, Snarl and V-create.

**Consequence:** to ban a move for Smeargle you must set its byte to `0x40`. A byte of `0` leaves it legal. The
generator does this for Dark Void.

## Alternate-form records (650–667)

Matched to PokeAPI form learnsets by similarity (inferred):

| Records | Form |
|---|---|
| 650–652 | Deoxys Attack / Defense / Speed |
| 653–654 | Wormadam Sandy / Trash |
| 655 | Shaymin Sky |
| 656 | Giratina Origin |
| 657–661 | Rotom (five appliance forms) |
| 662–664 | **empty** (probably the Therian forms) |
| 665 | Basculin Blue-Striped |
| 666 | Darmanitan Zen |
| 667 | Meloetta Pirouette |

Their flags and minimum levels are all zero. The checker reaches them through a species/form lookup for
form-capable species; plain species use records 1–649.

## The compiled-in table

Each app contains a populated 386,940-byte table in its ARM9 image. It is **not a fallback** (see
[App Structure](03-App-Structure)), but it is the best available template: it is a real, internally consistent
`rule.prd` image whose move data PokeAPI reproduces closely. It is byte-identical between the BW and BW2 apps.
Extract it with `tools/pwc2010_tool.py extract`.
