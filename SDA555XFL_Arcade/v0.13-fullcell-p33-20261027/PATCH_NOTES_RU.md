# SDA555XFL Arcade v0.13 — Tetris full-cell patch

## What changed

Patched the uploaded P3.3 Arcade v0.12 firmware directly. The original Tetris, Pong, launcher, menu, controls and settings remain byte-identical outside the embedded DRCS data. No routine, branch, pointer, or game-logic code was changed.

The image stores the seven 12×10 Tetris DRCS glyphs as 420 immediate operands in an existing startup sequence at ROM offsets `0x013B..0x07CA`. The patch replaces exactly those 420 immediate values while preserving each instruction (`MOV A,#imm; MOVX @DPTR,A; INC DPTR`) and the same 128-KiB image size.

The prior glyphs contained black index-0 pixels in every cell; the new glyph payload contains no index 0. Neighboring Tetris cells therefore do not inherit the previous black moat. The original palette-index convention is preserved per glyph: highlight `1`, face `2..8`, shadow `9..15`.

## Build / input identity

- Input: `sda555xfl_arcade_v0_12_P33_128k.bin`
- Input CRC32: `39C1BD4B`
- Input SHA-256: `09f59d40672278b5ccd56c241f769ed6bf4c55b191a7e18727e63c2ac1065896`
- Output: `sda555xfl_arcade_v0_13_P33_fullcell_128k.bin`
- Output size: `131072` bytes
- Output CRC32: `69879A1A`
- Output SHA-256: `81a3973a5eb5b1cdcd8032e90fb285f4855eb7414738f0fdfbe8e8e6e5ccaa5b`
- Changed bytes: 420 immediate operands only

## Verification

The script/report verifies the source identity, exact 420-store opcodes, replacement read-back, unchanged file size, and byte equality everywhere except those 420 operands. It also verifies every one of the seven 12×10 glyphs contains no black index `0`.

No Flash was written and no physical-TV test was performed. This is a firmware binary built from the uploaded P3.3 base, not a mere graphics preview. Test only after preserving a verified full Flash backup. The P3.2 variant was not built because only P3.3 was supplied.
