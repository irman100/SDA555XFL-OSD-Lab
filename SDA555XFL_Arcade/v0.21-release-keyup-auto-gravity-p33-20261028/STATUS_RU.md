# SUPERSEDED — v0.21 status correction

The original v0.21 notes incorrectly assumed that `0x5E`, `0x5A`, and `0x5F` are universal key-up events. This assumption is invalid for the observed 14-bit IR decode path: bit `0x40` can be part of an extended command code.

Do not use this branch as the specification for the release. Corrected implementation and reports are in [v0.22](https://github.com/irman100/SDA555XFL-OSD-Lab/tree/release/arcade-v0.22-irwatchdog-autogravity-gray-pongline-p33-20261028/SDA555XFL_Arcade/v0.22-irwatchdog-autogravity-gray-pongline-p33-20261028).

v0.22 uses a watchdog refreshed by repeated matching IR frames and clears the held-key latch after 8 Tetris ticks without such a frame. This design has not yet been verified against the actual physical remote/TV cadence. No v0.21 binary should be flashed based on the old documentation.
