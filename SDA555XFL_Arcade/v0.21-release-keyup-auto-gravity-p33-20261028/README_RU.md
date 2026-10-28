# SUPERSEDED — v0.21 release-keyup experiment

**Do not use this documentation as a firmware specification. It contains an incorrect assumption about IR key-up codes.** The implementation treated values with bit `0x40` set as button-release events. Review of the 14-bit IR command decoding showed that this bit can be part of an extended command and is not a reliable universal key-up marker.

Use the corrected documentation and locally verified release artifacts from [Arcade v0.22](https://github.com/irman100/SDA555XFL-OSD-Lab/tree/release/arcade-v0.22-irwatchdog-autogravity-gray-pongline-p33-20261028/SDA555XFL_Arcade/v0.22-irwatchdog-autogravity-gray-pongline-p33-20261028).

In v0.22, stopping held-key repeat is handled with an inactivity watchdog refreshed by repeated frames of the same IR command. It expires after 8 Tetris game ticks without a matching frame and clears the repeat latch/timer. This is a best-effort solution; actual remote frame cadence still requires testing on the physical board.

This v0.21 branch contains historical documentation only; no verified v0.21 firmware binary was published. Do not flash a binary based on these v0.21 notes.
