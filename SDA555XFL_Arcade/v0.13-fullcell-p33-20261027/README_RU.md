# SDA555XFL Arcade v0.13 — Tetris Full-Cell (P3.3)

This release is based on the user-supplied `sda555xfl_arcade_v0_12_P33_128k.bin`, not reconstructed from an absent source archive.

## Firmware artifact

`SDA555XFL_Arcade_v0_13_P33_fullcell_firmware.zip` contains the patched 128-KiB BIN, the original input BIN, the exact 420-byte DRCS payload, the reproducible patch script, source graphics, SHA-256 sums, and a verification report.

- Output file: `sda555xfl_arcade_v0_13_P33_fullcell_128k.bin`
- Size: 131072 bytes
- CRC32: `69879A1A`
- SHA-256: `81a3973a5eb5b1cdcd8032e90fb285f4855eb7414738f0fdfbe8e8e6e5ccaa5b`
- Archive SHA-256: `0918f69e3a1dd65d55431da1777eb690afb2a51907807a3b3845458547af512c`

## Patch scope

The image already contained seven Tetris DRCS glyphs as 420 immediate operands in the startup upload stream. The release replaces those operands only, removing index-0 pixels from the 12×10 cells. The instruction opcodes and all non-operand bytes are preserved. Pong, the launcher, menus, controls, and game logic are byte-identical to the input.

The existing per-piece color-index convention is kept: highlight 1, face 2–8, shade 9–15. No CLUT or display-word code is changed.

## Validation and limits

The patcher checks the input SHA-256, the 420-byte payload, each store instruction, readback, exact image size, and byte equality outside the immediate operands. The output was regenerated and compared byte-for-byte with the release BIN.

No external Flash was written and no physical-TV test was performed. P3.2 was not built because only the P3.3 image was provided. Before any hardware write, verify and preserve a complete backup of the current Flash.
