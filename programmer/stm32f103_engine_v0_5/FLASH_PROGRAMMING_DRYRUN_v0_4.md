# SDA555XFL Flash Programming Path — v0.4 DRY-RUN

## Proven ID
Live Software ID = `BF D5`, so the command interface is SST39LF/VF010-compatible.

## Exact sequences used only as plans

Byte Program: `5555 AA`, `2AAA 55`, `5555 A0`, `ADDR DATA`.

Chip Erase: `5555 AA`, `2AAA 55`, `5555 80`, `5555 AA`, `2AAA 55`, `5555 10`.

Status model for the future destructive implementation:
- Program busy: DQ7 is complement of true D7; complete: DQ7 becomes true data.
- Erase busy: DQ7=0; complete: DQ7=1.
- DQ6 toggles while Program/Erase is active, then stops.
- After apparent completion, confirm with two additional reads.
- Byte Program max 20 us; Chip Erase typical 70 ms in the SST datasheet.

## v0.4 safety state
`PROGRAM`, `ERASE`, `WRITE` return `ERR LOCKED_V0_4`.
`PLANBYTE` and `PLANERASE` only print the sequence; they never call the FPI write routine.

## Transition analysis from proven original
Proven original SHA-256: `6aa37c6d74d115eefdb52db8792b929b4104c59733485fc2c27a3402c2fce816`.

Separate-sync image:
- unchanged: 19663
- direct 1->0 changed bytes: 38
- changed bytes needing 0->1: 111371
- full erase required: YES
- bytes to program after erase: 310

VCS image:
- unchanged: 19663
- direct 1->0 changed bytes: 38
- changed bytes needing 0->1: 111371
- full erase required: YES
- bytes to program after erase: 310

Recovery original contains 111410 bytes != FF, so after a full-chip erase only those bytes need Byte Program.

## Recommended bench dry-run
```powershell
py .\pc_tool\sda555xfl_plan.py info COM9
py .\pc_tool\sda555xfl_plan.py id COM9
py .\pc_tool\sda555xfl_plan.py planbyte COM9 0x1234 0x5A
py .\pc_tool\sda555xfl_plan.py planerase COM9
py .\pc_tool\sda555xfl_plan.py image-plan COM9 ..\images\standalone_first_screen_vcs_128k.bin --recovery ..\images\RECOVERY_original_128k.bin --out plan_vcs.json
```
No destructive command is sent by any of those commands.

## Gate before v0.5
Real erase/program remains disabled until recovery, DQ7/DQ6 timeout handling, all-FF erase verification and full SHA-256 readback are all implemented together.
