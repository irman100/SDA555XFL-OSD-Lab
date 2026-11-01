# SDA555XFL OSD Lab

**From reverse-engineering a television OSD processor to a standalone graphics and retro-gaming platform.**

A hardware/software research project based on the **Sokol A-2010 TV chassis** and the **Micronas SDA555XFL A14 (PSDIP-52)**. The work investigates its 8051-compatible core, reconstructs the OSD memory model, brings custom graphics to a CRT, develops an STM32F103 Flash Programming Interface (FPI), and builds standalone Pong and Tetris software.

**Project progression:** PCB investigation → OSD reverse engineering → standalone video output → STM32F103 FPI programmer → menu and Pong → Tetris / Arcade.

[Русская версия](README_RU.md) · [Project status](docs/PROJECT_STATUS_RU.md) · [Technical overview](docs/PROJECT_OVERVIEW_RU.md)

## At a glance

- Target: Micronas SDA555XFL A14, PSDIP-52.
- Platform: Sokol A-2010 TV chassis.
- CPU: 8051-compatible core.
- Embedded Flash: 128 KiB.
- OSD: 40 × 25 character positions, 3,000-byte Character Display RAM, DRCS, GDW and CLUT.
- Video: dedicated H/V sync and RGB outputs.
- FPI: custom STM32F103 interface and host-side utilities.
- Demonstrations: standalone OSD, IR-controlled Pong, Tetris / Arcade.

## Project evolution

### 1 — Board and target investigation
Documented the Sokol A-2010 PCB, SDA555XFL package, accessible signal pads, FPI nodes and existing resistor network. Both PCB sides were photographed. Mechanical clearance/cutout work is documented using annotated source photographs; those overlays are working references, not manufacturer drawings.

### 2 — OSD reverse engineering
Recovered the screen-memory model:
- 40 columns × 25 rows = 1,000 character cells;
- 3 bytes per Character Display Word;
- 3,000 bytes of Character Display RAM at F448–FFFF;
- pointer arrays, Global Display Word (GDW), CLUT and DRCS areas;
- a custom 12 × 10 raster glyph for standalone OSD.

### 3 — Standalone graphics and sync
Built standalone OSD test firmware and v5/v6 diagnostic variants. Standalone bench work recorded approximately 15.625 kHz H-sync and 50 Hz V-sync. A photograph dated 1 November 2026 shows the custom Tetris OSD on a CRT. A photograph demonstrates visible output, not analog waveform margins or long-term stability.

### 4 — FPI migration to STM32F103
The earlier Arduino Nano wiring proposal is obsolete and must not be used as the current connection guide. The current FPI interface is based on **STM32F103** and two real annotated PCB photographs: top side for signals on the existing resistor network; underside for control lines and D6/D7.

See [STM32F103 FPI pin mapping](docs/STM32_FPI_CONNECTIONS_RU.md).

The project includes non-destructive ID detection (workflow reports ID BF D5), image and CRC validation, 128 KiB transfer planning, an STM32F103 FPI Engine v0.5, safety interlocks and software simulation. Destructive operations are compile-locked by default in v0.5 (ALLOW_DESTRUCTIVE_FPI=0). A software simulation is not evidence of a physical Flash write.

### 5 — Menu, Pong and Tetris
The standalone display work evolved into a custom menu and IR-controlled Pong, followed by Tetris/Arcade with a custom HUD, piece statistics, NEXT panel, 10 × 20 board, levels, gravity and held-key repeat experiments.

The latest documented Arcade build is v0.22 for P3.3:
- 131,072 bytes;
- CRC32 8AB10F0B;
- SHA-256 5d5c127dedc82796cb930943b10adb4c89128b8bcc29b107e7e98d8eeae476ad.

Helper-level tests pass; full 8051/IR runtime emulation and final timing validation with the actual remote remain open.

## STM32F103 FPI mapping — current reference

Use only the STM32F103 mapping in [the dedicated guide](docs/STM32_FPI_CONNECTIONS_RU.md) and its two new real annotated PCB photographs. The older Arduino Nano diagram is obsolete.

Summary:
- PA5…PA0 → D5…D0 through existing pull-up resistors R111/R112/R113/R114/R116/R115;
- PB15 → FPI ENTER (P3.6);
- PA8 → RESET#;
- PB0/PB1/PB10/PB11/PB12/PB13/PB14 → WR#, RD#, DDIR, ASEL1, ASELO, ASEN#, FMOD;
- PA6/PA7 → D6/D7.

R117/R118 are not to be touched; the annotation identifies them as connector-only. Pin 51 is marked NC. Do not infer FPI purpose for other pads without verification.

## Repository structure

| Directory | Purpose |
|---|---|
| docs/history/ | Reverse-engineering notes, memory maps and sync history |
| docs/STM32_FPI_CONNECTIONS_RU.md | Current STM32F103 FPI wiring reference |
| docs/PROJECT_PROGRESSION_RU.md | Project progression timeline |
| docs/PROJECT_OVERVIEW_RU.md | Technical architecture |
| docs/PROJECT_STATUS_RU.md | Current results and open work |
| docs/VERIFICATION_MATRIX_RU.md | Evidence and verification matrix |
| firmware/experimental/v5/ | Standalone OSD v5 |
| firmware/experimental/v6_no_shadow/ | Diagnostic v6 variants |
| programmer/stm32f103_engine_v0_5/ | STM32F103 firmware, host tools, safety audit and simulation |

## Evidence levels

The repository distinguishes:
- **Measured** — physically measured with suitable equipment.
- **Observed** — directly visible in a photograph, video or log.
- **Simulated** — checked using software models or helper-level tests.
- **Pending** — requires hardware verification.

A CRT photograph is observed evidence. A helper test is simulated evidence. A software RGB DAC value of 1.2 Vpp is not an analog measurement at the actual load.

## Open work

1. Complete hardware validation of Tetris gravity, repeat, soft-drop and key-release behaviour with the actual IR remote.
2. Separately verify complete Flash read-back for the current Arcade image, if a write is explicitly authorised and performed.
3. Measure RGB, BLANK/COR and sync waveforms with an oscilloscope and correct termination.
4. Confirm the mechanical cutout/clearance using physical dimensions, not photograph annotations alone.
5. Add the two original STM32-annotated photographs to GitHub and refresh the visual deck exclusively with these real source photos.

## Safety and publication

- The original factory Flash dump and recovery copies are kept outside Git.
- TV service manuals and third-party material are not redistributed.
- Do not remove the FPI compile lock or run erase/program commands without a separately reviewed target profile, verified backup and complete read-back plan.
- Colour annotations are not mechanical drawings.
- The repository remains Private; no public licence is granted by the current contents.

Start with the [project progression](docs/PROJECT_PROGRESSION_RU.md), then read the [STM32F103 FPI guide](docs/STM32_FPI_CONNECTIONS_RU.md) and the [technical overview](docs/PROJECT_OVERVIEW_RU.md).
