#!/usr/bin/env python3
"""fs_sys_call — файловые операции через DIAG-бэкдор Kyocera (subsys 0xFC, cmd 0x2000).

Обработчик живёт в демоне /vendor/bin/fs_sys_call_diag (uid=system, gid=root).
SELinux жёстко ограничивает доступ к блочным устройствам ТОЛЬКО разделом
chkcode (u:object_r:chkcode_block_device). Обычные файлы — по правилам
домена fs_sys_call_diag (шире, но не безгранично: /proc, /sys, часть /vendor).

Требует запущенного класса демонов kc_diag:
  vendor.kc.diag.status=start (ставится через kdiag_shell.py, см. гайд 02/04)

Протокол (проверен на A101BM 1.280PO.0686.a):
  запрос:  4B FC 00 20 | u16 subcmd | аргументы
    0=open:  u32 flags@+6, u32 mode@+10, path@+14 (NUL-terminated)
    1=close: u32 fd@+6
    2=read:  u32 fd@+6, u32 count@+10 (count<=0x400)
    3=write: u32 fd@+6, u32 count@+10, data@+14 (count<=0x400)
    4=lseek: u32 fd@+6, s32 offset@+10, s32 whence@+14
  ответ:   hdr4 | u16 subcmd | u16 result | u32 retval | u32 errno [ | data ]
    result=0 -> успех; 0xFFFF -> ошибка (retval/errno заполняются).
    Для open retval = слот fd 0..4. У демона всего 5 слотов fd!
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

from diag_transport import open_transport

SUBSYS_OPEN, SUBSYS_CLOSE, SUBSYS_READ, SUBSYS_WRITE, SUBSYS_LSEEK = 0, 1, 2, 3, 4
MAXRW = 0x400

# эхо-ответы DIAG: первый байт 0x13/0x14/0x15/0x18 = команда отвергнута ядром
# DIAG, в теле приходит ЭХО запроса — раньше парсер принимал его за ответ
# и неверно диагностировал «нет слотов» (реальный случай на remote-юните)
DIAG_ERR_RSP = {0x13: "BAD_CMD", 0x14: "BAD_PARM", 0x15: "BAD_LEN", 0x18: "BAD_MODE"}

O_RDONLY, O_WRONLY, O_RDWR = 0, 1, 2
SEEK_SET, SEEK_CUR, SEEK_END = 0, 1, 2


class FSError(RuntimeError):
    pass


class FSDiag:
    def __init__(self, transport=None, debug: bool = False):
        self.tr = transport or open_transport()
        self.debug = debug

    def _call(self, sub: int, args: bytes = b"", data: bytes = b""):
        payload = bytes([0x4B, 0xFC, 0x00, 0x20]) + struct.pack("<H", sub) + args + data
        r = self.tr.xfer(payload)
        if self.debug:
            print(f"[dbg] req : {payload[:32].hex(' ')}{'...' if len(payload) > 32 else ''}")
            print(f"[dbg] resp: {r.hex(' ') if r else '(нет ответа)'}")
        if r is None:
            raise FSError("нет ответа от fs_sys_call_diag (демон запущен? см. гайд)")
        if len(r) < 8:
            raise FSError(f"короткий ответ: {r.hex()}")
        if r[0] in DIAG_ERR_RSP:
            raise FSError(
                f"DIAG_{DIAG_ERR_RSP[r[0]]}: subsys 0x4B отверг команду (ответ = "
                f"эхо запроса). Диспетчер kdiag мёртв на этом юните — "
                f"диагностика: ps -A | grep kdiag_common; getprop | grep kc.diag")
        result = struct.unpack_from("<H", r, 6)[0]
        if len(r) < 16:
            return result, None, None, b""
        retval, errno = struct.unpack_from("<II", r, 8)
        return result, retval, errno, r[16:]

    # --- файловые операции -------------------------------------------------
    def open(self, path: str, flags: int = O_RDWR, mode: int = 0o600) -> int:
        args = struct.pack("<II", flags, mode) + path.encode() + b"\x00"
        result, retval, errno, raw = self._call(SUBSYS_OPEN, args)
        if result == 0xFFFF:
            raise FSError(f"open({path!r}) отклонён: errno={errno} (SELinux/путь?)")
        if retval is None:
            raise FSError(
                f"open({path!r}): демон вернул короткий/неожиданный ответ "
                f"(result={result:#x}, сырые байты см. --debug) — пришлите вывод")
        if retval > 4:
            raise FSError(
                f"open({path!r}): нет свободного fd-слота или отказ демона "
                f"(retval={retval:#x}, errno={errno}). Очистка: --close-slots; "
                f"если не помогло -- сырой ответ под --debug пришлите нам")
        return int(retval)

    def close(self, fd: int):
        self._call(SUBSYS_CLOSE, struct.pack("<I", fd))

    def close_all(self) -> list[int]:
        """Слепое закрытие всех слотов демона (0..4). Освобождает утечки."""
        closed = []
        for fd in range(5):
            try:
                result, retval, errno, _ = self._call(
                    SUBSYS_CLOSE, struct.pack("<I", fd))
                if result != 0xFFFF:
                    closed.append(fd)
            except FSError:
                pass
        return closed

    def read(self, fd: int, count: int = MAXRW) -> bytes:
        count = min(count, MAXRW)
        result, retval, errno, data = self._call(SUBSYS_READ, struct.pack("<II", fd, count))
        if result == 0xFFFF:
            raise FSError(f"read(fd={fd}): errno={errno}")
        return data[: int(retval or 0)]

    def write(self, fd: int, data: bytes) -> int:
        assert len(data) <= MAXRW
        args = struct.pack("<I", fd) + struct.pack("<I", len(data))
        result, retval, errno, _ = self._call(SUBSYS_WRITE, args, data)
        if result == 0xFFFF:
            raise FSError(f"write(fd={fd}): errno={errno}")
        return int(retval or 0)

    def lseek(self, fd: int, offset: int, whence: int = SEEK_SET) -> int:
        result, retval, errno, _ = self._call(SUBSYS_LSEEK, struct.pack("<Iii", fd, offset, whence))
        if result == 0xFFFF:
            raise FSError(f"lseek(fd={fd}): errno={errno}")
        return int(retval or 0)

    # --- высокоуровневые ---------------------------------------------------
    def read_file(self, path: str, size: int, chunk: int = MAXRW, progress=print) -> bytes:
        fd = self.open(path, O_RDONLY)
        try:
            out = bytearray()
            self.lseek(fd, 0, SEEK_SET)
            while len(out) < size:
                piece = self.read(fd, min(chunk, size - len(out)))
                if not piece:
                    break
                out += piece
                if progress and (len(out) % (chunk * 16) == 0 or len(out) == size):
                    progress(f"  {len(out)}/{size} байт")
            return bytes(out)
        finally:
            self.close(fd)

    def write_file(self, path: str, data: bytes, flags: int = O_WRONLY, mode: int = 0o600):
        """Запись файла порциями. Использовать только после анализа прав."""
        fd = self.open(path, flags, mode)
        try:
            self.lseek(fd, 0, SEEK_SET)
            sent = 0
            while sent < len(data):
                sent += self.write(fd, data[sent:sent + MAXRW])
            return sent
        finally:
            self.close(fd)


def main():
    ap = argparse.ArgumentParser(description="Чтение/запись файлов через fs_sys_call")
    ap.add_argument("path", nargs="?", help="путь на телефоне, например /dev/block/bootdevice/by-name/chkcode")
    ap.add_argument("outfile", nargs="?", help="куда сохранить прочитанное")
    ap.add_argument("--size", type=lambda x: int(x, 0), default=0x1000,
                    help="сколько байт прочитать (по умолчанию 0x1000)")
    ap.add_argument("--close-slots", action="store_true",
                    help="слепо закрыть все fd-слоты демона (0..4) и выйти — "
                         "лечит 'нет свободного fd-слота' после утечек")
    ap.add_argument("--debug", action="store_true",
                    help="печатать сырые запросы/ответы DIAG (hex)")
    a = ap.parse_args()

    fs = FSDiag(debug=a.debug)
    if a.close_slots:
        closed = fs.close_all()
        print("закрыты слоты:", closed if closed else "(все уже были свободны)")
        return 0
    if not a.path:
        ap.error("нужен path (или --close-slots)")

    data = fs.read_file(a.path, a.size)
    if a.outfile:
        Path(a.outfile).write_bytes(data)
        print(f"Сохранено {len(data)} байт -> {a.outfile}")
    else:
        print(data.hex(" "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
