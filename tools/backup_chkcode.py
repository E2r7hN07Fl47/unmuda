#!/usr/bin/env python3
"""backup_chkcode.py — дамп раздела chkcode через fs_sys_call (БЕЗ анлока).

Обязательный первый шаг перед любой записью в chkcode.

Раздел: /dev/block/bootdevice/by-name/chkcode -> /dev/block/sda16,
размер 0x80000 (512 КиБ). SELinux домена fs_sys_call_diag разрешает
blk_file open/read/write именно для chkcode_block_device — это единственный
блочный раздел, читаемый этим путём без разблокировки загрузчика.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from diag_transport import open_transport
from fs_sys_call import FSDiag

CHKCODE_PATH = "/dev/block/bootdevice/by-name/chkcode"
CHKCODE_SIZE = 0x80000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="chkcode_backup.bin")
    a = ap.parse_args()
    tr = open_transport()
    fs = FSDiag(tr)
    print(f"Читаю {CHKCODE_PATH} ({CHKCODE_SIZE} байт)...")
    data = fs.read_file(CHKCODE_PATH, CHKCODE_SIZE)
    if len(data) != CHKCODE_SIZE:
        print(f"ВНИМАНИЕ: прочитано {len(data)} вместо {CHKCODE_SIZE}", file=sys.stderr)
    out = Path(a.out)
    out.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    (out.with_suffix(".sha256")).write_text(f"{digest}  {out.name}\n")
    print(f"Сохранено: {out} ({len(data)} байт)")
    print(f"SHA-256: {digest}")
    print(f"Первые 16 байт: {data[:16].hex(' ')}")
    if set(data[:8]) <= {0x00, 0xFF}:
        print("Раздел выглядит чистым (нули/FF) — бэкап всё равно сохранён.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
