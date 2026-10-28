# SDA555XFL Arcade v0.21 — Release-Keyup Fix / Auto Gravity / Gray Pongline (P3.3)

## Исправление залипания после отпускания

В v0.20 коды отпускания проверялись только внутри Tetris-specific обработчика `0x0C3D`. Однако общий режимный диспетчер `0x0B36` не обязан проводить key-up событие через эту ветку, поэтому latch `RAM[0x39]` мог оставаться установленным, а Tetris продолжал повторять движение даже после физического отпускания кнопки.

В v0.21 обработка перенесена на реальную верхнюю точку событий клавиатуры:
- В основном цикле вызов `LCALL 0x0B36` по ROM offset `0x0947` заменён на `LCALL 0x9272` (`main_key_event_dispatch`).
- Совпадающие коды отпускания перехватываются до общего режимного диспетчера: `0x5E` для ← при latch `0x1E`, `0x5A` для → при latch `0x1A`, `0x5F` для ↓ при latch `0x1F`.
- При совпадении сразу очищаются `RAM[0x39]` и `RAM[0x3A]`; release событие не передаётся в старую ветку, где оно могло быть проигнорировано.
- Все остальные события без изменения идут в оригинальный `0x0B36`. Сканер `0x1B70..0x1C17` не менялся.
- Tetris-specific обработчик и frame timer сохраняют поведение v0.20: первый шаг сразу, ←/→ повтор после 10 игровых тактов, затем раз в 3 такта; ↓ выполняет soft-drop и повторяет раз в 2 такта; автогравитация действует независимо.

## Проверки
- Build: PASS; Python syntax: PASS; bounded 8051 helper simulation: PASS.
- BIN: 131072 bytes, CRC32 `5F511561`, SHA-256 `e1968394c4afc2b1027947c258a0dc82f1494529bcd1eb65f11fc5a6cc57b435`.
- Полный release ZIP SHA-256: `de92893e80ab3487963c260c949df7daae824f7fb39f157751541fb3fdcf5cd9`.
- Firmware-only ZIP SHA-256: `79183d9aad449aedccf48a0831f26be60347ba6d902f0cfe5a567e417b86eb97`.
- Source bundle SHA-256: `1841bcc8c850b7b2f2d86fbe6d6c0f9e9029215b9672a1c2f9620bad9694c126`.
- ZIP integrity: PASS for all three archives; firmware bytes inside archives match standalone BIN.
- The bounded helper test executes release dispatcher bytecode for left/right/down and confirms only a release matching the currently held key clears latch/timer before `0x0B36`. Unrelated key-up is forwarded to original dispatcher. Tetris auto gravity and repeat tests remain passing. No unexpected modified ROM bytes outside declared patch ranges.

## Ограничения
- Полный CPU/IR runtime и телевизор не эмулировались. Коды отпускания основаны на штатном scanner code path; после установки следует проверить прекращение автоповтора при отпускании физической клавиши.
- Flash не записывалась. Перед аппаратной проверкой сохранить полный дамп Flash.
- Этот BIN предназначен для варианта платы P3.3.

Исходный ROM: `sda555xfl_arcade_v0_12_P33_128k.bin`, SHA-256 `09f59d40672278b5ccd56c241f769ed6bf4c55b191a7e18727e63c2ac1065896`.
