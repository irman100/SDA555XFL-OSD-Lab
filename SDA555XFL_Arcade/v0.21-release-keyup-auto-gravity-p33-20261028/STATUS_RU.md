# Статус v0.21 — исправление отпускания кнопок

Ветка: `release/arcade-v0.21-release-keyup-auto-gravity-p33-20261028`

## Патч
- Хук главного события ввода по offset `0x0947`: `LCALL 0x0B36` → `LCALL 0x9272`.
- Helper `main_key_event_dispatch` перехватывает release-код только если он соответствует установленному latch:
  - `0x5E` + `RAM[0x39] == 0x1E` (←)
  - `0x5A` + `RAM[0x39] == 0x1A` (→)
  - `0x5F` + `RAM[0x39] == 0x1F` (↓)
- Совпадающий key-up сбрасывает `RAM[0x39]` и `RAM[0x3A]`, затем сразу возвращается; он больше не зависит от попадания в Tetris-specific handler `0x0C3D`.
- Любое несовпадающее событие передаётся оригинальному `0x0B36`.
- Основной loop hook на `0x096F`, Pong hook на `0x0969), клавиатурный scanner `0x1B70..0x1C17` оставлены без изменений.

## Результаты
- BIN: 128 KiB, CRC32 `5F511561`, SHA-256 `e1968394c4afc2b1027947c258a0dc82f1494529bcd1eb65f11fc5a6cc57b435`.
- Release ZIP, firmware-only ZIP, source bundle: ZIP-integrity PASS.
- В bounded 8051 simulator выполнены настоящие инструкции wrapper helper: все три совпадающих release сбрасывают latch/timer и не вызывают старый router; unrelated key-up передаётся в старый router и не сбрасывает latch.
- Повтор ←/→, повтор ↓, повторное нажатие после отпускания и автогравитация продолжают проходить проверки.
- Changed bytes outside declared patch spans: 0.
- Physical TV test: NO; full 8051 runtime: NO; Flash written: NO.
