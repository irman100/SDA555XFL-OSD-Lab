# Arcade v0.12 — full-cell Tetris DRCS (27.10.2026)

## State

The local assets package was generated and verified. It corrects the old inset look: the 12×10 DRCS tile rasters use their full cell area, with a colored bevel and highlight instead of black padding. The palette is tuned to the supplied screenshot (blue, green, white).

- Local ZIP SHA-256: `90ed6eec08f8d6b60e40174878841da19fbae58967e522d438c4e167191be653`
- Raw DRCS payload: 420 bytes; CRC32 `B210C008`
- Candidate CLUT payload: 32 bytes; SHA-256 `39dd0509792bba4f0b94c72d2fda509d0286a1a903e6e8074a4e46fc7450bc4d`
- Validation: generator round-trip, ZIP integrity, and local SHA-256 checks passed.

## Limits — do not flash this package

This is an assets-recovery package, not a firmware build. It does not prove that the game runtime uploads the DRCS data or that the CLUT setup is correct on the actual adapter. The real Arcade v0.11 P3.2/P3.3 BINs are not available in the current working environment; expected old CRC32 values in the handoff are P3.2 `D05ED794` and P3.3 `34FC08F1`. Do not create placeholder BINs or write external Flash. No physical-TV test has been performed in this step.

The complete assets ZIP and the updated handoff are available as local conversation attachments. The ZIP itself is not yet stored in this repository; this status note records the verified state and outstanding integration blockers.

Repository: https://github.com/irman100/SDA555XFL-OSD-Lab
