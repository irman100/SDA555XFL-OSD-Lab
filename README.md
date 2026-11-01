# SDA555XFL OSD Lab

**От обратной разработки телевизионного OSD к собственной автономной графической и игровой платформе.**  
**From reverse-engineering a television OSD processor to a standalone graphics and retro-gaming platform.**

[Русский](#русский) · [English](#english) · [Документация / Documentation](#документация--documentation)

---

## Русский

SDA555XFL OSD Lab — аппаратно-программный исследовательский проект на базе телевизионного шасси **Sokol A-2010** и микросхемы **Micronas SDA555XFL A14 (PSDIP-52)**. Цель проекта — разобраться во встроенном OSD-процессоре, научиться формировать собственную графику, разработать интерфейс программирования Flash на STM32F103 и превратить телевизионную микросхему в небольшую автономную ретро-платформу.

### Эволюция проекта

1. **Исследование платы.** Документирование обеих сторон Sokol A-2010, SDA555XFL, штатных резисторных цепей, доступных площадок и механических ограничений.
2. **Reverse engineering OSD.** Восстановление модели экранной памяти, Pointer Arrays, GDW, CLUT и DRCS.
3. **Автономный видеовывод.** Собственные OSD-образы, тесты синхронизации и растровые символы.
4. **Собственный FPI.** Переход от ранних экспериментальных вариантов к программатору на **STM32F103**, host-инструментам и проверкам образа.
5. **Интерактивная графика.** Меню, управление ИК-пультом и Pong.
6. **Tetris / Arcade.** Игровое поле, HUD, статистика фигур, NEXT, уровни и работа с повтором управления.

### Платформа и технические ориентиры

| Подсистема | Текущая документация |
|---|---|
| Целевой чип | Micronas SDA555XFL A14, PSDIP-52 |
| Исходная плата | Телевизионное шасси Sokol A-2010 |
| Процессор | 8051-совместимое ядро |
| Встроенная Flash | До 128 КиБ |
| OSD | 40 × 25 ячеек, Character Display RAM 3000 байт |
| Графика | GDW, CLUT, DRCS |
| FPI | STM32F103 + host-side инструменты |
| Игры | IR Pong, Tetris / Arcade |

### Актуальный FPI

Текущая аппаратная конфигурация использует **STM32F103**. Актуальные сигналы и точки подключения сведены в [руководстве FPI / STM32F103](docs/STM32_FPI_CONNECTIONS_RU.md).

На фотографиях обратной стороны платы может оставаться надпись Nano от промежуточной итерации. Это часть истории проекта, а не повод ретушировать оригинал: актуальную распиновку определяет таблица STM32F103 в техническом руководстве.

### Фотографии проекта

В публикации используются только реальные фотографии и скриншоты, полученные в ходе работы: плата Sokol A-2010 с обеих сторон, две авторские фотографии FPI с аннотациями STM32F103, зона механического выреза, настоящий CRT-экран с Tetris и окно Universal FPI Flasher.

**Принцип качества:** каждый оригинал публикуется отдельным файлом в исходном разрешении. Не заменять фотографии низкокачественной матрицей кадров, контактным листом или уменьшенным коллажем. Допускаются отдельные уменьшенные превью для навигации, но они не заменяют оригинал. Полностью сгенерированные фотографии аппаратуры и игровых экранов не используются.

Исходные фото найдены и проверены; бинарные оригиналы ещё требуется добавить в assets/publication. До их загрузки здесь намеренно нет ссылок на отсутствующие файлы изображений.

### Достоверность результатов

- **Measured** — измерено прибором.
- **Observed** — непосредственно видно на фото, видео или в логе.
- **Simulated** — проверено программной моделью.
- **Pending** — требует дополнительной проверки на аппаратуре.

Фотография Tetris на CRT подтверждает визуальный вывод OSD, но не заменяет измерения RGB/sync осциллографом. Скриншот Flasher со статусом RUN OK не следует считать доказательством полного физического цикла erase/program/read-back.

### Безопасность

- Заводской дамп и recovery-копии Flash не включаются в публикационный набор.
- Разрушительные FPI-операции остаются заблокированными в стандартной конфигурации STM32F103 Engine v0.5.
- Не выполнять erase/program без отдельного разрешения, проверенной резервной копии и плана полного read-back.
- Разметка зоны выреза является исследовательской фотографией, а не размерным производственным чертежом.
- Репозиторий остаётся Private.

### Документация

- [Хронология развития проекта](docs/PROJECT_PROGRESSION_RU.md)
- [Технический обзор](docs/PROJECT_OVERVIEW_RU.md)
- [FPI: подключение STM32F103](docs/STM32_FPI_CONNECTIONS_RU.md)
- [Фотогалерея и правила качества изображений](docs/PHOTO_GALLERY_RU.md)
- [Манифест исходных фотоматериалов](docs/PUBLICATION_ASSET_MANIFEST_RU.md)
- [Сценарий презентации](docs/PROJECT_PRESENTATION_RU.md)
- [Текущий статус](docs/PROJECT_STATUS_RU.md)
- [Матрица проверок](docs/VERIFICATION_MATRIX_RU.md)

Подробная русская версия: [README_RU.md](README_RU.md).

---

## English

SDA555XFL OSD Lab is a hardware/software research project built around the **Sokol A-2010 TV chassis** and the **Micronas SDA555XFL A14 (PSDIP-52)**. The goal is to understand the built-in OSD processor, generate custom graphics, develop an STM32F103-based Flash Programming Interface, and turn a television IC into a small standalone retro-gaming platform.

### Project progression

1. **Board investigation.** Documenting both sides of the Sokol A-2010 PCB, the SDA555XFL device, resistor networks, accessible pads and mechanical constraints.
2. **OSD reverse engineering.** Reconstructing the display-memory model, Pointer Arrays, GDW, CLUT and DRCS.
3. **Standalone video.** Custom OSD firmware, sync experiments and raster glyphs.
4. **Custom FPI.** Moving from early experimental approaches to an **STM32F103** programmer, host utilities and image validation.
5. **Interactive graphics.** A custom menu, IR remote control and Pong.
6. **Tetris / Arcade.** A game board, HUD, piece statistics, NEXT preview, levels and key-repeat experiments.

### Platform at a glance

| Subsystem | Project reference |
|---|---|
| Target IC | Micronas SDA555XFL A14, PSDIP-52 |
| Original board | Sokol A-2010 TV chassis |
| CPU | 8051-compatible core |
| Embedded Flash | Up to 128 KiB |
| OSD | 40 × 25 cells, 3,000-byte Character Display RAM |
| Graphics | GDW, CLUT, DRCS |
| FPI | STM32F103 and host-side tools |
| Games | IR-controlled Pong, Tetris / Arcade |

### Current FPI hardware

The current programmer interface is based on **STM32F103**. The authoritative signal mapping and board connection points are documented in the [STM32F103 FPI guide](docs/STM32_FPI_CONNECTIONS_RU.md).

Some underside annotations may still show the word “Nano” from an earlier development iteration. It is intentionally retained as historical context in the original photograph. It does not override the current STM32F103 pin-mapping table.

### Project photography

The publication uses real project photographs and screenshots: both sides of the Sokol A-2010 PCB, the two author-annotated STM32F103 FPI views, the mechanical cutout study, the actual CRT displaying Tetris, and the Universal FPI Flasher window.

**Image-quality rule:** publish each original as a separate file at its source resolution. Do not replace the photographs with a low-resolution frame matrix, contact sheet or compressed collage. Small thumbnails may be used for navigation only; they are not substitutes for the originals. No fully AI-generated photographs of the hardware or game screens are used.

The source photographs have been located and reviewed. Their original binary files still need to be committed under assets/publication; this README deliberately avoids broken image links until that upload is complete.

### Evidence and limitations

- **Measured** — verified with measurement equipment.
- **Observed** — directly visible in a photograph, video or log.
- **Simulated** — checked using a software model.
- **Pending** — still requires hardware verification.

A CRT photograph demonstrates visible OSD output; it does not replace oscilloscope measurements of RGB and sync. A Flasher screenshot showing RUN OK is not, by itself, proof of a complete physical erase/program/read-back cycle.

### Safety

- The factory Flash dump and recovery copies are not part of the publication bundle.
- Destructive FPI operations remain compile-locked in the standard STM32F103 Engine v0.5 configuration.
- Do not erase or program Flash without explicit authorization, a verified backup and a complete read-back plan.
- The cutout annotation is a photographic study, not a dimensioned manufacturing drawing.
- The repository remains Private.

### Documentation

- [Project progression](docs/PROJECT_PROGRESSION_RU.md)
- [Technical overview](docs/PROJECT_OVERVIEW_RU.md)
- [STM32F103 FPI wiring reference](docs/STM32_FPI_CONNECTIONS_RU.md)
- [Photo gallery and image-quality rules](docs/PHOTO_GALLERY_RU.md)
- [Original photo asset manifest](docs/PUBLICATION_ASSET_MANIFEST_RU.md)
- [Presentation storyboard](docs/PROJECT_PRESENTATION_RU.md)
- [Project status](docs/PROJECT_STATUS_RU.md)
- [Verification matrix](docs/VERIFICATION_MATRIX_RU.md)

