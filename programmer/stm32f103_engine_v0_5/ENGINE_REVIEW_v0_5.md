# SDA555XFL FPI Engine v0.5

## Статус

В v0.5 реальный SST39LF/VF010 programming/recovery engine уже присутствует в
исходнике STM32, но поставляемая сборка **compile-locked**:

```text
ALLOW_DESTRUCTIVE_FPI=0
```

То есть при обычной сборке через приложенный `platformio.ini` реальные
`ARM / ERASEGO / PROGRAMIMAGE` не могут выполнить destructive WR.

## Что реализовано в engine source

### Flash identity gate
Перед destructive session firmware требует Software ID:

```text
BF D5
```

### Live CRC gate
`ARM current_crc target_crc` сам перечитывает все 128 KiB и сравнивает live CRC
с ожидаемым current CRC.

### Chip Erase
Реализована точная подтверждённая последовательность SST:

```text
5555 AA
2AAA 55
5555 80
5555 AA
2AAA 55
5555 10
```

После неё:
1. DQ7/DQ6 polling;
2. два дополнительных контрольных чтения;
3. полный проход 128 KiB — каждый байт должен быть `FF`;
4. дополнительный full-array CRC32.

### Byte Program

```text
5555 AA
2AAA 55
5555 A0
ADDR DATA
```

До команды проверяется, что операция не требует ни одного перехода `0 -> 1`.
После неё:
1. DQ7;
2. DQ6;
3. два дополнительных чтения;
4. exact byte read-back.

### Full-image programming
`PROGRAMIMAGE` принимает ровно 128 KiB бинарного потока.
Байты `FF` пропускаются.
Если программирование одного байта не прошло, STM32 всё равно дочитывает остаток
binary stream, чтобы UART не потерял framing, и только затем возвращает ошибку.

После потока проверяются:
- CRC32 входного image;
- полный CRC32 реально записанной Flash.

### Interlocks
Кроме compile lock предусмотрены:
- ID `BF D5`;
- live-current CRC;
- target CRC;
- отдельная `ARM`-сессия;
- magic `SST39_BFD5_ERASE`;
- magic `SST39_BFD5_PROGRAM`;
- повторный live CRC непосредственно перед erase;
- generic `WRITE/PROGRAM/ERASE` не используются.

## Polling

Текущий SST datasheet задаёт:
- Byte Program maximum: 20 us;
- Chip Erase maximum: 100 ms;
- DQ7 = complement true D7 while Program busy;
- DQ7 = 0 while Erase busy;
- DQ6 toggles while Program/Erase busy;
- после потенциального asynchronous completion нужны два дополнительных reads.

v0.5 реализует именно этот подход.

## Simulation

Полный цикл был прогнан программной моделью:

```text
original
 -> full chip erase
 -> program VCS test image
 -> full target verify
 -> full chip erase
 -> program original recovery
 -> full recovery verify
```

Result: **PASS**

### Original
- CRC32: `B3680360`
- SHA-256: `6aa37c6d74d115eefdb52db8792b929b4104c59733485fc2c27a3402c2fce816`

### First-screen VCS
- programmed non-FF bytes: 310
- CRC32: `E0123039`
- SHA-256: `8527dd1f0fd8b5fbb1539d4cae1e6a9133a6d37853f47aef212054cf24b7748b`

### Recovery
- programmed non-FF bytes: 111410
- CRC32: `B3680360`
- SHA-256: `6aa37c6d74d115eefdb52db8792b929b4104c59733485fc2c27a3402c2fce816`

### Negative Flash-physics test
`PASS: illegal 0->1 rejected`

Иными словами, модель отдельно доказала, что recovery полностью возвращается к
нашему эталонному SHA-256.

## Static safety audit

Result: **PASS**

Проверки:
- PASS — `compile_lock_default_in_source`
- PASS — `safe_platformio_flag`
- PASS — `proven_id_BF_D5`
- PASS — `program_sequence_present`
- PASS — `erase_sequence_present`
- PASS — `dq7_dq6_polling_present`
- PASS — `full_ff_verify_present`
- PASS — `full_crc_verify_present`
- PASS — `binary_stream_drain_on_failure`
- PASS — `magic_erase_interlock`
- PASS — `magic_program_interlock`
- PASS — `generic_write_not_exposed`

## Что делаем на реальном STM32 сейчас

Пока только прошиваем безопасную v0.5 (`ALLOW_DESTRUCTIVE_FPI=0`) и проверяем:

```powershell
py .\pc_tool\sda555xfl_engine_v0_5.py audit-firmware `
  .\firmware_stm32f103\src\main.c `
  .\firmware_stm32f103\platformio.ini

py .\pc_tool\sda555xfl_engine_v0_5.py simulate-cycle `
  .\images\RECOVERY_original_128k.bin `
  .\images\standalone_first_screen_vcs_128k.bin `
  .\images\RECOVERY_original_128k.bin
```

На железе можно дополнительно проверить `INFO`, `ID5555`, `READ`, `PLANBYTE`,
`PLANERASE`, `ENGINESTATUS`.

При safe build:
`ARM`, `ERASEGO`, `PROGRAMIMAGE` обязаны отвечать `ERR COMPILE_LOCK`.

Реальный erase в этом проходе **не запускаем**.
