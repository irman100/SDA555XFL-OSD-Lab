# SDA555XFL — reverse engineering v4
## DRCS, PSAVE, точный Sync pinout и проект первого автономного экрана

### Контроль образа
- Size: 131072 bytes / 0x20000
- CRC32: `B3680360`
- SHA-256: `6aa37c6d74d115eefdb52db8792b929b4104c59733485fc2c27a3402c2fce816`

---

## 0. Важная коррекция к v3

В v3 была слишком смелая привязка master-sync к P3.5/P4.7.

Для **PSDIP52 нашего SDA555XFL** это неверно.

Официальный pinout PSDIP52 показывает отдельные выводы:

- pin 19 = `HS/SSC`
- pin 20 = `VS`
- pin 38 = `R`
- pin 39 = `G`
- pin 40 = `B`
- pin 41 = `BLANK/COR`

А в Sync System manual сказано:

- `SCR0.MAST=1` переводит **H и V pins** в output;
- `SCR0.VCS=1` выводит composite sync именно на **V pin**.

Следовательно для нашего PSDIP52:

```text
H-sync output       -> pin 19 HS/SSC
V-sync output       -> pin 20 VS
Composite sync VCS  -> pin 20 VS, when SCR0.VCS=1
```

`P4.7` в user manual относится к дополнительной альтернативной функции на других
вариантах корпуса/ядра. На pinout PSDIP52 отдельного P4.7 вообще нет.

Это снимает самую неприятную неоднозначность предыдущего прохода.

---

## 1. PSAVE=07h в заводской прошивке НЕ надо повторять для первого экрана

`PSAVE` (SFR D8h) после reset = `00h`.

Низшие биты:

```text
bit0 PERI
bit1 DISP
bit2 SLI_ACQ
```

По user manual, `DISP=1` переводит в power-save:

- display generator
- pixel clock
- display sync unit
- DAC
- COR/BLANK logic

Именно поэтому заводское `MOV PSAVE,#07h` нельзя трактовать как обязательную
часть включения OSD. Наоборот — это отключает display-подсистему и используется
штатной телевизионной программой для энергосбережения в отдельных состояниях.

В заводском образе действительно присутствуют разные записи:

```text
PSAVE = 00h
PSAVE = 01h
PSAVE = 07h
PSAVE = 1Fh
```

и отдельные CLR/SETB для его битов.

### Для нашего minimal standalone boot

```text
PSAVE  = 00h
PSAVEX = 00h
```

То есть display/DAC/PLL оставляем активными.

---

## 2. DRCS layout теперь восстановлен математически и совпадает байт-в-байт

Заводской GDW:

```text
07 00 00 00 00 58 09 66 41 08
```

`GDW[6]=0x09` -> CHADRC = 1 -> **10 raster lines**.

`GDW[7]=0x66`:

```text
DRCSB1 = 6 -> boundary1 = 864
DRCSB2 = 6 -> boundary2 = 864
```

Поскольку обе границы одинаковы:

```text
768..863  -> 1-bit DRCS
864..863 -> 2-bit DRCS (пустой диапазон)
864..1023 -> 4-bit DRCS
```

### 1-bit DRCS

10 lines × 12 pixels × 1 bit = 120 bits = **15 bytes/character**.

Count:

```text
864 - 768 = 96 characters
96 × 15 = 1440 bytes = 0x5A0
```

Factory pointer:

```text
DRC1POINT = 0xC476
0xC476 + 0x5A0 = 0xCA16
```

Следующий заводской DRCS pointer:

```text
DRC4POINT = 0xCA16
```

То есть 1-bit область занимает **ровно `0xC476..0xCA15`**
и заканчивается точно перед `DRC4POINT`.

Это сильное независимое подтверждение нашей расшифровки GDW и pointer arrays.

### 4-bit DRCS

2-bit диапазон пуст, потому что boundary1 == boundary2.

4-bit:

```text
1024 - 864 = 160 characters
10 × 12 × 4 bit = 60 bytes/character
160 × 60 = 9600 bytes
```

С `DRC4POINT=0xCA16` это даёт:

```text
0xCA16 .. 0xEF95
```

`DRC2POINT=0xCC50` в этой конфигурации не описывает активный 2-bit диапазон,
поэтому его положение внутри этого пространства не противоречит карте.

---

## 3. Точный packing 1-bit DRCS

Manual задаёт 12 pixels на строку.

Для пары raster lines:

```text
byte +0:
  bit7..0 = line N, pixels 0..7

byte +1:
  bit7..4 = line N,   pixels 8..11
  bit3..0 = line N+1, pixels 0..3

byte +2:
  bit7..0 = line N+1, pixels 4..11
```

Для 10 raster lines это 5 пар × 3 bytes = **15 bytes**.

---

## 4. Готов тестовый 12x10 DRCS glyph

Для первого экрана предлагаю не зависеть от ROM charset.

Glyph #768:

```text
111111111111
100000000001
101000000101
100100001001
100010010001
100001100001
100010010001
100100001001
101000000101
111111111111
```

Encoded bytes:

```text
FF F8 01 A0 59 09 89 18 61 89 19 09 A0 5F FF
```

