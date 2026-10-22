# SDA555XFL STM32F103 FPI ENGINE v0.5

Это проход с уже написанным real programming/recovery engine, но он
COMPILE-LOCKED по умолчанию.

`platformio.ini` содержит:

    -DALLOW_DESTRUCTIVE_FPI=0

Поэтому эту сборку безопасно прошивать для проверки протокола:
реальный Chip Erase / Byte Program не выполнятся.

Полный dry simulation:

    py .\pc_tool\sda555xfl_engine_v0_5.py simulate-cycle ^
      .\images\RECOVERY_original_128k.bin ^
      .\images\standalone_first_screen_vcs_128k.bin ^
      .\images\RECOVERY_original_128k.bin

На настоящем устройстве после прошивки v0.5:
- INFO / ID5555 / READ работают;
- PLANBYTE / PLANERASE работают;
- ENGINESTATUS показывает compile lock;
- ARM / ERASEGO / PROGRAMIMAGE должны вернуть ERR COMPILE_LOCK.

Реальное destructive execution в этом проходе не включать.
