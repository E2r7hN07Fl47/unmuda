# Code comments - English translation

Translation of every Russian docstring and comment in the repository, keyed to
line numbers in the original files. Comments only - no code was changed.

---

## `unlock.sh`

| Line | Text |
|---|---|
| 4 | `#   Made by Mamkin_Xakep` |
| 5 | `#   Assisted by Google Gemini` |
| 8 | `# Strict mode: abort on any error` |
| 13 | `This utility is intended for unlocking the bootloader on Balmuda Phone smartphones.` |
| 14 | `Using this program entails the loss of all data on the phone.` |
| 15 | `Neither the author nor anyone else is liable for possible losses.` |
| 16 | `You perform all actions at your own risk.` |
| 19 | `Do you agree? [y/N]: ` |
| 23 | `Procedure cancelled. Have a good day.` |
| 27 | `Consent received. Performing the bootloader unlocking procedure...` |
| 29 | `# 1. CHECKING DEPENDENCIES AND CONNECTION` |
| 30 | `Error: ADB is not installed!` |
| 31 | `Error: Fastboot is not installed!` |
| 32 | `Error: Python3 is not installed!` |
| 34 | `Waiting for the device in ADB mode...` |
| 38 | `Error: the device is connected but not authorized. Allow debugging on the phone screen!` |
| 42 | `# 2. EXPLOITATION AND STARTING DIAG` |
| 43 | `Activating the DIAG interface...` |
| 46 | `Done!` |
| 48 | `# 3. CRITICAL STAGE: CHKCODE BACKUP` |
| 49 | `Backing up the chkcode partition...` |
| 51 | `Warning: the old chkcode_backup.bin file was removed to create a fresh backup.` |
| 57 | `# Checking that the backup file exists and is not empty (size > 0 bytes)` |
| 59 | `CRITICAL ERROR: the chkcode partition backup was not created or is empty! Stopping the script to prevent a brick.` |
| 62 | `The backup was created successfully and verified!` |
| 64 | `# 4. MODIFYING THE CHKCODE PARTITION` |
| 65 | `Writing the magic word into the chkcode partition...` |
| 67 | `Done!` |
| 69 | `# 5. REBOOTING INTO FASTBOOT WITH A LINK CHECK` |
| 70 | `Rebooting into fastboot mode...` |
| 72 | `Waiting for a connection in fastboot mode (about 10 seconds)...` |
| 76 | `# Checking whether fastboot can see the device` |
| 79-80 | `CRITICAL ERROR: the phone went for a reboot, but fastboot mode was not detected by the system! Please check the USB cable/drivers and do NOT close this terminal.` |
| 83 | `The device was successfully found in fastboot mode!` |
| 85 | `# 6. UNLOCKING THE BOOTLOADER` |
| 86 | `Performing the bootloader unlock...` |
| 88 | `Please confirm the request on the phone screen!` |
| 90 | `Done!` |
| 92 | `# 7. CLEARING THE PARTITION (RETURNING TO THE STANDARD CHKCODE)` |
| 93 | `Removing the magic word...` |
| 97 | `Error: failed to create chkcode_zero.img` |
| 102 | `WARNING: error while flashing the clean chkcode! Do not reboot the phone manually!` |
| 105 | `Done!` |
| 107 | `# 8. FINAL REBOOT` |
| 108 | `Rebooting...` |
| 110 | `Done!` |
| 112 | `The bootloader unlock was completed successfully. If you encountered any errors in its operation, please report them to us in GitHub Issues.` |

---

## `shell.nix`

