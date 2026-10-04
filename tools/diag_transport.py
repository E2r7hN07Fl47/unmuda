#!/usr/bin/env python3
"""Диаг-транспорт Qualcomm QCDM/HDLC поверх USB (Linux + Windows, без WSL).

Единственная зависимость: pyusb (+ libusb-1.0 и, на Windows, WinUSB-драйвер
на DIAG-интерфейсе телефона — см. TOOLS.md).

Диаг-интерфейс появляется в USB только в композиции diag,modem,adb
(см. guide/02-diag-mode.md): VID 0482, PID 0A9D, interface #0,
bulk OUT 0x01 / bulk IN 0x81.
"""
from __future__ import annotations

import sys
import time

import usb.core
import usb.util

VID = 0x0482
PID = 0x0A9D

INTERFACE = 0
ALTSETTING = 0
EP_OUT = 0x01
EP_IN = 0x81

USB_TIMEOUT_MS = 3000
REQUEST_TRIES = 3

DIAG_ERRORS = {
    0x13: "DIAG_BAD_CMD_F",
    0x14: "DIAG_BAD_PARM_F",
    0x15: "DIAG_BAD_LEN_F",
    0x18: "DIAG_BAD_MODE_F",
}


def crc16_x25(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return crc ^ 0xFFFF


def escape(data: bytes) -> bytes:
    out = bytearray()
    for b in data:
        if b == 0x7E:
            out += b"\x7D\x5E"
        elif b == 0x7D:
            out += b"\x7D\x5D"
        else:
            out.append(b)
    return bytes(out)


def unescape(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        if data[i] == 0x7D and i + 1 < len(data):
            out.append(data[i + 1] ^ 0x20)
            i += 2
        else:
            out.append(data[i])
            i += 1
    return bytes(out)


def frame(payload: bytes, with_crc: bool = True) -> bytes:
    """HDLC-фрейм для отправки.

    with_crc=True (по умолчанию): payload + CRC16-X.25 + 0x7E — так требует
    ядро diag в HDLC-режиме (чистый бут: crc_check() в diag_process_hdlc_pkt;
    без CRC ядро отвечает BAD_CMD-эхом 0x13 на ЛЮБУЮ команду, даже VERNO).
    with_crc=False: совместимость с ядром в non-HDLC режиме (hdlc_disabled=1,
    в него ядро переходит после старта некоторых диаг-клиентов; так работал
    первый исследованный юнит 1.280 — из-за него баг жил незамеченным).
    DiagTransport выбирает режим автоматически при первом обмене.
    """
    if with_crc:
        body = payload + crc16_x25(payload).to_bytes(2, "little")
        return escape(body) + b"\x7E"
    return escape(payload) + b"\x7E"


class DiagTransport:
    """Открывает DIAG-интерфейс и делает синхронные запросы-ответы."""

    def __init__(self, quiet: bool = True):
        self.quiet = quiet
        self.dev = usb.core.find(idVendor=VID, idProduct=PID)
        if self.dev is None:
            raise RuntimeError(
                f"USB {VID:04x}:{PID:04x} не найден. Проверьте: (1) телефон в "
                "композиции diag,modem,adb (guide/02-diag-mode.md); "
                "(2) на Windows установлен WinUSB-драйвер на диаг-интерфейс "
                "(TOOLS.md); (3) права/udev на Linux."
            )
        cfg = self.dev.get_active_configuration()
        try:
            if self.dev.is_kernel_driver_active(INTERFACE):
                self.dev.detach_kernel_driver(INTERFACE)
        except (NotImplementedError, usb.core.USBError):
            pass
        usb.util.claim_interface(self.dev, INTERFACE)
        self.ep_out, self.ep_in = None, None
        for ep in cfg[(INTERFACE, ALTSETTING)]:
            if ep.bEndpointAddress == EP_OUT:
                self.ep_out = ep
            elif ep.bEndpointAddress == EP_IN:
                self.ep_in = ep
        if self.ep_out is None or self.ep_in is None:
            raise RuntimeError("DIAG endpoints 0x01/0x81 не найдены")
        # Режим TX-фрейма: с CRC (ядро в HDLC-режиме) или без (non-HDLC).
        # Пока неизвестен — стартуем с CRC (правильный режим для чистого
        # бута); при BAD_CMD-эхе xfer() сам переключится на без-CRC ретраем.
        self._use_crc = True

    def log(self, *a):
        if not self.quiet:
            print(*a, file=sys.stderr)

    def drain(self, attempts: int = 8):
        """Сброс накопившихся асинхронных данных (логи и т.п.)."""
        for _ in range(attempts):
            try:
                self.ep_in.read(4096, timeout=60)
            except usb.core.USBError:
                return

    def xfer(self, payload: bytes, timeout: int = USB_TIMEOUT_MS,
             tries: int = REQUEST_TRIES) -> bytes | None:
        self.drain()
        for attempt in range(1, tries + 1):
            pkt = frame(payload, self._use_crc)
            self.log(f"TX PAYLOAD: {payload.hex(' ')} (crc={self._use_crc})")
            try:
                self.dev.write(self.ep_out, pkt, timeout)
                raw = bytearray()
                deadline = time.monotonic() + timeout / 1000.0
                while time.monotonic() < deadline:
                    try:
                        chunk = bytes(self.ep_in.read(4096, timeout=200))
                        raw += chunk
                    except usb.core.USBError:
                        if raw:
                            break
                        continue
                    if raw and raw.endswith(b"\x7E"):
                        break
                if not raw:
                    raise usb.core.USBError("timeout")
                # снять HDLC-обёртку, проверить CRC
                for frame_bytes in bytes(raw).split(b"\x7E"):
                    if not frame_bytes:
                        continue
                    body = unescape(frame_bytes)
                    if len(body) < 2:
                        continue
                    data, crc_rx = body[:-2], int.from_bytes(body[-2:], "little")
                    if crc16_x25(data) == crc_rx:
                        # BAD_CMD/BAD_PARM/BAD_LEN/BAD_MODE: ядро отвергло
                        # команду. Если шлём с CRC — вероятная причина: ядро
                        # в non-HDLC режиме (hdlc_disabled), где CRC в хвосте
                        # пакета ломает разбор. Переключаемся и ретраим.
                        if data and data[0] in DIAG_ERRORS and self._use_crc:
                            self._use_crc = False
                            self.log("BAD_CMD с CRC -> ретрай без CRC "
                                     "(ядро в non-HDLC режиме)")
                            raise usb.core.USBError("hdlc mode mismatch")
                        self.log(f"RX PAYLOAD: {data.hex(' ')}")
                        return data
                raise usb.core.USBError("bad crc")
            except usb.core.USBError as e:
                self.log(f"попытка {attempt} не удалась: {e}")
                if attempt == tries:
                    return None
                time.sleep(0.4)
        return None

    def ping(self) -> bool:
        r = self.xfer(bytes([0x00]))          # DIAG_VERNO_F
        return r is not None and len(r) >= 2

    def close(self):
        try:
            usb.util.release_interface(self.dev, INTERFACE)
            usb.util.dispose_resources(self.dev)
        except Exception:
            pass


def open_transport() -> DiagTransport:
    return DiagTransport()
