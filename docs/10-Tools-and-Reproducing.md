# 10. Tools and Reproducing

All tools are plain Python 3 scripts in `tools/`. Nothing needs to be installed except the libraries below, and
**no tool modifies your `.app`**.

```bash
pip install unicorn capstone pandas numpy
```

You supply: the two `.app` files (from your own DSi dump) and a copy of the
[PokeAPI CSV data](https://github.com/PokeAPI/pokeapi/tree/master/data/v2/csv) (`data/v2/csv`) (use [DownGit](https://downgit.github.io/#/home?url=https://github.com/PokeAPI/pokeapi/tree/master/data/v2/csv)).

## Script reference

| Script | Purpose | Inputs | Outputs |
|---|---|---|---|
| `pwc2010_tool.py` | Swiss-army helper for both apps. Subcommands: `selftest`, `extract`, `inspect`, `make-cfg`, `make-reg` | `.app`, options | the compiled-in table, `regulation.cfg`, `regulation.bin` |
| `make_rule_prd.py` | Rebuild `rule.prd` from PokeAPI | CSV dir, template, `--target bw\|bw2` | `rule_*.prd`, per-cell diff CSV |
| `validate_rule_prd.py` | Run a table through the emulated checker on thousands of sampled cells | `.app`, CSV dir, `.prd` | pass/fail report |
| `make_testcase.py` | Build and verify the illegal-party `.pk5` set | `.app`, optional `--prd` | `.pk5` files, `manifest.csv` |
| `verify_error_codes.py` | Trigger each error code in the emulated checker | `.app`, CSV dir, `.prd` | verification CSV |
| `verify_regulation.py` | Run the `regulation.bin` accessors against a file | `.app`, `regulation.bin` | pass/fail report |
| `build_error_table.py` | Generate the error-code reference from the binary | `.app` | `error_codes.csv`, `message_bank_E.txt` |
| `read_logs.py` | Decode `logT`/`logB` files; codes → messages; decode the team-level bitmask; sanitize logs | log files, optional PokeAPI CSV | readable report, CSV/JSON, sanitized copy |
| `crossvalidate_logs.py` | Replay a real DSi log through the emulated checker | `.app`, CSV dir, `.prd`, log files | per-Pokémon agree/differ report |
| `pk5.py` | Library: build encrypted Gen-5 `.pk5` records | : | : |
| `emu.py` | Library: Unicorn harness for the ARM9 image | : | : |

### `pwc2010_tool.py`

```bash
python3 pwc2010_tool.py selftest  APP.app                       # assert the layout facts on your binary
python3 pwc2010_tool.py extract   APP.app  template.prd          # the compiled-in 386,940-byte table
python3 pwc2010_tool.py inspect   template.prd 1 10 12 150       # min level, max form, move-byte count per species
python3 pwc2010_tool.py make-cfg  regulation.cfg --party --box --livematch --carts IRDO,IREO
python3 pwc2010_tool.py make-reg  regulation.bin --min-count 4 --level-mode 0 --ban-species 150,151
```

Works with either app (it detects the title ID and picks the right buffer address).

### `make_rule_prd.py`

| Option | Meaning |
|---|---|
| `--target bw\|bw2` | Which game generation's move sources define "native". `bw2` adds the BW2 tutor moves. |
| `--events template\|none` | Keep (default) or drop the template's event-move bits |
| `--hidden-abilities allow\|template` | Clear or keep species flag `0x0400`. Default: `allow` for `bw2`, `template` for `bw` |
| `--report FILE` | Write every cell that differs from the template |

### The emulator libraries

`emu.Tool(arm9_path, name)` loads the ARM9 image; `.put(addr, bytes)` writes memory; `.call(addr, *args)` runs a
function and returns `r0`. `pk5.build(**fields)` returns a 136-byte record (species, item, exp, moves, EVs, ball,
locations, `bad_checksum=`, `bad_egg=`, …); see the docstring for all fields.

## Reproducing everything from scratch

```bash
APP=/path/to/PokemonBW2.app            # the BW2 app
CSV=/path/to/pokeapi/data/v2/csv
G=data/generated

python3 tools/pwc2010_tool.py selftest $APP
python3 tools/pwc2010_tool.py extract  $APP $G/rule_template.prd

for t in bw bw2; do
  python3 tools/make_rule_prd.py --csv-dir $CSV --template $G/rule_template.prd --target $t \
          --out $G/rule_$t.prd --report $G/diff_vs_template_$t.csv
  python3 tools/validate_rule_prd.py $APP $CSV $G/rule_$t.prd
done

python3 tools/pwc2010_tool.py make-cfg $G/regulation.cfg --party --box --livematch --carts IRDO,IREO
python3 tools/pwc2010_tool.py make-reg $G/regulation.bin --min-count 3 --level-mode 2 --level 50 --ban-species 150,151,493
python3 tools/verify_regulation.py $APP $G/regulation.bin

python3 tools/make_testcase.py $APP --prd $G/rule_bw2.prd --out testcases/bw2_illegal_party
python3 tools/verify_error_codes.py $APP $CSV $G/rule_bw.prd --out docs/verification_rule_bw.csv
python3 tools/build_error_table.py $APP docs

python3 tools/read_logs.py testcases/hardware_logs/sample_logT261004.dat testcases/hardware_logs/sample_logB261004.dat
python3 tools/crossvalidate_logs.py $APP $CSV $G/rule_bw2.prd \
        testcases/hardware_logs/sample_logT261004.dat testcases/hardware_logs/sample_logB261004.dat
```

`validate_rule_prd.py`, `make_testcase.py`, `verify_error_codes.py`, `verify_regulation.py`,
`build_error_table.py` and `crossvalidate_logs.py` **require the BW2 app** (their addresses are BW2-build addresses). `pwc2010_tool.py` accepts both.

## Using the outputs on a DSi (or 3DS)

Copy `regulation.cfg`, `regulation.bin` and `rule.prd` to the **root of the SD card** used by the DSi (the apps open
`sdmc:regulation.cfg`, `sdmc:regulation.bin`, `sdmc:rule.prd`). **Confirmed on a real DSi** with the generated files
(see [Log Files and Viewer](13-Log-Files-and-Viewer)); the logs appear on the same card as `logTYYMMDD.dat` / `logBYYMMDD.dat`.

## Adapting to another build

Every address in the scripts is a BW2-build address. If you have a different build, re-derive them in this order:
the three path strings → their literal-pool references (`ldr` users) → the init routine → the helper that returns a
buffer and length → the wrapper (the function called with `r3 = 1` and a size of `0x88`/`0xDC`) → the checker.
The table size and record layout were identical across the two builds, so only addresses need to change.
