# TOOLS - the complete list of tools

Everything installs on a regular Linux (x86_64) or Windows 10/11 (x64). WSL is not needed.
A Nix alternative is `nix-shell` from the repository root (see `shell.nix`):
a ready-made environment with python+pyusb, libusb, adb/fastboot and utilities for
working with images.

## 1. Required

| Tool | Version | Linux | Windows | Why |
|---|---|---|---|---|
| Python | ≥ 3.9 | `sudo apt install python3 python3-pip` (or the python.org distribution) | https://python.org (check "Add to PATH") | all the scripts in tools/ |
| pyusb | ≥ 1.2 | `pip3 install --user pyusb` | `pip install pyusb` | USB-DIAG |
| libusb-1.0 | 1.0.x | `sudo apt install libusb-1.0-0` | see §3 (Zadig installs WinUSB itself; pyusb needs libusb.dll - see below) | the pyusb backend |
| Android platform-tools | ≥ 34 | `sudo apt install adb fastboot` OR https://developer.android.com/studio/releases/platform-tools | the same site (zip, unpack, add to PATH) | adb, fastboot |

### Windows: libusb backend for pyusb (once)

pyusb works with libusb-1.0.dll:

1. Download https://github.com/libusb/libusb/releases (e.g. libusb-1.0.27.7z).
2. From the archive, put `VS2015-x64/dll/libusb-1.0.dll` into the same folder
   where python.exe is (or into the system PATH).
3. Check: `python -c "import usb; print(usb.backend.libusb1.get_backend())"`
   - it should return an object, not None.

### Windows: WinUSB driver for the phone's DIAG interface - Zadig

https://zadig.akeo.ie → Options → List All Devices → select
**BALMUDA_Android (Interface 0)** → driver **WinUSB** → Replace.
Do NOT change the driver of the parent composite device or of Interface 2
(you would break adb/MTP).

### Linux: USB access without root (optional)

```bash
sudo tee /etc/udev/rules.d/51-balmuda.rules <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="0482", MODE="0666"
EOF
sudo udevadm control --reload && sudo udevadm trigger
```

(Or run the scripts via sudo. For the diag composition, qcserial may grab the
interface: `sudo rmmod qcserial` before working.)

## 2. Used optionally in the instructions

| Tool | Why | Where |
|---|---|---|
| picocom/minicom (Linux) | the AT port as a tty | `sudo apt install picocom` (/dev/ttyUSB* appears with qcserial) |
| 7-Zip / tar | unpacking | standard |

## 3. Already included in the repository (tools/)

| File | Purpose |
|---|---|
| `diag_transport.py` | QCDM/HDLC transport over USB (both OSes) |
| `cve31317.py` | switching the USB composition to diag,modem,adb (CVE-2024-31317) |
| `kdiag_shell.py` | shell commands on the phone (subsys 0xFC cmd 0x2080/0x2081) |
| `fs_sys_call.py` | open/read/write/lseek via fs_sys_call_diag (0x2000) |
| `backup_chkcode.py` | dump of chkcode (mandatory before unlocking) |
| `unlock_chkcode.py` | writing LOOTBFCK with checks and protection against a missing backup |
| `exfil.py` | pulling arbitrary files off the phone |
| `at_console.py` | AT commands to the modem (interface 1) |
| `requirements.txt` | `pip install -r requirements.txt` |

## 4. What is NOT required (important)

- WSL, usbipd, virtual machines - not needed anywhere.
- Root, Magisk, TWRP - not needed for the unlock itself.
- Paid unlock services - not needed, and pointless for this method.