| Lines | Text |
|---|---|
| 1-2 | `# shell.nix - environment for unlocking the BALMUDA Phone (A101BM)`<br>`# Part of the A101BM-unlock repository.` |
| 4-6 | `# Usage:`<br>`#   nix-shell            # from the repository root`<br>`#   cd tools && python3 cve31317.py ...` |
| 8-13 | `# Notes:`<br>`#  - udev rules for USB without root on NixOS:`<br>`#      services.udev.extraRules = ''`<br>`#        SUBSYSTEM=="usb", ATTR{idVendor}=="0482", MODE="0666"`<br>`#      '';`<br>`#    On ordinary Linux you can temporarily: sudo chmod 666 /dev/bus/usb/*/*, or use the udev file from TOOLS.md.` |
| 14 | `#  - On non-NixOS distributions without nix - install according to the repository's TOOLS.md.` |
| 22 | `# python + the single dependency of the tools/ scripts` |
| 27 | `# libusb backend for pyusb` |
| 31 | `# adb + fastboot (native Linux)` |
| 34 | `# USB diagnostics (lsusb)` |
| 37 | `# the AT port as a tty, if qcserial has grabbed the interface (an alternative to at_console.py)` |
| 39 | `# auxiliary, for working with partition images (not required for the unlock)` |
| 40 | `# mke2fs/debugfs - ext4 (metadata)` |
| 41 | `# mkfs.f2fs/sload.f2fs - userdata` |
| 42 | `# unpacking images` |

---

## `tools/diag_transport.py`

**Lines 2-10 (module docstring):**

