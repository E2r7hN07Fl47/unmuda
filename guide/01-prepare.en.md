# 01 - Preparation

## Who this is intended for

A fully self-contained instruction for the Kyocera BALMUDA Phone (A101BM,
SoftBank, SoC Snapdragon 765G / SM7250 "saipan", Android 12).
Verified on firmware **1.280PO.0686.a** (SPL 2022-10-01).
On other kernel/firmware versions the paths may differ.

## What you will need (briefly; the full list is in ../TOOLS.md)

- A computer with Linux (x86_64) **or** Windows 10/11 (x64) - without WSL.
- Python 3.9+ and the `pyusb` package.
- platform-tools (adb + fastboot).
- A USB cable; a phone with USB debugging enabled (Settings → About phone →
  tap build number 7 times → For developers → USB debugging).
- On Windows - Zadig (to install the WinUSB driver on the diag interface).

## Compatibility check (2 minutes, changes nothing)

```bash
adb shell getprop ro.build.version.incremental   # 1.280PO.0686.a
adb shell getprop ro.build.version.security_patch  # 2022-10-01
adb shell getprop ro.product.model               # A101BM
adb shell ls /system_ext/framework/qcrilhook.jar # must exist
```

If SPL ≥ 2024-05-01 - CVE-2024-31317 is closed, and the method of bringing up
diag mode from guide 02 will not work (a different way to switch
`sys.usb.config` would be needed, and this repository does not have one).

## Map of the method

```
Android (adb)                      USB diag,modem,adb            fastboot
    |                                    |                          |
    | CVE-2024-31317 ->                  | Kyocera DIAG backdoor:   |
    | setprop sys.usb.config             | 0xFC/0x2081 = shell      |
    v                                    | 0xFC/0x2000 = files      |
 [02-diag-mode]                          v                         |
                                    [03-backups-no-unlock]          |
                                         |  fs_sys_call:            |
                                         |  chkcode backup          |
                                         v                          |
                                    [04-unlock]                     |
                                         | write LOOTBFCK +         |
                                         | flashing unlock          |
                                         v                          |
                                                              [05-restore]
                                                              removing the magic,
                                                              normal boot
```

## Iron rule (from POSTULATES)

Any write to partitions - only after backing up the partition being changed, and
only with the commands from this repository. The repository also includes
"anti-examples" (what NOT to do) - they are marked with the word DANGEROUS and
were inserted not for the sake of decoration.
