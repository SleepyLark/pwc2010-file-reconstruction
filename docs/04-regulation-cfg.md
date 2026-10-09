# 4. `regulation.cfg`

A **13-byte** file of switches. The apps read the whole file with no length check; the highest offset ever read is
`0x0C`, so 13 bytes is the minimum safe size.

## Field map

| Offset | Meaning | Test applied | Status |
|---|---|---|---|
| `0x00` | Check the **Party** (also gates writing the Party log `logT`) | must be **exactly `1`** (`cmp r0,#1`) | read-only; confirmed on hardware (Party was checked and logged) |
| `0x01` | Check the **Battle Box** (also gates writing `logB`) | must be **exactly `1`** | read-only; confirmed on hardware |
| `0x02`, `0x03` | not read | | read-only |
| `0x04`–`0x0A` | **Per-cartridge accept flags** (table below) | non-zero = accept | **verified** (emulated) |
| `0x0B` | not read | | read-only |
| `0x0C` | Write the **livematch** file (a separate output; **not** the `logT`/`logB` files the Log Viewer reads) | **any non-zero** | read-only |
| `0x0D` and up | not read | | read-only |

Read sites (BW1 build; the BW2 build has identical read sites): `0x020054D8` (`cfg[1]`), `0x02006558` (`cfg[0]`),
`0x020051D8` → `0x02008998` (cartridge gate), `0x020077CC` (`cfg[0x0C]`).

The two checks use different tests: `cfg[0]` and `cfg[1]` must be exactly 1 (a value of 2 *disables* them), while
`cfg[0x0C]` enables on any non-zero byte.

## The cartridge gate

The routine at `0x02008998` (identical in both apps) reads the 32-bit game code at offset `+0x0C` of the cartridge
header copy that the DSi keeps at `0x02FFFA80`. It then selects either a constant "allowed" or one of the config
bytes. The mapping was found by **running the routine over every code `IRAA`…`IRZZ`** in an emulator, so it does not
depend on my reading of the compare tree.

| Game codes | Result |
|---|---|
| `IRBO` `IRAO` (BW) · `IRDO` `IREO` (BW2) | `cfg[5]` |
| `IRBJ` `IRAJ` · `IRDJ` `IREJ` | `cfg[4]` |
| `IRBF` `IRAF` · `IRDF` `IREF` | `cfg[6]` |
| `IRBI` `IRAI` · `IRDI` `IREI` | `cfg[7]` |
| `IRBS` `IRAS` · `IRDS` `IRES` | `cfg[8]` |
| `IRBD` `IRAD` · `IRDD` `IRED` | `cfg[9]` |
| `IRBK` `IRAK` · `IRDK` `IREK` | `cfg[10]` |
| anything else | 0 (not allowed) |

*(Inferred, by general DS convention rather than from these files: the last letter of the game code is the
region/language: `O` USA and Europe, `J` Japan, `F` France, `D` Germany, `I` Italy, `S` Spain, `K` Korea)*

### What a failed gate does (inferred)

If the byte is 0, execution falls through to a block that draws a screen, waits for a button press, and then calls
`0x0201AB04`, the same routine used by the file-error paths. This is consistent with message 44 ("Pokémon Black or
White … is not the inserted cartridge"). It was not run on hardware.

## Correction to earlier hypothesis

An early note described byte 5 as "turns on Slot-1 access". The code shows it is not a general hardware switch. It is
**one of seven per-cartridge accept flags**, and byte 5 happens to be the one used by the Japanese releases. A US or
European cartridge needs no config byte at all.

## Ready-made examples

| Goal | 13 bytes |
|---|---|
| Party + Battle Box + livematch log, USA/European cartridge | `01 01 00 00 00 01 00 00 00 00 00 00 01` |
| Same, US/European cartridge (cartridge bytes irrelevant) | `01 01 00 00 00 00 00 00 00 00 00 00 01` |
| Party only, no log | `01 00 00 00 00 00 00 00 00 00 00 00 00` |

The first row is exactly the prefix the community found by trial and error; the generator reproduces it
(`tools/pwc2010_tool.py make-cfg --party --box --livematch --carts IRDO,IREO`).