> Qualcomm QCDM/HDLC diag transport over USB (Linux + Windows, without WSL).
>
> The only dependency: pyusb (+ libusb-1.0 and, on Windows, a WinUSB driver on the
> phone's DIAG interface - see TOOLS.md).
>
> The diag interface appears over USB only in the `diag,modem,adb` composition
> (see guide/02-diag-mode.md): VID 0482, PID 0A9D, interface #0,
> bulk OUT 0x01 / bulk IN 0x81.

**Lines 73-82 (`frame()` docstring):**

> HDLC frame for transmission.
>
> `with_crc=True` (default): payload + CRC16-X.25 + 0x7E - this is what the diag
> kernel requires in HDLC mode (a clean boot: `crc_check()` in
> `diag_process_hdlc_pkt`; without a CRC the kernel answers with a BAD_CMD echo
> 0x13 to ANY command, even VERNO).
>
> `with_crc=False`: compatibility with the kernel in non-HDLC mode
> (`hdlc_disabled=1`, which the kernel switches into after some diag clients
> start; that is how the first researched unit, 1.280, worked - which is why the
> bug went unnoticed).
>
> DiagTransport selects the mode automatically on the first exchange.

| Line | Text |
|---|---|
| 90 | `Opens the DIAG interface and performs synchronous request-response exchanges.` |
| 117-119 | `# TX frame mode: with CRC (the kernel in HDLC mode) or without (non-HDLC).`<br>`# While it is unknown - start with CRC (the correct mode for a clean`<br>`# boot); on a BAD_CMD echo xfer() will itself switch to a no-CRC retry.` |
| 127 | `Resetting the accumulated asynchronous data (logs and the like).` |
| 156 | `# strip the HDLC wrapper, verify the CRC` |
| 165-168 | `# BAD_CMD/BAD_PARM/BAD_LEN/BAD_MODE: the kernel rejected`<br>`# the command. If we are sending with a CRC - the probable cause: the kernel`<br>`# is in non-HDLC mode (hdlc_disabled), where the CRC in the tail of the`<br>`# packet breaks parsing. Switch over and retry.` |
| 171-172 | `BAD_CMD with CRC -> retry without CRC (kernel in non-HDLC mode)` |
| 179 | `attempt {n} failed: {e}` |
| 185 | `# DIAG_VERNO_F` |

---

## `tools/kdiag_shell.py`

**Lines 2-21 (module docstring):**

> kdiag_shell - shell commands on the phone via the Kyocera DIAG backdoor.
>
> Mechanism (verified on A101BM 1.280PO.0686.a):
> - subsys 0xFC, cmd 0x2080: `system(string)` → return code
> - subsys 0x2081: `system(string)` + stdout capture (up to 0x400 bytes)
>
> Request format: `4B FC <cmd_lo> <cmd_hi> <command string>\x00`
>
> Response format (empirical, see the kdiag_common decompilation):
> - bytes 0..3: echo of the `4B FC <cmd>` header
> - bytes 4..7: status (0x2080: exit code<<8; 0x2081: 0 on success)
> - byte 8: output-present flag (0x2081)
> - bytes 9..: the command's stdout
>
> Commands run as uid=1000(system), gid=0(root), SELinux context
> u:r:kdiag_common:s0. This is NOT root: access to block devices is restricted by
> SELinux (see guide/03-backups-no-unlock.md).
>
> Output limitation of 0x2081 (important): the daemon reads the pipe ONCE -
> multi-stage pipelines get truncated. Reliable: a single stage, or writing to
> /mnt/vendor/persist/... followed by reading it back in chunks (exfil.py).

| Line | Text |
|---|---|
| 33-34 | `# DIAG error codes: with such a first byte the response contains an ECHO of the request`<br>`# rather than the result - previously this was silently passed off as the command's output.` |
| 39-43 | `Return (return code, output).`<br>`Codes: -1 = no response; -3 = the command was rejected by the dispatcher`<br>`(a DIAG_*_F echo response - the 0xFC handler is not registered).` |
| 57 | `Shell via the Kyocera DIAG backdoor` |
| 67 | `DIAG does not respond to DIAG_VERNO_F` |
| 71-73 | `Diagnostics: adb shell ps -A | grep kdiag_common`<br>`      adb shell getprop vendor.kc.diag.fact (expects kcfactoff)` |

---

## `tools/fs_sys_call.py`

**Lines 2-22 (module docstring):**

> fs_sys_call - file operations via the Kyocera DIAG backdoor (subsys 0xFC, cmd 0x2000).
>
> The handler lives in the daemon /vendor/bin/fs_sys_call_diag (uid=system, gid=root).
> SELinux strictly limits access to block devices to ONLY the chkcode partition
> (u:object_r:chkcode_block_device). Ordinary files follow the rules of the
> fs_sys_call_diag domain (broader, but not unlimited: /proc, /sys, part of /vendor).
>
> Requires the kc_diag daemon class to be running:
>   vendor.kc.diag.status=start (set via kdiag_shell.py, see guides 02/04)
>
> Protocol (verified on A101BM 1.280PO.0686.a):
> ```
>   request:  4B FC 00 20 | u16 subcmd | arguments
>     0=open:  u32 flags@+6, u32 mode@+10, path@+14 (NUL-terminated)
>     1=close: u32 fd@+6
>     2=read:  u32 fd@+6, u32 count@+10 (count<=0x400)
>     3=write: u32 fd@+6, u32 count@+10, data@+14 (count<=0x400)
>     4=lseek: u32 fd@+6, s32 offset@+10, s32 whence@+14
>   response: hdr4 | u16 subcmd | u16 result | u32 retval | u32 errno [ | data ]
>     result=0 -> success; 0xFFFF -> error (retval/errno are populated).
>     For open retval = fd slot 0..4. The daemon has only 5 fd slots in total!
> ```

| Line | Text |
|---|---|
| 35-37 | `# DIAG echo responses: a first byte of 0x13/0x14/0x15/0x18 means the command was rejected`<br>`# by the diag kernel, and the body carries an ECHO of the request - previously the parser`<br>`# took it for a response and misdiagnosed "no free slot" (a real case on a remote unit)` |
| 94-95 | `Blind close of all the daemon's slots (0..4). Frees leaks.` |
| 146 | `Writing a file in chunks. Use only after analysing the permissions.` |
| 160 | `Read/write files via fs_sys_call` |
| 164-166 | `blindly close all the daemon's fd slots (0..4) and exit -`<br>`cures "no free fd slot" after leaks` |
| 167-168 | `print raw DIAG requests/responses (hex)` |

---

## `tools/backup_chkcode.py`

**Lines 2-9 (module docstring):**

> backup_chkcode.py - dump of the chkcode partition via fs_sys_call (WITHOUT the unlock).
>
> Mandatory first step before any write to chkcode.
>
> Partition: /dev/block/bootdevice/by-name/chkcode -> /dev/block/sda16, size
> 0x80000 (512 KiB). The SELinux domain of fs_sys_call_diag permits blk_file
> open/read/write for exactly chkcode_block_device - it is the only block
> partition readable this way without unlocking the bootloader.

| Line | Text |
|---|---|
| 31 | `Reading {CHKCODE_PATH} ({CHKCODE_SIZE} bytes)...` |
| 34 | `WARNING: read {n} instead of {CHKCODE_SIZE}` |
| 39 | `Saved: {out} ({n} bytes)` |
| 43 | `The partition looks clean (zeros/FF) - the backup was saved anyway.` |

---

## `tools/unlock_chkcode.py`

**Lines 2-14 (module docstring):**

> unlock_chkcode.py - writing the LOOTBFCK service magic into chkcode (the unlock step).
>
> WHAT IT DOES (verified on A101BM 1.280PO.0686.a):
>   writes the 8 bytes `LOOTBFCK` (0x4C4F4F54 + 0x4246434B LE) at offset 0 of the
>   chkcode partition. The bootloader (ABL), when `KcFastbootCheck()==TRUE`:
>   1) registers the FULL fastboot command table (flash/erase/boot/...);
>   2) skips the IsUnlocked/IsCriticalPartition checks inside flash/erase;
>   3) SIDE EFFECT: on every boot it enters fastboot mode (BootIntoFastboot=TRUE)
>      - Android itself will NOT boot until the magic is removed! To revert:
>      fastboot flash chkcode zeros (see guide 05).
>
> The script refuses to work without an existing chkcode backup alongside it
> (item 1 of the checklist).

