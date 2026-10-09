# PWC Rule Check Tool: Reverse-Engineering Notes

Research notes on two abandoned Nintendo DSi applications used to check Pokémon legality for official
Pokémon World Championships–style tournaments:

| Application | DSi title ID | Games checked |
|---|---|---|
| **PWC2010 Rule Check Tool** | `0003000434534e41` | Pokémon Black / White |
| **PokemonBW2 Rule Check Tool** | `000300044b394841` | Pokémon Black 2 / White 2 |

Both apps verify Pokémon in a cartridge's save data against rule files stored on the DSi's SD card. Those files
were not distributed with the apps. This project works out **what each file contains, how the apps read it, and
how to rebuild usable replacements**, and documents every on-screen error code.

## Pages

| # | Page | What it covers |
|---|---|---|
| 1 | [Project Overview](01-Project-Overview) | Goals, results at a glance, repository map |
| 2 | [Methodology](02-Methodology) | How conclusions were reached; confidence labels; the emulator harness |
| 3 | [App Structure](03-App-Structure) | DSi header, NitroFS, ARM9 layout, key functions, BW vs BW2 differences |
| 4 | [regulation.cfg](04-regulation-cfg) | The 13-byte switch file and the cartridge gate |
| 5 | [regulation.bin](05-regulation-bin) | The tournament-rules file (bans, level rules, clauses) |
| 6 | [rule.prd Format](06-rule-prd-format) | The 386,940-byte legality table, field by field |
| 7 | [Rebuilding rule.prd](07-Rebuilding-rule-prd) | Regenerating the table from PokeAPI; accuracy; decisions |
| 8 | [Error Codes](08-Error-Codes) | Every red number in the log, with its message and cause |
| 9 | [Test Cases](09-Test-Cases) | The illegal-party test set and how each case was verified |
| 10 | [Tools and Reproducing](10-Tools-and-Reproducing) | Every script, its inputs/outputs, how to rerun everything |
| 11 | [Corrections and Lessons](11-Corrections-and-Lessons) | Mistakes made along the way and what fixed them |
| 12 | [Open Questions](12-Open-Questions) | What is still unknown or untested |
| 13 | [Log Files and Viewer](13-Log-Files-and-Viewer) | The `logT`/`logB` format, what the viewer's red numbers mean (including the party-level bitmask), real-DSi evidence |

## Ground rules used throughout

Every claim is labelled one of:

* **Observed**: read directly from the binary, a file, or the output of an emulator run.
* **Inferred**: a strong interpretation of observed facts (usually confirmed by a test, which is then cited).
* **Speculative**: a possibility with no confirming test. These are kept to the [Open Questions](12-Open-Questions) page.

Addresses are ARM9 virtual addresses (`0x02004000` = start of the ARM9 image). Unless stated otherwise,
addresses are for the **BW2 build**; the BW1 build has the same code shifted by a small constant.
