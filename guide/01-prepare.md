# 01 — Подготовка

## На кого рассчитано

Полностью автономная инструкция для Kyocera BALMUDA Phone (A101BM,
SoftBank, SoC Snapdragon 765G / SM7250 «saipan», Android 12).
Проверено на прошивке **1.280PO.0686.a** (SPL 2022-10-01).
На других версиях ядра/прошивки пути могут отличаться.

## Что понадобится (кратко; полный список — ../TOOLS.md)

- Компьютер с Linux (x86_64) **или** Windows 10/11 (x64) — без WSL.
- Python 3.9+ и пакет `pyusb`.
- platform-tools (adb + fastboot).
- Кабель USB; телефон с включённой отладкой по USB (Настройки → О телефоне →
  7 раз тапнуть номер сборки → Для разработчиков → Отладка по USB).
- На Windows — Zadig (установка WinUSB-драйвера на диаг-интерфейс).

## Проверка совместимости (2 минуты, ничего не меняет)

```bash
adb shell getprop ro.build.version.incremental   # 1.280PO.0686.a
adb shell getprop ro.build.version.security_patch  # 2022-10-01
adb shell getprop ro.product.model               # A101BM
adb shell ls /system_ext/framework/qcrilhook.jar # должен существовать
```

Если SPL ≥ 2024-05-01 — CVE-2024-31317 закрыт, способ подъёма diag-режима
из гайда 02 не сработает (потребуется иной способ переключить
`sys.usb.config`, которого в этом репозитории нет).

## Карта метода

```
Android (adb)                      USB diag,modem,adb            fastboot
    |                                    |                          |
    | CVE-2024-31317 ->                  | Kyocera DIAG-бэкдор:     |
    | setprop sys.usb.config             | 0xFC/0x2081 = shell      |
    v                                    | 0xFC/0x2000 = файлы      |
 [02-diag-mode]                          v                         |
                                    [03-backups-no-unlock]          |
                                         |  fs_sys_call:            |
                                         |  бэкап chkcode           |
                                         v                          |
                                    [04-unlock]                     |
                                         | запись LOOTBFCK +        |
                                         | flashing unlock          |
                                         v                          |
                                                              [05-restore]
                                                              снятие магии,
                                                              нормальная загрузка
```

## Железное правило (из POSTULATES)

Любая запись в разделы — только после бэкапа изменяемого раздела и только
командами из этого репозитория. В репозиторий входят и «анти-примеры»
(чего НЕ делать) — они помечены словом ОПАСНО и вставлены не для красоты.
