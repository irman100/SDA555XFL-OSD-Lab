# SDA555XFL OSD Lab — статус на 1 ноября 2026

## Общая стадия
Проект прошёл путь от анализа платы и заводской OSD-структуры к автономному OSD, собственной связке STM32F103 FPI, меню, Pong и Tetris/Arcade.

## Последняя подтверждённая линия работ
- SDA555XFL A14, PSDIP-52 на плате Sokol A-2010.
- Восстановлена OSD geometry 40 × 25, 1000 ячеек, 3 байта/ячейку, Display RAM 3000 байт.
- Обнаружены/описаны Pointer Arrays, GDW, CLUT, DRCS.
- Standalone bench observations: H-sync около 15,625 кГц, V-sync около 50 Гц.
- Созданы standalone OSD v5 и диагностические v6 варианты.
- Исторический v5 VCS image документирован с полным read-back: CRC32 E0123039; SHA-256 8527dd1f0fd8b5fbb1539d4cae1e6a9133a6d37853f47aef212054cf24b7748b.
- Разработан STM32F103 FPI Engine v0.5, host utilities и compile-lock destructive операций.
- Созданы меню, Pong с ИК-управлением и Tetris/Arcade.
- Фото 01.11.2026 подтверждает вывод Tetris OSD на CRT.
- В Universal FPI Flasher screenshot выбран образ 131072 байта, CRC32 8AB10F0B, статус RUN OK; один screenshot не является доказательством полного erase/program/read-back.

## Текущий FPI hardware reference
- Текущая архитектура: STM32F103.
- Arduino Nano mapping устарел.
- Точная таблица и сигналы: docs/STM32_FPI_CONNECTIONS_RU.md.
- Два актуальных annotated source photos предоставлены автором; original PNG files должны быть добавлены в assets для прямого отображения на GitHub.
- R117/R118 не трогать; pin 51 NC по аннотации.

## Arcade v0.22 — P3.3
- BIN 131072 bytes; CRC32 8AB10F0B.
- SHA-256 5d5c127dedc82796cb930943b10adb4c89128b8bcc29b107e7e98d8eeae476ad.
- Helper-level tests проходят; полного 8051/IR runtime и физического подтверждения timing с конкретным пультом нет.
- Последующая аппаратная проверка автогравитации, DAS/soft-drop и отпускания ИК-кнопок требуется отдельно.

## Следующие задачи
1. Проверить Tetris controls and gravity на реальном телевизоре и реальном пульте.
2. Для актуального Arcade image провести полный read-back только если запись отдельно разрешена.
3. Измерить RGB, BLANK/COR и sync с корректной нагрузкой.
4. Завершить физические размеры cutout/clearance.
5. Добавить два STM32 FPI annotated PNG в assets и обновить PPTX/PDF только реальными фотографиями.

## Safety
Оригинальный заводской ROM и recovery-копии не коммитить. FPI Engine v0.5 destructive operations compile-locked по умолчанию. Не разблокировать erase/program без проверенного target profile, backup и полного read-back плана.
