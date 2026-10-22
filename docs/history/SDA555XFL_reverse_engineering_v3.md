# SDA555XFL — reverse engineering v3
## Цель прохода: автономный Sync Master + первый собственный экран

### Контроль образа
- Size: 131072 bytes / 0x20000
- CRC32: `B3680360`
- SHA-256: `6aa37c6d74d115eefdb52db8792b929b4104c59733485fc2c27a3402c2fce816`

---

## 1. Главная находка этого прохода

Для режима **50 Hz, 40×25** Micronas почти всё нужное уже задаёт аппаратными reset-defaults.

Документация задаёт:
- `PCLK1:PCLK0 = 0x01:0x48`, то есть `PF = 0x148 = 328`
- `VLR1:VLR0 = 0x02:0x71`, то есть `VLR = 625`
- `HPR1:HPR0 = 0x08:0x55`, то есть `HPR = 2133`

Формулы документации дают:

```text
fpixel = PF × 300 MHz / 8192
       = 12.011719 MHz

tH = HPR × 30 ns
   = 63.99000 us

fH = 15.62744 kHz

625-line interlace:
field rate ≈ 50.00781 Hz
frame rate ≈ 25.00391 Hz
```

То есть reset-defaults фактически уже образуют PAL-подобный 625/50 timing.

Это сильно упрощает первый автономный тест:
нам не нужно сначала вычислять/подбирать PLL, PCLK, HPR и VLR.

---

## 2. Заводская геометрия прекрасно согласуется с этими таймингами

В заводской прошивке:

```text
SCR1     = C0
OSD_CTRL = 0D
SDH0     = BF
SDV0     = 28
HCR1     = 14
```

### Горизонталь

`SDH = 0x0BF = 191 pixels`.

При `fpixel = 12.011719 MHz`:

```text
191 pixels = 15.901 us
```

40 колонок × 12 pixels:

```text
480 pixels = 39.961 us
```

Следовательно character area приблизительно занимает:

```text
start ≈ 15.901 us
end   ≈ 55.862 us
line  ≈ 63.990 us
```

То есть геометрия помещается в строку с хорошим запасом.

### Вертикаль

`SDV = 0x28 = 40 lines`.

Из заводского GDW:

```text
GDW = 07 00 00 00 00 58 09 66 41 08
GDW[0] = 07 -> 40 columns
GDW[6] = 09 -> CHADRC=1, CHAROM=1 -> 10 raster lines/character
```

25 rows × 10 lines = 250 raster lines.

При текущем H-period:

```text
top delay     ≈ 2.560 ms
character area≈ 15.997 ms
remaining     ≈ 1.440 ms per field
```

Иными словами, найденные настройки образуют внутренне согласованный экран 40×25.

---

## 3. Минимальный переход в Sync Master

`SCR0` находится по SFR `E2h`.

Биты:
- bit0 `MAST`
- bit1 `VCS`
- bit2 `SNC` (slave only)
- bit3 `INT`: 0 interlace, 1 non-interlace
- bit4 `VP`
- bit5 `HP`
- bits7..6 RGB/COR delay

### Вариант A: отдельные H/V

Для 625-line interlace:

```text
SCR0 = 01h
```

Это:
- `MAST=1`
- `VCS=0`
- `INT=0`
- normal H/V polarity
- no extra RGB delay

### Вариант B: composite sync

```text
SCR0 = 03h
```

Это:
- `MAST=1`
- `VCS=1`
- остальное как выше

У документации разных ревизий есть неоднозначность в описании того, на каком именно
физическом выводе PSDIP52 оказывается VCS. Поэтому программное значение ясно,
а физический pin для composite-sync нужно подтвердить одним низковольтным bench-test.

Для обычного VS на P4.7 документация требует:
- `P4_7_Alt = 1`
- `VS_OE = 1`
в `CSCR0`.

По расположению битов это маска `0x0C`.

---

## 4. Важная деталь по портам

Для secondary function P3 вывод должен иметь `1` в port latch.

Поэтому в минимальной автономной прошивке перед включением master sync разумно явно:

```asm
SETB P3.5
```

а для P4.7:

```asm
SETB P4.7
```

и затем включить его alternate function через CSCR0.

---

## 5. OSD/XRAM: заводскую карту сохраняем

Заводской шаблон из Flash начинается с:

```text
ROM 8F5F:
48 F4 10 C4 06 C4 07 00 00 00 00 58 09 66 41 08 00 10 00 1F F0 10 F0 1F 07 10 0F 1F 7F 10 FF 1F
```

После копирования в XRAM:

