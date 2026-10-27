# Arcade v0.15 — Bevel HUD / P3.3

This is the continuation of the user-supplied Arcade v0.12 P3.3 firmware. The local v0.15 release package was produced with the revised Tetris HUD and is available in the chat attachments:
- `SDA555XFL_Arcade_v0_15_P33_release_core.zip`
- `SDA555XFL_Arcade_v0_15_P33_firmware_only.zip`
- `SDA555XFL_Arcade_v0_15_P33_flash_image.zip`

The new view places the lines counter above the playfield, TOP/SCORE/NEXT on the right, statistics on the left, and a metallic beveled frame around the centered 10×20 board. Tetris tile faces fill their cells; a one-pixel highlight and one-pixel opposite shadow provide the raised-block effect. Pong and the launcher are retained in the base image.

**Important:** the GitHub branch includes this release note, but the binary ZIP itself is not counted as published here until its binary upload can be verified through the repository contents API. The P3.3 BIN was not written to external Flash and has not been tested on the physical TV. The "NEXT" and "LEVEL 03" panels are static, because the original game loop has no dynamic next-piece queue or level counter.
