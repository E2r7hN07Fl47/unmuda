#!/usr/bin/env python3
"""kdiag_shell — shell-команды на телефоне через DIAG-бэкдор Kyocera.

Механизм (проверен на A101BM 1.280PO.0686.a):
  subsys 0xFC, cmd 0x2080: system(строка)           -> код возврата
  subsys 0x2081:          system(строка)+захват stdout (до 0x400 байт)

Формат запроса: 4B FC <cmd_lo> <cmd_hi> <строка команды>\\x00
Формат ответа (эмпирика, см. декомпиляцию kdiag_common):
  байты 0..3  : эхо заголовка 4B FC <cmd>
  байты 4..7  : статус (0x2080: exit-код<<8; 0x2081: 0 при успехе)
  байт  8     : флаг наличия вывода (0x2081)
  байт  9..   : stdout команды

Команды выполняются от uid=1000(system), gid=0(root),
SELinux-контекст u:r:kdiag_common:s0. Это НЕ root: доступ к блочным
устройствам ограничен SELinux (см. guide/03-backups-no-unlock.md).

Ограничение вывода 0x2081 (важно): демон читает пайп ОДИН раз —
многостадийные конвейеры обрезаются. Надёжно: одна стадия, или запись
в /mnt/vendor/persist/... с последующим чтением по кускам (exfil.py).
"""
from __future__ import annotations

import argparse
import sys

from diag_transport import open_transport

CMD_SYSTEM = 0x2080
CMD_OUTPUT = 0x2081

# Коды ошибок DIAG: с таким первым байтом ответ содержит ЭХО запроса,
# а не результат — раньше это молча выдавалось за вывод команды.
DIAG_ERR_RSP = {0x13: "BAD_CMD", 0x14: "BAD_PARM", 0x15: "BAD_LEN", 0x18: "BAD_MODE"}


def shell(tr, command: str, capture: bool = True) -> tuple[int, str]:
    """Вернуть (код_возврата, вывод).

    Коды: -1 = нет ответа; -3 = команда отвергнута диспетчером
    (эхо-ответ DIAG_*_F — обработчик 0xFC не зарегистрирован).
    """
    cmd = CMD_OUTPUT if capture else CMD_SYSTEM
    payload = bytes([0x4B, 0xFC, cmd & 0xFF, (cmd >> 8) & 0xFF]) + command.encode() + b"\x00"
    r = tr.xfer(payload)
    if r is None or len(r) < 9:
        return -1, ""
    if r[0] in DIAG_ERR_RSP:
        return -3, f"DIAG_{DIAG_ERR_RSP[r[0]]}: команда отвергнута (kdiag_common не запущен?)"
    status = int.from_bytes(r[4:8], "little", signed=True)
    out = r[9:].decode(errors="replace").rstrip("\x00") if capture else ""
    return status, out


def main():
    ap = argparse.ArgumentParser(description="Shell через DIAG-бэкдор Kyocera")
    ap.add_argument("command", help="команда sh")
    ap.add_argument("--no-capture", action="store_true", help="только system(), без захвата вывода")
    a = ap.parse_args()
    tr = open_transport()
    try:
        if not tr.ping():
            print("DIAG не отвечает на DIAG_VERNO_F", file=sys.stderr)
            return 2
        rc, out = shell(tr, a.command, capture=not a.no_capture)
        if out:
            print(out)
        if rc == -3:
            print(f"ОШИБКА: {out}", file=sys.stderr)
            print("Диагностика: adb shell ps -A | grep kdiag_common",
                  "      adb shell getprop vendor.kc.diag.fact (ожидается kcfactoff)",
                  sep="\n", file=sys.stderr)
            return 3
        print(f"[exit={rc}]", file=sys.stderr)
        return 0 if rc != -1 else 1
    finally:
        tr.close()


if __name__ == "__main__":
    sys.exit(main())