| Line | Text |
|---|---|
| 33-34 | `--backup  file of the backup (mandatory; created by backup_chkcode.py)` |
| 35 | `--yes  do not ask for confirmation` |
| 40-41 | `REFUSING: no backup {backup}. Run backup_chkcode.py first (without a backup there is no way).` |
| 45-46 | `Writing LOOTBFCK will enable service mode: the phone will ALWAYS boot into fastboot until the magic is removed. Continue? [yes/N]` |
| 48 | `Cancelled.` |
| 58 | `REFUSING: wrote {n} bytes instead of {len(MAGIC)}` |
| 62 | `Verification read (first 16):` |
| 64 | `ERROR: the magic did not verify! Restore the backup:` |
| 67 | `OK: LOOTBFCK written and confirmed.` |
| 68-69 | `Next: adb reboot bootloader -> fastboot flashing unlock ->`<br>`confirm VOLUME UP on the phone screen. See guide 04.` |

---

## `tools/at_console.py`

**Lines 2-9 (module docstring):**

> at_console - AT commands to the modem via USB interface 1 (bulk 0x02/0x82).
>
> Works on both Linux and Windows (only pyusb is needed; on Windows -
> WinUSB/Zadig on the interface, see TOOLS.md; on Linux with qcserial busy:
> sudo rmmod qcserial).
>
> Requires the diag composition (guide 02). Read-only diagnostics: ATI, AT+CLAC,
> AT$QCPDPP? and the like.

| Line | Text |
|---|---|
| 28 | `0482:0a9d not found - enable the diag composition (guide 02)` |
| 39 | `AT endpoints 0x02/0x82 not found` |
| 66 | `AT commands; with no arguments - interactive mode` |
| 74 | `Interactive mode: type AT commands, 'quit' to exit.` |

---

## `tools/exfil.py`

**Lines 2-16 (module docstring):**

> exfil.py - pulling a file off the phone via kdiag_shell (0x2081).
>
> Two-stage scheme that works around the daemon's limitation (a single pipe read):
>   1) `cat <src> > /mnt/vendor/persist/x`  (persist is writable)
>   2) dd chunks of 200 B | base64 > /mnt/vendor/persist/c.b64
>   3) `cat c.b64` -> into the 0x2081 response
>
> Reliable for files of any size (speed ~1 KB/s because of the chunks).
>
> Usage (examples):
>   python exfil.py /vendor/bin/fs_sys_call_diag out_dir/
>   python exfil.py /mnt/vendor/persist/some_efs_file .
>
> Limitation: the file read is performed as uid=system in the kdiag_common
> domain - files unavailable to SELinux will return empty (0 bytes).

| Line | Text |
|---|---|
| 35 | `TRANSPORT REFUSED: {out}` |
| 36 | `First get this working: python3 kdiag_shell.py id` |
| 40 | `Failed to copy {src} (no rights or the path): {out!r}` |
| 44 | `{src}: 0 bytes (empty or unavailable)` |
| 46 | `{src}: {size} bytes, pulling in chunks...` |
| 64 | `Chunk {i} is unreadable after 6 attempts` |
