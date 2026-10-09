# 7. Rebuilding `rule.prd` from PokeAPI

## Approach

The original table is a deterministic function of game data, so the question is: *which PokeAPI sets reproduce each
bit?* Instead of guessing, each bit was **correlated against every (version-group × method) set** using the table
compiled into the app as ground truth, and the definition with the best match was kept.

Move data comes from `pokemon_moves.csv` (method 1 = level-up, 2 = egg, 3 = tutor, 4 = machine; version groups
5–10 = RS, E, FRLG, DP, Pt, HGSS; 11 = BW; 12/13 = Colosseum/XD; 14 = B2W2).

## Definitions that reproduce the original

All sets are **unioned along the evolution chain** (an evolved Pokémon may know anything its pre-evolutions learned),
and alternate-form learnsets are merged into their species.

| Bit | Definition | Match to the original |
|---|---|---|
| `0x02` egg | egg moves, version groups 5–14, chain-unioned | 6,133 true positives, **2 extra, 3 missing** (99.97 %) |
| `0x01` learnable | (BW [+ B2W2 for the BW2 build] level-up/TM/tutor) ∪ (older: RS, E, FRLG, DP, Pt, HGSS **plus Colosseum/XD**) | F1 **0.9978** (149 extra, 25 missing) |
| `0x80` older-only | older set minus the target-game set minus egg moves | F1 **0.981** (82 extra, 266 missing) |

Things that were *not* guesses but findings:

* **Gen 1–2 sources are excluded.** Those games cannot transfer forward, and including them hurt the fit.
* **Colosseum/XD tutors are included.** Adding vg 12/13 dropped bit-0 misses from 157 to 25. (Nightmare and
  Self-Destruct, both XD tutor moves, were the largest groups.)
* **Shedinja inherits Ninjask's moves** (it is created during Nincada→Ninjask evolution).
* **Species with alternate forms use the union of their forms' learnsets** (Deoxys, Giratina, Shaymin, …).

The residual mismatches are almost all **event moves** (bits `0x04`/`0x10`), which PokeAPI does not contain.

## What is regenerated, and what is carried over

| Part of the file | Source in the rebuild |
|---|---|
| Move bits `0x01`, `0x02`, `0x80` for species 1–649 | **Regenerated from PokeAPI** |
| Move bits `0x04`, `0x10`, `0x40` (event / XD / sketch) | **Carried from the template**: no data source |
| Species flags | Carried from the template (`0x0400` cleared for BW2, see below) |
| Minimum level, maximum form, allowed locations | Carried from the template. A derivation from evolution data matched only 116 of 649 species, because the original is mostly 0 |
| Item whitelist (first 0x50 bytes) | Carried from the template (checked against PokeAPI: only Safari/Cherish Ball rejected) |
| Records 650–667 (forms) | Carried from the template; bans applied |

This is a **hybrid** by necessity. The honest summary is that PokeAPI can rebuild the *move* knowledge; everything
about *events and species restrictions* comes from the original table.

## Decisions (each is an option or an explicit choice)

### Sky Drop: left to the app's own check

The apps contain a dedicated Sky Drop check (mode 0 only, move 507 in any slot → **code 170 + slot**, message *"This
Pokémon knows Sky Drop. Change this move."*). An earlier version of the generator zeroed Sky Drop in the table,
which makes the app report the generic **150** ("can't learn") *before* it reaches its own check, so the dedicated
message was hidden. The generator now leaves Sky Drop's normal legality in place and lets the app ban it with the
proper message. Verified: **every** species the table lets learn Sky Drop (9 testable ones, plus Smeargle) returns 170.

### Dark Void: banned in the table

There is no dedicated check, so Dark Void is zeroed for every species (and set to `0x40` for Smeargle). It reports as
**150**. Verified exhaustively: no record anywhere treats Dark Void as legal.

### Hidden Abilities (`--hidden-abilities`)

The template sets flag `0x0400` on 645/649 species, so a **Hidden Ability returns code 62** ("can't be found with
this Ability yet"). That reflects the game's launch, before Dream World abilities. Verified: a Pikachu with Lightning
Rod is rejected under the template flags.

| Target | Default | Reason |
|---|---|---|
| `bw2` | **allow** (clears `0x0400`) | the 2013 VGC format permitted Dream World abilities |
| `bw` | **template** | matches the original BW-era behaviour |

Override with `--hidden-abilities allow|template`. "Allow" is a simplification: it also permits Hidden Abilities
that were never actually obtainable for a few species.

### Cells that differ from the original on purpose

| Move | Cells | Why |
|---|---|---|
| **Snarl** | 56 | PokeAPI lists Snarl as **TM95 in BW and BW2** (`machines.csv`), but the original table makes it illegal for every Pokémon. Treated as an omission in the original and made legal (including for Smeargle). |
| **Rock Climb** | 92 | DPPt HM available to transferred Pokémon; the original has these cells empty |
| **Dark Void** | 2 | the ban |
| other | 37 | scattered one- or two-cell differences (Reflect, Head Smash, Flash, …) |

To make the output match the original in a particular cell, edit `tools/make_rule_prd.py` or patch the file; the full
per-cell list is written by `--report`.

## Results

| Build | Cells differing from the original | Share of all 667 × 559 cells |
|---|---|---|
| **BW** (`rule_bw.prd`) | **187** | 0.05 % |
| **BW2** (`rule_bw2.prd`) | 5,831 | 1.56 %: 3,547 older-only→native + 2,276 newly legal (BW2 tutors) + 8 other |

The BW2 additions are the real Black 2 / White 2 move-tutor moves: Snore, Sleep Talk, Covet, Hyper Voice, Foul Play,
Knock Off, Uproar, Wonder Room and others.

## Validation

`tools/validate_rule_prd.py` loads a candidate table into the emulated app and runs the app's own checker on
synthetic Pokémon (species at Lv 100 with a legal ability). Species whose clean control fails (those with special
flags or location lists) are skipped.

| Table byte class | Expected | Checker returned (BW build) | (BW2 build) |
|---|---|---|---|
| no learnable bits | 150 | 2,192 × 150 | 2,172 × 150 |
| older-only (`0x80`) | 160 | 61 × 160 | 34 × 160 |
| egg-only | 180 | 31 × 180 | 31 × 180 |
| ordinary legal | 0 | 199 × 0 | 246 × 0 |

**Zero anomalies in 2,483 sampled cells per build**, plus 12 spot checks (Hyper Beam on Pikachu, Thunderbolt, HM
moves, Sky Drop on every table-legal learner, Dark Void, Smeargle's Steamroller / Chatter / Snarl, …).
`tools/make_testcase.py` was additionally run with both generated tables and all 26 test cases still pass.

## Running it

```bash
python3 tools/pwc2010_tool.py extract  BW2.app data/generated/rule_template.prd     # the template
python3 tools/make_rule_prd.py --csv-dir POKEAPI_CSV --template data/generated/rule_template.prd \
        --target bw2 --out data/generated/rule_bw2.prd --report data/generated/diff_vs_template_bw2.csv
python3 tools/validate_rule_prd.py BW2.app POKEAPI_CSV data/generated/rule_bw2.prd
```

Required PokeAPI files: `pokemon_moves`, `pokemon`, `pokemon_species`, `moves`, `experience`, `pokemon_abilities`,
`pokemon_species_names`.
