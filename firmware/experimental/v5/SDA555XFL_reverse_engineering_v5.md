# SDA555XFL reverse engineering v5
## Реальный 8051 binary-кандидат и instruction-level verification

### Proven original
- Size: 131072 bytes
- CRC32: `B3680360`
- SHA-256: `6aa37c6d74d115eefdb52db8792b929b4104c59733485fc2c27a3402c2fce816`

### Generated code
Executable size: **312 bytes**.

The generated program:
1. disables interrupts;
2. keeps PLL/display out of power-save;
3. explicitly writes `PCLK=0148h`, `VLR=0271h`, `HPR=0855h`;
4. installs the factory pointer arrays;
5. writes the factory GDW and our 15-byte 1-bit DRCS #768;
6. initializes all 1000 display cells;
7. draws a visible 8×3 test block;
8. applies factory-proven RGB/display positioning;
9. releases P3.5/P4.7 and enables `CSCR0=0Ch`;
10. enables OSD;
11. enters Sync Master **last**;
12. remains in an infinite loop.

### Two image variants
- `standalone_first_screen_separate_sync_128k.bin`: `SCR0=01h`
- `standalone_first_screen_vcs_128k.bin`: `SCR0=03h`

They differ only in the final SCR0 immediate.

### Sync-routing correction / open issue
The 2003 Micronas Design Guide is more specific than the older generic wording:
it says H-sync is visible on **P3.5 (instead of the H-sync pin)** in Sync Master,
while VS requires P4.7 alternate mode + VS_OE.

At the same time the pin-function table says HS/SC can be HS/VCS in master mode.

Therefore v5 deliberately prepares both alternate paths and the first low-voltage bench
must observe all plausible outputs:
- PSDIP52 pin 19 `HS/SC`
- PSDIP52 pin 20 `VS/P4.7`
- PSDIP52 pin 26 `P3.5`

This avoids hard-coding an unverified silicon-routing assumption.

### Instruction-level verification
Both binaries were executed in a verifier implementing exactly the 8051 opcodes used.

Separate sync:
- steps to stable loop: 10396
- XRAM writes: 3109
- final SCR0: `0x01`

VCS:
- steps to stable loop: 10396
- XRAM writes: 3109
- final SCR0: `0x03`

Automatic checks passed:
- every MOVX write stayed in `C000..FFFF`;
- `C400..C40F` equals the factory pointer0+GDW block;
- `C470..C475` equals the factory DRCS pointer block;
- `C476..C484` equals our 15-byte glyph;
- Display RAM has exactly 1000 CDWs;
- 24 cells are visible, 976 black;
- no unexpected XRAM region was written;
- all DJNZ/SJMP relative branches resolve correctly;
- both programs reach a stable two-byte infinite loop.

This verifier does **not** emulate the analog DAC/display/sync hardware.

### Full 128-KiB images
Separate sync:
- CRC32 `EB676CE4`
- SHA-256 `990eea130ef4b679940a3c9f71d44f7d52cc87aff1ad9e812cf7145ba8479392`

VCS:
- CRC32 `E0123039`
- SHA-256 `8527dd1f0fd8b5fbb1539d4cae1e6a9133a6d37853f47aef212054cf24b7748b`

### Recovery image
`RECOVERY_original_128k.bin` is byte-for-byte identical to `original_1.bin`:
- CRC32 `B3680360`
- SHA-256 `6aa37c6d74d115eefdb52db8792b929b4104c59733485fc2c27a3402c2fce816`

### Flash safety state
The STM32 programmer remains READ ONLY.
No erase/program implementation was added.

The Micronas Flash Programming Manual states that erase is full-chip and program is
byte-oriented, but it explicitly sends the exact command addresses/data to the separate
Flash specification. Therefore the next pass should identify that JEDEC command set
before any WR pulse is permitted.
