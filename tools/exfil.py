#!/usr/bin/env python3
"""exfil.py — вытягивание файла с телефона через kdiag_shell (0x2081).

Двухступенчатая схема обходит ограничение демона (один read пайпа):
  1) cat <src> > /mnt/vendor/persist/x        (persist доступен на запись)
  2) dd-чанки по 200Б | base64 > /mnt/vendor/persist/c.b64
  3) cat c.b64 -> в ответ 0x2081
Надёжно для файлов любого размера (скорость ~1КБ/сек из-за чанков).

Использование (примеры):
  python exfil.py /vendor/bin/fs_sys_call_diag out_dir/
  python exfil.py /mnt/vendor/persist/some_efs_file .

Ограничение: чтение файла выполняется от uid=system в домене
kdiag_common — недоступные SELinux файлы вернут пустоту (0 байт).
"""
from __future__ import annotations

import argparse
import base64
import re
import sys
from pathlib import Path

from diag_transport import open_transport
from kdiag_shell import shell

X = "/mnt/vendor/persist/x"
C = "/mnt/vendor/persist/c.b64"


def exfil(tr, src: str) -> bytes | None:
    rc, out = shell(tr, f"cat {src} > {X} ; stat -c %s {X}")
    if rc == -3:
        print(f"ОТКАЗ транспорта: {out}", file=sys.stderr)
        print("Сначала добейтесь работы: python3 kdiag_shell.py id", file=sys.stderr)
        return None
    size_s = (out or "").strip().splitlines()[-1] if out else ""
    if not size_s.isdigit():
        print(f"Не удалось скопировать {src} (нет прав или пути): {out!r}", file=sys.stderr)
        return None
    size = int(size_s)
    if size == 0:
        print(f"{src}: 0 байт (пусто или недоступно)", file=sys.stderr)
        return None
    print(f"{src}: {size} байт, тяну чанками...", file=sys.stderr)
    CH = 200
    buf = bytearray()
    n = (size + CH - 1) // CH
    for i in range(n):
        want = CH if i < n - 1 else size - CH * (n - 1)
        for _ in range(6):
            shell(tr, f"dd if={X} bs={CH} skip={i} count=1 2>/dev/null | base64 > {C}")
            rc, c = shell(tr, f"cat {C}")
            m = re.sub(r"[^A-Za-z0-9+/=]", "", c or "")
            try:
                chunk = base64.b64decode(m + "=" * (-len(m) % 4))
                if len(chunk) == want:
                    buf += chunk
                    break
            except Exception:
                pass
        else:
            print(f"Чанк {i} не читается после 6 попыток", file=sys.stderr)
            shell(tr, f"rm -f {X} {C}")
            return None
    shell(tr, f"rm -f {X} {C}")
    return bytes(buf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="путь к файлу на телефоне")
    ap.add_argument("outdir", nargs="?", default=".")
    a = ap.parse_args()
    tr = open_transport()
    data = exfil(tr, a.src)
    if data is None:
        return 1
    out = Path(a.outdir) / Path(a.src).name
    out.write_bytes(data)
    print(f"OK {len(data)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
