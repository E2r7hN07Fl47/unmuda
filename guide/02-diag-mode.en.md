# 02 - Bringing up diag mode (USB composition diag,modem,adb)

The Kyocera diag backdoor lives in a USB interface that the phone exposes only
in the `diag,modem,adb` composition. After every phone reboot the composition
resets to `mtp,adb` - the step will have to be repeated.

## 2.1 Switching the composition

From the `tools/` directory:

```bash
python3 cve31317.py            # Linux
python cve31317.py --adb adb   # Windows (adb.exe in PATH)
```

What the script does: disables the USAP pool, builds the CVE-2024-31317 payload,
pushes it to the phone and pokes the app spawn until `sys.usb.config` switches
(up to 12 attempts; it succeeds more easily after a phone reboot).

Success:

```bash
adb shell getprop sys.usb.config   # diag,modem,adb
```

The USB device re-enumerates: **0482:0a9d** (it was 0482:0a74).

## 2.2 Driver on Windows (skip on Linux)

The composition is a composite USB device: interface 0 = DIAG, 1 = modem (AT),
2 = adb. adb works through the standard Android driver; the DIAG interface needs
WinUSB:

1. Download Zadig (https://zadig.akeo.ie).
2. Options → List All Devices.
3. In the dropdown select **BALMUDA_Android (Interface 0)**
   (NOT the parent composite and NOT Interface 2 - otherwise you will break adb!).
4. Use the arrows to select the target driver **WinUSB** → Replace Driver.
5. Check: `python -c "import usb.core; print(usb.core.find(idVendor=0x0482,idProduct=0x0a9d))"`
   should print a device object, not None.

Reverting to the stock driver after the work (once you are back in mtp,adb):
Device Manager → remove the device with the WinUSB driver → reconnect.

## 2.3 Checking the diag channel

```bash
cd tools
python3 -c "from diag_transport import open_transport; t=open_transport(); print('DIAG OK' if t.ping() else 'no response')"
```

(Windows: the same with `python`.)

The diag channel responds - move on to guide 03 (dumps without unlock) or 04 (unlock).

## Troubleshooting

| Symptom | Cause/treatment |
|---|---|
| cve31317: all attempts end at `sys.usb.config=mtp,adb` | Reboot the phone and repeat; check the SPL (guide 01); on a freshly booted device the USAP pool is empty |
| `ping()` prints `no response`, but VERNO as a raw frame with CRC does answer | everything is fine - update the repository: the older transport version sends frames without CRC (guide 06 §6.1, bug A) |
| `Device or resource busy` on open_transport (Linux) | `sudo rmmod qcserial`, or release the interface: `sudo fuser -k /dev/bus/usb/...` |
| Windows: `No backend available` | libusb is not installed - see TOOLS.md (pyusb + libusb dll) |
| adb disappeared after the switch | This is normal during the moment of re-enumeration; it comes back as Interface 2. If not - reconnect the cable |
