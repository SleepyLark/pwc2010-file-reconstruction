# 2. Methodology

## Principles

1. **Treat every conclusion as a hypothesis until a test supports it.** A reading of disassembly is "observed" only
   for what the instructions literally do; what they *mean* is "inferred" until a run confirms it.
2. **Prefer small scripts and reproducible tests** over one-off exploration. Everything cited here can be re-run
   from `tools/`.
3. **For each reverse-engineering step, state what result would confirm or falsify it.** Several hypotheses in this
   project *were* falsified (see [Corrections and Lessons](11-Corrections-and-Lessons)).
4. **Never invent missing data.** Where a field's meaning is unknown it is documented as unknown and carried over
   verbatim, not guessed.

## Evidence sources

| Source | Used for |
|---|---|
| The `.app` binaries (decrypted TWL images) | Header, NitroFS files, ARM9 code and data |
| A community error-code spreadsheet and a wiki page (supplied at the start; later unavailable) | Initial hypotheses about codes and the 13-byte config prefix `01 01 00 00 00 01 00 00 00 00 00 00 01` |
| PokeAPI CSV dataset | Move, species, evolution, and item data for rebuilding `rule.prd` |
| The apps' own message bank (`data/message_E.dat`) | Authoritative error-message text |
| The **Log Viewer** `.app` and a community C++ struct for the log format | Log layout; checked against the Rule Check Tool's own log writer |
| **Real DSi log files** (`logT`/`logB`) | The first hardware evidence: compared with the emulator Pokémon by Pokémon |
| The apps' own code→message routine | Authoritative code→message mapping (run, not read) |

## Tooling

* **Capstone** (ARM disassembly). Skip-data mode is required: without it Capstone silently stops at the first
  literal-pool word, which once produced a truncated listing.
* **Unicorn** (CPU emulation). The ARM9 image is loaded at `0x02004000`; individual functions are called with
  chosen arguments and their return values read.
* **pandas / numpy** for the PokeAPI correlation work.

### The emulator harness (`tools/emu.py`)

The harness maps the ARM9 image, 16 pages of scratch memory at `0x10000000`, and maps any other page on demand.
`Tool.call(addr, *args)` sets `r0–r3`, points `lr` at a sentinel of NOPs, runs, and returns `r0` as a signed int.
No OS, SD card or hardware is emulated, and none is needed: the functions of interest are pure computations over
buffers I place in memory. The emulator's fidelity was then **tested against a real DSi**: rebuilding every Pokémon
from a real log and comparing verdicts gave 16/16 agreement ([Log Files and Viewer](13-Log-Files-and-Viewer)).

Key functions driven this way (BW2 build):

| Address | Role |
|---|---|
| `0x0200C418` | Wrapper: takes a Pokémon record and a mode, returns the first error code |
| `0x0200D070` | Converts a 136-byte stored record to a 220-byte party record |
| `0x0200D828` | Field getter (decrypts and reads one field of a record) |
| `0x0200B430` | The rule checker itself |
| `0x020082CC` | Maps an error code to a message index |
| `0x0200A870–0x0200A934` | `regulation.bin` accessors |

### Validating the test inputs themselves

A synthetic Pokémon is only a good test if the app reads it the way I intended. `tools/pk5.py` builds Gen-5 stored
records (PID, checksum, four shuffled and encrypted 32-byte blocks). Its correctness was established by feeding
records to the app's own getter across different shuffle orders and confirming that species, item and level read
back as written. A test that passed only because the record decoded to noise would be worthless; one such case was
caught this way (see [Corrections and Lessons](11-Corrections-and-Lessons)).

## How a hypothesis was handled: worked example

> *Hypothesis:* the 16-bit value at record offset +2 is a minimum legal level.
>
> *Observed:* in the table compiled into the app, Bulbasaur = 1, Ivysaur = 16, Venusaur = 32.
> *Inferred:* these are their evolution levels.
> *Test that would falsify it:* a Pokémon below that level should be rejected, one at or above should not.
> *Result:* Ivysaur at levels 1 and 10 returned code 31, at 16 and 32 returned 0. Venusaur at 16 returned 31, at 32
> returned 0. **Confirmed.**
>
> *Later refinement:* the field is actually a one-byte minimum level at +2 and a one-byte *maximum form number* at +3.

## Confidence labels in the rest of the wiki

Where a table has a "Status" column:

* **verified**: triggered in the emulator by a constructed input, returning exactly the expected code
* **read-only**: seen in the disassembly but not triggered
* **unreachable**: the condition exists in code but cannot occur given the app's inputs (for example, a one-byte field compared against 255)
* **not observed**: a message exists but no return site was found in the code path the BW2 tool uses
