# 3. App Structure

## Image format (observed)

Both `.app` files are **decrypted TWL (DSi) images** as found in a NAND dump.

| Property | PWC2010 (BW) | PokemonBW2 |
|---|---|---|
| File size | 2,151,424 B | 2,152,448 B |
| DSi title ID (header `0x230`) | `0003000434534e41` | `000300044b394841` |
| Game-code field | `NTRJ`, maker `01` (both) | same |
| ARM9 offset / load address / size | `0x4000` / `0x02004000` / `0x108BE0` | `0x4000` / `0x02004000` / `0x108E60` |
| ARM9 entry | `0x02004850` | `0x02004850` |
| NitroFS | 14 files | 14 files |
| Rule-table buffer (slot 0) | `0x0203BC4C` | `0x0203BECC` |

## NitroFS contents (observed)

Only name and text tables. **No rule data is stored in the filesystem.**

| Files | Content |
|---|---|
| `data/item_{E,J,K}.dat` | Item names (English / Japanese / Korean), UTF-16LE |
| `data/pokemon_{E,J,K}.dat` | Species names |
| `data/waza_{E,J,K}.dat` | Move names |
| `data/message_{E,J,K}.dat` | The 66 UI/error strings per language, one per line |
| `data/tbf_ww_s.NFTR`, `data/tbf_kr_s.NFTR` | Fonts |

## SD-card paths (observed strings, ARM9 `0x0203B5xx`–`0x0203BCxx`)

`sdmc:regulation.cfg`, `sdmc:regulation.bin`, `sdmc:rule.prd` (inputs);
`sdmc:livematchYYMMDD.dat`, `sdmc:logTYYMMDD.dat`, `sdmc:logBYYMMDD.dat`, `sdmc:logYYMMDD.dat` (outputs).

## Program flow (observed unless marked)

The main routine starts at **`0x020050E0`** (same address in both builds):

1. Load `rule.prd` whole into memory (helper `0x0200A61C`: open, get length, allocate, read, close, return buffer and
   length) and hand it to the **rule loader** (`0x0200B34C` in BW2; BW1 `0x0200B320`), which `memcpy`s it into a
   static buffer. No parsing, no checksum.
2. Load `regulation.bin` and `regulation.cfg` the same way (helper `0x0200A54C`). **No length checks.**
3. **Cartridge gate** (`0x02008998`): read the inserted cartridge's game code, pick a `regulation.cfg` byte (see
   [regulation.cfg](04-regulation-cfg)). A zero result shows a "wrong cartridge" screen and the app exits.
4. If `cfg[1] == 1`: read the **Battle Box** (save block `0x31`, six records of 0x88 bytes) and run the checker on each.
5. If `cfg[0] == 1`: read the **Party** (save block `0x1A`, six records of 0xDC bytes) and do the same.
   *(Inferred from record sizes: 0x88 is a stored record, 0xDC a party record.)*
6. For every Pokémon that passed, apply the `regulation.bin` rules (codes 500–502), then party-wide rules
   (600–603).
7. **Logs.** After the result screen, when the user presses **A** (a key-register test at `0x02007C00`; inferred), and
   only for a check enabled by `cfg[1]` (Battle Box, call at `0x02007C4C`) or `cfg[0]` (Party, `0x02007CA0`), the tool
   builds a 0x234-byte record and **appends** it to `logBYYMMDD.dat` / `logTYYMMDD.dat` (writer `0x0200AED0`). The
   team-level problems are stored as a **bitmask**; see [Log Files and Viewer](13-Log-Files-and-Viewer).
8. If `cfg[0x0C] != 0`, append 90-byte records to `livematchYYMMDD.dat` (BW1 writer at `0x020087F8`). The Log Viewer
   does not read this file.
9. Draw the result screens; per-slot codes live in an array of six 32-bit values, empty slots hold `-1` (they are
   stored as 0 in the log).

Both passes call the wrapper with **mode 0**. (`mov r5, sb` executes once, outside the loop, with `sb = 0`.)

## Per-Pokémon check path

```
wrapper 0x0200C418(mode, record, size, 1)
   ├─ reject all-zero header                    (empty slot)
   ├─ copy the first 0x88 bytes
   ├─ 0x0200D828(rec, 0x9F)  level
   ├─ 0x0200D070             stored (136 B) -> party (220 B) form
   └─ checker 0x0200B430(party_record, mode)    returns the FIRST failing code, or 0
```

Because the checker returns at the first failure, **a Pokémon shows only one code at a time**. Fixing it may reveal
the next. The evaluation order is listed on the [Error Codes](08-Error-Codes) page.

### Modes

| Mode | Used by BW2 tool? | Effect |
|---|---|---|
| 0 | **Yes (both passes)** | Normal. Also enables the native Sky Drop check (170+). |
| 1, 2 | No | Species flags `0x100` / `0x200` give code 23 |
| 3 | No | Handles a different 0x70-byte record format; relaxes several checks |
| 4 | No | Separate path in the wrapper; relaxes level and ball checks; flag `0x80` gives code 23 |

Code 23 is therefore unreachable in the BW2 tool. (Confirmed by calling the checker with mode 1.)

## Text storage (observed)

`message_{J,E,K}.dat` are loaded line by line into **512-byte slots**: language `L` (J=0, E=1, K=2) occupies
`0x0210CB10 + L × 0x8400`, and message `i` is at `+ i × 0x200`. `0x8400 / 0x200 = 66`, matching the 66 lines.
The `@` character in the strings marks a line break in the on-screen layout.

## Code→message routine (observed and run)

`0x020082CC` takes an error code in `r0` and returns a message index in `r0`. It is a hand-compiled chain of
compares and jump tables (ranges are grouped in sixes, so `150–155` all return message 26 even though only
`150–153` are ever produced). **It was run for every code −1…700** to build the mapping in
[Error Codes](08-Error-Codes); it was never decoded by hand.

## BW1 vs BW2 differences (observed)

| Item | Result |
|---|---|
| Init routine, file-load sites, cartridge-gate routine, `regulation.cfg` read sites | **Identical addresses and logic** |
| Cartridge game codes | BW: `IRA*`/`IRB*`; BW2: `IRD*`/`IRE*`. Same index mapping. |
| Rule loader, move/item accessors, `regulation.bin` accessors | Same code, **+0x2C** bytes in BW2 |
| Checker and wrapper | BW2 is larger (the wrapper moved from ≈`0x0200C1D4` to `0x0200C418`) |
| `rule.prd` buffer size, record size, move limit, species limit | **Identical** (`0x5E77C`, `0x244`, 560, 649) |
| Table compiled into the app | **Byte-identical** in both builds (45,612 non-zero bytes) |

The last row matters: the compiled-in table is *not* BW2-specific. It looks like a BW1-era development table that was
carried over unchanged.

## The compiled-in table is not a fallback

The loader keeps two buffers and an "active" index in BSS (`0x0222228C` BW1 / `0x0222250C` BW2, zero-initialised).
The first `rule.prd` load goes into **slot 1** and flips the active index. Slot 0 (populated, 386,940 bytes in the
ARM9 image) is used only until that load; slot 1 in the image is all zeros. A shorter-than-expected `rule.prd`
therefore leaves the tail of the table zeroed, which means "nothing legal", so `rule.prd` must be full size.