```text
C400: 48 F4 -> Display RAM pointer = F448
C402: 10 C4 -> CLUT pointer        = C410
C404: 06 C4 -> GDW/Cursor pointer  = C406

C406..C40F GDW:
07 00 00 00 00 58 09 66 41 08

C470: 76 C4 -> 1-bit DRCS pointer  = C476
C472: 50 CC -> 2-bit DRCS pointer  = CC50
C474: 16 CA -> 4-bit DRCS pointer  = CA16
```

Эту память в первом эксперименте лучше не перестраивать вообще.

---

## 6. Формат одного символа теперь можно кодировать напрямую

Каждое знакоместо = 24-bit CDW = 3 последовательных байта.

Из таблицы Micronas:

```text
bits  0.. 9 = CHAR[9:0]
bit      10 = FLASH
bit      11 = UH
bit      12 = DH
bit      13 = DW
bit      14 = BOX
bits 15..17 = CLUT[2:0]
bits 18..20 = FG[2:0]
bits 21..23 = BG[2:0]
```

Следовательно:

```text
byte0 = CHAR[7:0]

byte1:
  bit0..1 = CHAR[9:8]
  bit2    = FLASH
  bit3    = UH
  bit4    = DH
  bit5    = DW
  bit6    = BOX
  bit7    = CLUT0

byte2:
  bit0..1 = CLUT1..2
  bit2..4 = FG0..2
  bit5..7 = BG0..2
```

Для простого steady ROM character, subCLUT0, white foreground, black background:

```text
FG=7
BG=0
CLUT=0
attributes=0

byte0 = CHAR & FF
byte1 = (CHAR >> 8) & 03
byte2 = 1C
```

То есть после выяснения кода ROM-символа мы уже можем писать его прямо в `F448 + row*120 + col*3`.

---

## 7. Более надёжный первый экран — не "HELLO", а DRCS test glyph

Для первого аппаратного теста лучше вообще не зависеть от таблицы ROM-шрифта.

План:
1. сохранить заводской XRAM layout;
2. в 1-bit DRCS area записать один простой собственный glyph;
3. поместить его character address в одну/несколько CDW;
4. выбрать белый FG / чёрный BG;
5. включить `OSD_CTRL`;
6. включить master sync.

Так мы одновременно проверим:
- XRAM writes;
- display fetch;
- DRCS fetch;
- RGB DAC;
- pixel clock;
- H/V sync;
- правильность CDW.

---

## 8. Предлагаемая последовательность первого автономного boot

Пока это **dry-run plan**, не образ для записи.

```asm
; power-on/reset defaults уже дают:
; PCLK = 0x0148
; HPR  = 0x0855
; VLR  = 0x0271

; 1. Заводские pointer arrays
MOV F6h,#00h
MOV F5h,#04h
MOV F4h,#70h
MOV F3h,#04h

; 2. Скопировать заводской OSD template 8F5F -> XRAM C400...
;    либо воспроизвести только минимально нужные структуры.

; 3. DAC / OSD positioning — берём заводские значения
MOV E1h,#C0h       ; SCR1
MOV E6h,#BFh       ; SDH0
MOV E4h,#28h       ; SDV0
MOV E7h,#14h       ; HCR1

; 4. Secondary sync port latches = 1
SETB P3.5
SETB P4.7

; 5. Для отдельного VS на P4.7
ORL DDh,#0Ch       ; CSCR0: P4_7_Alt + VS_OE

; 6. Display generator
MOV F8h,#0Dh       ; заводское OSD_CTRL

; 7. Включить master sync ПОСЛЕДНИМ
MOV E2h,#01h       ; separate H/V
; или 03h для VCS/composite-sync candidate
```

Master включаем последним, чтобы все указатели, XRAM и OSD уже были готовы.

---

## 9. Что ещё не считаю доказанным

1. Точный физический output pin для `VCS` именно у нашего PSDIP52/ревизии:
   документация содержит смешанные формулировки.
2. Точный ROM character number для ASCII-подобных `A..Z`.
3. Минимальный объём заводского OSD template, который действительно обязан быть загружен.
4. Нужен ли нам `PSAVE=07h` или достаточно оставить reset state для собственного minimal boot.
5. Нужно отдельно проверить состояние PLL/display power-save после собственного reset-path.

До ответа на эти пять пунктов я не рекомендую формировать прошивку для записи.

---

## 10. Вывод прохода

Самое важное изменение картины:

**Sync Master намного проще, чем ожидалось.**

Для 40×25 @ 50 Hz чип уже после reset имеет:
- правильный pixel clock около 12 MHz;
- H period около 64 us;
- VLR=625.

Заводская прошивка добавляет в основном позиционирование OSD и включает display generator.

Поэтому первый собственный автономный экран выглядит реалистичным без сложной
инициализации PLL и без внешнего TDA8842.
