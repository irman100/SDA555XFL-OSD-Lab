# SDA555XFL Flash Command Set — RE v6

## Итог документального прохода

Официальный Micronas `6251-556-2AN` доказывает свойства интерфейса, но **не публикует
unlock-addresses/data**. Он говорит:

- Flash до 128 KiB;
- JEDEC-compatible command set;
- Program = 4 write cycles;
- Chip erase = 6 write cycles;
- erase: two unlock writes → setup → two unlock writes → erase confirm;
- program: two unlock writes → program setup → data write;
- D7 показывает окончание erase/program;
- отдельного VPP не требуется;
- точные command addresses/data вынесены в "appropriate flash specification".

Этого недостаточно, чтобы честно выбрать между несколькими JEDEC 1-Mbit x8 семействами.

## Реальные кандидаты

### SST39LF/VF010
- 128K x8, 2.7/3.0–3.6 V;
- JEDEC;
- Program: `5555 AA, 2AAA 55, 5555 A0, PA PD`;
- Chip erase: `5555 AA, 2AAA 55, 5555 80, 5555 AA, 2AAA 55, 5555 10`;
- Software ID entry: `AA/55/90` at `5555/2AAA`;
- Manufacturer/device: `BF D5`;
- DQ7 polling.

### Atmel AT49BV/LV010
- same `5555/2AAA` unlock convention;
- same 4-cycle byte program and 6-cycle chip erase shape;
- Software ID: `1F 17`.

### AMD Am29LV010B
- 128K x8, 3-V family;
- same command data bytes and 4/6-cycle shape;
- unlock convention is `0555/02AA`;
- Software ID: `01 6E`.

### ST M29W010B
- 128K x8, 2.7–3.6 V;
- 100k program/erase cycles;
- same 4/6-cycle shape and DQ7/toggle status;
- unlock convention `0555/02AA`;
- Electronic Signature: `20 23`.

## Вывод

По одному только Micronas manual нельзя доказать, что embedded macro именно SST,
AMD, Atmel или ST-compatible: несколько реальных устройств совпадают по внешнему
описанию.

Поэтому "точный command set" нужно доказать **неразрушающим Software ID probe**.

## Безопасный ID probe v0.3

Подготовлена отдельная STM32 firmware.

Она умеет только:

- обычное чтение FPI;
- Software ID entry:
  - `AA`
  - `55`
  - `90`
- выход/reset:
  - `F0`

В исходнике **нет** последовательностей:
- `A0` — Byte Program setup;
- `80` — Erase setup;
- `10` — Chip Erase confirm;
- `30` — Sector/Block Erase confirm.

Generic host WRITE отсутствует.

### Почему два режима

`ID5555`
- unlock1 = `0x5555`
- unlock2 = `0x2AAA`
- проверяет SST/Atmel-style decoding.

`ID0555`
- unlock1 = `0x0555`
- unlock2 = `0x02AA`
- проверяет AMD/ST-style decoding.

Каждый probe:

1. читает normal array bytes `00000/00001`;
2. посылает `F0`;
3. посылает только `AA/55/90`;
4. читает ID bytes `0000..0003`;
5. посылает `F0`;
6. снова читает normal bytes `00000/00001`;
7. выдаёт `IDEXIT OK` только если normal array восстановился.

Для нашего оригинала ожидаемые normal bytes:
`C2 82`.

## Как интерпретировать

Если `5555` вернёт:

- `BF D5` → SST39LF/VF010-compatible command set практически доказан;
- `1F 17` → Atmel AT49xV010-compatible command set.

Если `5555` не изменит чтение, пробуем `0555`.

Если `0555` вернёт:

- `01 6E` → AMD Am29LV010B-compatible;
- `20 23` → ST M29W010B-compatible.

Если оба режима не дадут ID:
- exact embedded macro может скрывать/не реализовывать Software ID;
- тогда следующий шаг — искать алгоритм PGS53/ChipProg/Xeltek либо делать ещё один
  строго неразрушающий behavioral test.

## Рекомендуемый порядок bench-test

Сначала перепрошить **только STM32** v0.3.
SDA555XFL Flash не стирается и не программируется.

Проверить:

```powershell
py .\pc_tool\sda555xfl_idprobe.py info COM9
```

Потом **сначала**:

```powershell
py .\pc_tool\sda555xfl_idprobe.py probe COM9 5555
```

Если ID не распознан — только тогда:

```powershell
py .\pc_tool\sda555xfl_idprobe.py probe COM9 0555
```

После каждого теста программа сама проверяет возврат к normal array.

## Статус

ERASE/PROGRAM всё ещё не реализованы.
Этот проход предназначен только для доказательства семейства embedded Flash.
