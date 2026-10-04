#!/usr/bin/env python3
"""at_console — AT-команды модему через USB interface 1 (bulk 0x02/0x82).

Работает и на Linux, и на Windows (нужен только pyusb; на Windows —
WinUSB/Zadig на интерфейс, см. TOOLS.md; на Linux при занятом qcserial:
sudo rmmod qcserial).

Требует diag-композицию (гайд 02). Read-only диагностика: ATI, AT+CLAC,
AT$QCPDPP? и т.п.
"""
from __future__ import annotations

import argparse
import sys
import time

import usb.core
import usb.util

VID, PID = 0x0482, 0x0A9D
IFACE = 1
EP_OUT, EP_IN = 0x02, 0x82


def open_modem():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        raise RuntimeError("0482:0a9d не найден — включите diag-композицию (гайд 02)")
    try:
        if dev.is_kernel_driver_active(IFACE):
            dev.detach_kernel_driver(IFACE)
    except (NotImplementedError, usb.core.USBError):
        pass
    usb.util.claim_interface(dev, IFACE)
    eps = {}
    for ep in dev.get_active_configuration()[(IFACE, 0)]:
        eps[ep.bEndpointAddress] = ep
    if EP_OUT not in eps or EP_IN not in eps:
        raise RuntimeError("AT endpoints 0x02/0x82 не найдены")
    return dev, eps[EP_OUT], eps[EP_IN]


def at(dev, ep_out, ep_in, command: str, timeout_s: float = 4.0) -> str:
    try:
        while ep_in.read(4096, timeout=50):
            pass
    except usb.core.USBError:
        pass
    ep_out.write(command.encode() + b"\r", timeout=1000)
    out = bytearray()
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            out += bytes(ep_in.read(4096, timeout=200))
        except usb.core.USBError:
            if out:
                text = out.decode(errors="replace")
                if text.rstrip().endswith(("OK", "ERROR")):
                    break
            continue
    return out.decode(errors="replace").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", nargs="*", help="AT-команды; без аргументов — интерактивный режим")
    a = ap.parse_args()
    dev, ep_out, ep_in = open_modem()
    try:
        if a.command:
            for c in a.command:
                print(f"> {c}\n{at(dev, ep_out, ep_in, c)}")
        else:
            print("Интерактивный режим: вводите AT-команды, 'quit' — выход.")
            while True:
                try:
                    c = input("AT> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not c or c.lower() in ("quit", "exit"):
                    break
                print(at(dev, ep_out, ep_in, c))
    finally:
        usb.util.release_interface(dev, IFACE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
