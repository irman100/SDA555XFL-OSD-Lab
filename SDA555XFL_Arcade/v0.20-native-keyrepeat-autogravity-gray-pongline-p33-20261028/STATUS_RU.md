# Статус v0.20

Ветка: `release/arcade-v0.20-native-keyrepeat-autogravity-gray-pongline-p33-20261028`

## Что реально исправлено
1. В v0.18/v0.19 таймерный обработчик был подключён к Pong-циклу `0x0969`, поэтому Tetris не получал обработку. Теперь `0x096F` вызывает composite helper `0x9260`.
2. На входе Tetris `0x0C3D` установлен key dispatcher `0x927C`. Первый ←/→ делает ровно один шаг; удержание — после 10 игровых тактов, затем каждые 3 такта. Коды отпускания `0x5E/0x5A` снимают latch. ↓ — один шаг сразу, повторы через 2 такта; release `0x5F`.
3. Автогравитация: 18 тактов на level 1, один такт на level 18; используется штатный row-step `0x1739`.
4. Pong separator `:` -> `.`, ROM `0x14E3`. Фоновая плитка светло-серая, CLUT не изменена.
5. Таймер удержания — RAM `0x39/0x3A`, сбрасывается при старте Tetris `0x1528`; scanner RAM `0x49` и сам scanner не менялись.

## Отчёт
- BIN: 131072 bytes, CRC32 `CB2AB894`, SHA-256 `b1e0fed4315c6a829731ce3e80786797470267c3aca1bb8f6b2d784f1ce5943e`.
- Bounded 8051 simulation: PASS. Repeat tick calls include the input frame: left `[11,14,17]`, right `[11,14]`, down `[3,5,7]`. Same key re-arms after release.
- Geometry: 28 cases; levels: 18; changed bytes outside allowed ranges: 0.
- Physical TV test: NO. Full 8051 emulation: NO. Flash written: NO.
- GitHub CI checks on docs commit: not yet available.