Его надо положить в:

```text
DRC1POINT = 0xC476
character address = 768 = 0x300
```

То есть эти 15 bytes занимают:

```text
0xC476..0xC484
```

---

## 5. Character Display Word для glyph 768

Для ROM/1-bit DRCS:

```text
CHAR = 768 = 0x300
CLUT = 0
FG = 7
BG = 0
FLASH/UH/DH/DW/BOX = 0
```

Три bytes CDW:

```text
00 03 1C
```

Почему это удобно:

- subCLUT0 использует hardwired CLUT entries 0..7;
- hardwired entry 0 = black;
- hardwired entry 7 = full white;
- поэтому программируемую CLUT для первого теста вообще можно не заполнять.

Для невидимой фоновой ячейки можно использовать тот же glyph, но `FG=0`, `BG=0`:

```text
00 03 00
```

Тогда и нулевые, и единичные pixels будут black.

---

## 6. Минимальная XRAM-конфигурация первого экрана

Сохраняем заводские pointer values:

```text
C400 = 48 F4  ; display -> F448
C402 = 10 C4  ; CLUT -> C410
C404 = 06 C4  ; GDW/cursor -> C406

C470 = 76 C4  ; 1-bit DRCS -> C476
C472 = 50 CC  ; 2-bit DRCS -> CC50 (inactive)
C474 = 16 CA  ; 4-bit DRCS -> CA16
```

GDW оставляем заводской:

```text
C406..C40F = 07 00 00 00 00 58 09 66 41 08
```

Для первого теста не требуется загружать все 1126 bytes заводского template.
Минимально необходимы:

1. pointer arrays;
2. 10-byte GDW;
3. наш 15-byte DRCS glyph;
4. Character Display RAM.

CLUT programmable area можно не инициализировать, потому что FG/BG выбираются из
hardwired entries 0..7.

---

## 7. Display RAM

`DISPOINTh = F448`.

40 × 25 × 3 = 3000 bytes, до `FFFF` включительно.

Безопасная последовательность:

1. заполнить все 1000 cells чёрным:
   `00 03 00`;
2. в центре экрана записать несколько cells:
   `00 03 1C`.

Например прямоугольник 8×3 из нашего тестового glyph.

Адрес cell:

```text
F448 + (row*40 + col)*3
```

---

## 8. Минимальные SFR для собственного OSD

На основе reset defaults + заводской конфигурации:

```text
PSAVE  D8 = 00   ; display/DAC active
PSAVEX D7 = 00   ; PLL active, normal source

SCR1   E1 = C0   ; reserved bit + RGB gain 1.0 V, factory value
SDV0   E4 = 28   ; factory vertical display delay
SDH0   E6 = BF   ; factory horizontal display delay
HCR1   E7 = 14   ; factory clamp setting

POINTARRAY1 H/L F3/F4 = 04/70
POINTARRAY0 H/L F5/F6 = 04/00

OSD_CTRL F8 = 0D ; GDW download enabled + display generator enabled
```

### Sync Master

Separate H/V:

```text
SCR0 E2 = 01
pin 19 = H
pin 20 = V
```

Composite sync:

```text
SCR0 E2 = 03
pin 19 = H
pin 20 = VCS composite sync
```

Для первого bench-test я предпочитаю **03h**, потому что один pin 20 сразу даёт
composite sync для последующего SCART-интерфейса. Pin 19 остаётся полезен как H-sync
для осциллографической проверки.

---

## 9. Что больше НЕ требуется в minimal boot

Для PSDIP52 не нужны:

```text
SETB P3.5
P4.7 alternate mode
CSCR0 P4_7_Alt / VS_OE
```

Это было ошибочным ответвлением v3.

Dedicated H/V pins у нашего корпуса уже существуют отдельно.

---

## 10. Первый автономный код теперь можно сделать действительно маленьким

Последовательность:

```text
RESET
 -> SP
 -> PSAVE=0 / PSAVEX=0
 -> pointer arrays
 -> write pointer tables into XRAM
 -> write 10-byte GDW
 -> write 15-byte 1-bit DRCS glyph #768
 -> clear 1000 CDW cells to black
 -> draw test rectangle with CDW 00 03 1C
 -> SCR1/SDH/SDV/HCR
 -> OSD_CTRL=0D
 -> SCR0=03 LAST
 -> infinite loop
```

`SCR0=03` ставим последним: переход slave->master сбрасывает внутренние H/V counters,
а к этому моменту display memory уже полностью готова.

---

## 11. Что осталось до первого flashable test image

Теперь список стал коротким:

1. собрать этот minimal boot в реальные opcodes 8051;
2. проверить все direct-SFR addresses по user manual;
3. проверить MOVX-доступ к XRAM `C400..FFFF`;
4. сделать эмуляционную/статическую проверку generated binary;
5. подготовить **полный 128-KiB recovery image** на базе original_1.bin;
6. только после этого отдельно реализовывать FPI program/erase.

Важно: Flash manual описывает full-chip erase. Поэтому прежде чем вообще включать запись,
нам нужен путь полного восстановления исходного 128-KiB образа.

На текущем проходе ERASE/PROGRAM по-прежнему не добавлялись.
