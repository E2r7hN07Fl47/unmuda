#!/usr/bin/env python3
"""unlock_chkcode.py — запись сервисной магии LOOTBFCK в chkcode (шаг анлока).

ЧТО ДЕЛАЕТ (проверено на A101BM 1.280PO.0686.a):
  пишет 8 байт 'LOOTBFCK' (0x4C4F4F54 + 0x4246434B LE) по смещению 0
  раздела chkcode. Загрузчик (ABL) при KcFastbootCheck()==TRUE:
    1) регистрирует ПОЛНУЮ таблицу fastboot-команд (flash/erase/boot/...);
    2) пропускает проверки IsUnlocked/IsCriticalPartition внутри flash/erase;
    3) ПОБОЧНОЕ ДЕЙСТВИЕ: при каждой загрузке входит в fastboot-режим
       (BootIntoFastboot=TRUE) — Android сам НЕ ЗАГРУЗИТСЯ, пока магия
       не снята! Возврат: fastboot flash chkcode нулей (см. guide/05).

Скрипт отказывается работать без
существующего бэкапа chkcode рядом (п1 чек-листа).
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from diag_transport import open_transport
from fs_sys_call import FSDiag, O_RDWR, SEEK_SET

CHKCODE_PATH = "/dev/block/bootdevice/by-name/chkcode"
MAGIC = b"LOOTBFCK"
CHUNK = 0x400


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backup", default="chkcode_backup.bin",
                    help="файл бэкапа (обязателен; создаётся backup_chkcode.py)")
    ap.add_argument("--yes", action="store_true", help="не спрашивать подтверждение")
    a = ap.parse_args()

    backup = Path(a.backup)
    if not backup.exists():
        print(f"ОТКАЗ: нет бэкапа {backup}. Сначала запустите backup_chkcode.py "
              "(без бэкапа — никак).", file=sys.stderr)
        return 2

    if not a.yes:
        print("Запись LOOTBFCK включит сервисный режим: телефон будет ВСЕГДА")
        print("загружаться в fastboot, пока магия не снята. Продолжить? [yes/N]")
        if input().strip().lower() != "yes":
            print("Отменено.")
            return 1

    tr = open_transport()
    fs = FSDiag(tr)
    fd = fs.open(CHKCODE_PATH, O_RDWR)
    try:
        fs.lseek(fd, 0, SEEK_SET)
        n = fs.write(fd, MAGIC)
        if n != len(MAGIC):
            print(f"ОТКАЗ: записано {n} байт вместо {len(MAGIC)}", file=sys.stderr)
            return 1
        fs.lseek(fd, 0, SEEK_SET)
        back = fs.read(fd, 16)
        print("Контрольное чтение (первые 16):", back.hex(" "))
        if back[:8] != MAGIC:
            print("ОШИБКА: магия не подтвердилась! Восстановите бэкап:", file=sys.stderr)
            print(f"  python fs_sys_call.py {CHKCODE_PATH} ... (см. guide/05)", file=sys.stderr)
            return 1
        print("OK: LOOTBFCK записан и подтверждён.")
        print("Далее: adb reboot bootloader -> fastboot flashing unlock ->")
        print("подтвердить ГРОМКОСТЬ ВВЕРХ на экране телефона. См. guide/04.")
    finally:
        fs.close(fd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
