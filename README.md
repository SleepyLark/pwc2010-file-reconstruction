# PWC Rule Check Tool: Reverse-Engineering Notes and Tools

Research into two obscure Nintendo DSi applications that checked Pokémon legality for official tournaments:

* **PWC2010 Rule Check Tool** (Pokémon Black / White), title ID `0003000434534e41`
* **PokemonBW2 Rule Check Tool** (Pokémon Black 2 / White 2), title ID `000300044b394841`

The apps read three files from the SD card that were never distributed: `regulation.cfg`, `regulation.bin` and
`rule.prd`. This repository documents what those files are, how the apps use them, and provides tools to rebuild
working replacements, plus a reference for every error code the apps (and the log viewer) show.

> **Status:** initial verification was mainly done by **emulating the apps' own ARM9 code** and later confirmed using **real DSi hardware**.

## What you get

| | |
|---|---|
| 📄 **Format documentation** | All three files, field by field, with the code address behind each claim |
| 🔢 **Error-code reference** | 72 codes, exact on-screen messages taken from the app, cause of each, and verification status → [`docs/08-Error-Codes.md`](docs/08-Error-Codes.md) / [`error_codes.csv`](docs/error_codes.csv) |
| 🛠 **File generators** | `regulation.cfg`, `regulation.bin`, and a `rule.prd` rebuilt from [PokeAPI](https://pokeapi.co) data (BW and BW2 variants) |
| 🧪 **Illegal-party test case** | 26 synthetic Pokémon with a manifest of expected error codes |
| 📜 **Log format + reader** | The `logT`/`logB` format, what the Log Viewer's red numbers mean (the team-level number is a **bitmask**), a log decoder |
| 🔬 **Emulator harness** | Run the apps' checker on any Pokémon you construct, or replay a real DSi log |

## Headline findings

* `regulation.cfg` is **13 bytes**. Bytes 0 and 1 switch the Party and Battle Box checks (must be exactly `1`);
  bytes 4–10 are **per-cartridge accept flags** chosen by the cartridge's game code; byte 0x0C enables the livematch
  log. Identical in both apps.
* `rule.prd` is **not parsed**. It is copied straight into memory: an 80-byte **held-item whitelist** followed by
  **667 records of 0x244 bytes** (flags, minimum level, maximum form, allowed locations, one legality byte per move).
  Total size **386,940 bytes**.
* `regulation.bin` holds the tournament rules: minimum team size, level rule, total-level cap, duplicate clauses, a
  **banned-species bitmap** and a **banned-item bitmap**.
* The apps contain a populated copy of the table, but it is **not a fallback**: it is overwritten by the first
  `rule.prd` load. It is byte-identical in both apps.
* PokeAPI reproduces the table's move data to **99.95 %** of cells; the remainder is mostly event moves, which PokeAPI
  lacks.
* The apps have their **own Sky Drop check** (code 170), so Sky Drop is deliberately *not* zeroed in the rebuilt table.
* The Log Viewer prints **numbers only** (decimal). Beside a Pokémon that number is the error code; for the whole team
  it is a **bitmask** (2 duplicate species, 4 duplicate items, 8 total level, 16 too few Pokémon), not 600–603.
* Several earlier assumptions were wrong and were corrected along the way; see
  [Corrections and Lessons](docs/11-Corrections-and-Lessons.md).

## Quick start

```bash
pip install unicorn capstone pandas numpy

# 1. check your binary matches the documented layout
python3 tools/pwc2010_tool.py selftest PokemonBW2.app

# 2. extract the table compiled into the app, then rebuild from PokeAPI
python3 tools/pwc2010_tool.py extract PokemonBW2.app data/generated/rule_template.prd
python3 tools/make_rule_prd.py --csv-dir pokeapi/data/v2/csv --template data/generated/rule_template.prd \
        --target bw2 --out data/generated/rule_bw2.prd

# 3. config files
python3 tools/pwc2010_tool.py make-cfg data/generated/regulation.cfg --party --box --livematch --carts IRDO,IREO
python3 tools/pwc2010_tool.py make-reg data/generated/regulation.bin --min-count 4 --level-mode 0 --ban-species 150,151

# 4. verify everything in the emulator
python3 tools/validate_rule_prd.py PokemonBW2.app pokeapi/data/v2/csv data/generated/rule_bw2.prd
python3 tools/make_testcase.py     PokemonBW2.app --prd data/generated/rule_bw2.prd --out testcases/bw2_illegal_party
```

Copy `regulation.cfg`, `regulation.bin` and `rule.prd` to the SD card root. Full instructions:
[Tools and Reproducing](docs/10-Tools-and-Reproducing.md).

## Documentation

The `docs/` folder is a wiki-style set of pages (it works as plain Markdown, and as a GitHub wiki with
`_Sidebar.md`). Start at [`docs/Home.md`](docs/Home.md).

1. [Project Overview](docs/01-Project-Overview.md)
2. [Methodology](docs/02-Methodology.md)
3. [App Structure](docs/03-App-Structure.md)
4. [`regulation.cfg`](docs/04-regulation-cfg.md)
5. [`regulation.bin`](docs/05-regulation-bin.md)
6. [`rule.prd` Format](docs/06-rule-prd-format.md)
7. [Rebuilding `rule.prd`](docs/07-Rebuilding-rule-prd.md)
8. [Error Codes](docs/08-Error-Codes.md)
9. [Test Cases](docs/09-Test-Cases.md)
10. [Tools and Reproducing](docs/10-Tools-and-Reproducing.md)
11. [Corrections and Lessons](docs/11-Corrections-and-Lessons.md)
12. [Open Questions](docs/12-Open-Questions.md)
13. [Log Files and Viewer](docs/13-Log-Files-and-Viewer.md)

## Repository layout

```
docs/                          wiki pages, error_codes.csv, message_bank_E.txt, verification output
tools/                         Python scripts (pwc2010_tool, make_rule_prd, validate_rule_prd, make_testcase,
                               verify_error_codes, verify_regulation, build_error_table, read_logs,
                               crossvalidate_logs, pk5, emu)
data/generated/                regulation.cfg, regulation.bin, per-cell diff reports
                               (*.prd are git-ignored: see below)
testcases/bw2_illegal_party/   26 .pk5 files + manifest.csv
testcases/hardware_logs/       sanitized logT/logB from a real DSi run
```

## Legal and licensing notes

* **No copyrighted or propriety software are included in this repo**.
* The scripts, `.pk5` test files and documentation are original work generated using Claude Sonnet 5.5. **Free and open for all**.
* Pokémon and related names are trademarks of Nintendo / Creatures Inc. / GAME FREAK inc. This project is not
  affiliated with or endorsed by them.
* PokeAPI data is used under PokeAPI's own terms. Only cached files are used and no requests are ever sent to the official API; see <https://github.com/PokeAPI/pokeapi>.
