# 11. Corrections and Lessons

An honest log of things that were **wrong at some point** during this project, how each was caught, and what replaced
it. Several earlier statements in the project's chat history are superseded by this page, so it is worth reading
before relying on any older summary.

## Findings that were wrong, and their fixes

| # | What I believed / did | How it was caught | Correct finding |
|---|---|---|---|
| 1 | The 80-byte header of `rule.prd` is a *species* bitmap with "no bounds check" past species 640. | Tracing who calls the bitmap function: it is passed the **held item ID**. Then tested: clear bit → code 61, set bit → pass. | It is a **held-item whitelist** indexed by `itemID − 1`. |
| 2 | Record `+2` is a `u16` minimum level. | Reading the checker: `+2` is a signed *byte* read and `+3` is a separate byte used for forms. Test: Pikachu form 5 → code 32. | `+2` = u8 minimum level, `+3` = s8 maximum form. |
| 3 | A "Victini Lv 15 still returns 31" result looked like it contradicted the min-level theory. | I had used the wrong growth curve, so the Pokémon was really below level 15. | With correct levels the tool raises 31 exactly below each species' minimum (Ivysaur 16, Venusaur 32, Victini 15): the theory was **confirmed**. |
| 4 | The original table globally excludes Snarl, Rock Climb and Flash, so I added an `--original-exclusions` option. | The option made the output *less* like the original (361 vs 194 differing cells). Breaking diffs down by move showed the original has Flash legal in 279 cells and Rock Climb in 36. | Option **removed**. Only Snarl is excluded for (almost) every species; Rock Climb and Flash differ in specific cells. |
| 5 | Banning a move = writing a zero byte. | The validator found Smeargle accepting Steamroller (and would have accepted Dark Void). Reading accessor `0x0200B2A0`: for flag-`0x08` species the byte is read as "legal unless bit `0x40`". | Bans must be `0x40` for Smeargle. Fixed and checked exhaustively. |
| 6 | Zeroing Sky Drop in `rule.prd` is the right way to ban it. | Mapping every code to its message showed code 170 = *"This Pokémon knows Sky Drop. Change this move."*, and reading the code showed a dedicated check (mode 0) that runs *after* the table lookup. | Leave Sky Drop's legality in the table so the app's own check reports 170. Zeroing replaced it with the generic 150. |
| 7 | "Corrupt checksum → Bad Egg (10)". | The same construction returned 10 for one Pokémon and garbage for another. My builder encrypted with the *true* checksum and then overwrote the stored one, so the app decrypted noise. | Two reliable triggers: a checksum mismatch where data is encrypted with the *stored* value, and the Bad Egg flag (sanity word bit 2). The old construction is deprecated in `pk5.py`. |
| 8 | `regulation.bin` accessor addresses were the BW1 ones plus `0x28`. | The first emulation run returned the pointer I passed in. The real shift is **+0x2C**. The min-count accessor had "worked" only because `0x0200A86C` is a literal-pool word that executes harmlessly. | Addresses corrected; all accessors now verified. |
| 9 | Form records 662–664 were Keldeo. | Learnset matching showed they have no moves at all. | Probably the Therian forms (empty in this table). |
| 10 | Pidgeot is a Sky Drop learner (spot check). | The check returned 150, not 170. The table says Pidgeot cannot learn it. | The validator now picks learners from the table and tests **every** one. |
| 11 | "Mewtwo Lv 50" test case. | The tool reported Lv 45. Mewtwo's growth curve is "slow", not "medium slow". | Experience formula corrected; label matches the tool's computed level. |
| 12 | An early community note called `cfg[5]` "Slot-1 access". | Emulating the cartridge-gate routine over every game code. | It is one of seven **per-cartridge accept flags**. |
| 13 | `r5` in the init loops is the slot index. | The loop jumps back to a point *after* `mov r5, sb`. | `r5` is the constant mode 0. |
| 14 | Hidden Abilities are fine in the generated table. | Verifier case for code 62: Pikachu with Lightning Rod was rejected. | Flag `0x0400` is set on 645 species in the template; the BW2 build now clears it by default (an explicit option). |

## Corrections from the Log Viewer and the real-DSi logs

| # | What I believed | How it was caught | Correct finding |
|---|---|---|---|
| 15 | The Log Viewer reads the `livematch` files. | The viewer's own path strings are `sdmc:logB%02d%02d%02d.dat` and `sdmc:logT…`. | The viewer reads **`logT`/`logB`**. `livematch` is a different file it does not read. |
| 16 | The team-level red number is a 600-series code. | A real log held **16** in the header (a 2-Pokémon box, minimum 3), and the init routine ORs bits into the value. | It is a **bitmask** (2 / 4 / 8 / 16). Only per-Pokémon numbers equal the error codes. |
| 17 | The viewer maps codes to messages. | It has no message table and prints decimals (`0x66666667` division). | Numbers only; users need the [Error Codes](08-Error-Codes) page. |
| 18 | The community log struct's names (`distribution_form`, `country`, `*base`, `rom`, `heart`, `get_place`) describe the data. | Compared with the source field IDs in the Rule Check Tool's log writer. | Event flag, language, **computed stats** (not base stats), origin version, **shiny flag**, egg location / met location. |
| 19 | The "unknown" log bytes hold unknown data. | Their values varied between Pokémon in real logs, and the writer never sets them. | Uninitialised heap memory; not data. |
| 20 | EV/IV code order (80–85, 100–105) was unknown. | The writer reads fields in the order HP, Atk, Def, Spe, SpA, SpD. | Recorded in the Error Codes table (inferred from field order). |
