# 03 - Dumps WITHOUT unlocking the bootloader

What is actually available before the unlock, and what is not - an honest table
(verified on 1.280PO.0686.a):

| Target | Path | Status |
|---|---|---|
| **chkcode partition** (512 KiB) | fs_sys_call read - that is exactly what the SELinux domain allows | ✅ verified |
| Arbitrary files (vendor, system, /mnt/vendor/persist) | exfil.py via kdiag_shell | ✅ verified |
| Output of shell commands (uid=system) | kdiag_shell.py 0x2081 | ✅ verified |
| Modem AT commands | USB interface 1 (see below) | ✅ verified |
| boot/system/vendor/... partitions | NO before the unlock: no diag domain has SELinux rights to their blk_device | ❌ impossible with this method |
| devinfo | NO (SELinux; the state is duplicated in fastboot `getvar` anyway) | ❌ |

Everything is done with the diag composition from guide 02.

## 3.1 chkcode backup - mandatory before any unlock

```bash
cd tools
python3 backup_chkcode.py -o chkcode_backup.bin
```

Result: `chkcode_backup.bin` + `.sha256`. On a stock device the partition is
usually all zeros/FF - save the file anyway (it is your reference for recovery).

## 3.2 Arbitrary files (exfil)

```bash
python3 exfil.py /vendor/bin/fs_sys_call_diag .      # example: the daemon binary
python3 exfil.py /vendor/etc/init/init.kdmc.rc .     # the diag services config
```

Speed is ~1 KiB/s (chunks of 200 bytes) - be patient with large files.
Files forbidden to uid=system by SELinux will return an error/0 bytes - that is
a limitation of the method, not a script failure.

## 3.3 Shell commands (diagnostics)

```bash
python3 kdiag_shell.py "id"
# uid=1000(system) gid=0(root) groups=0(root),1000(system),2901(vendor_qti_diag)
# context=u:r:kdiag_common:s0

python3 kdiag_shell.py "getprop ro.build.fingerprint"
python3 kdiag_shell.py "ls -la /dev/block/bootdevice/by-name/"
```

Starting the diag daemons (needed for fs_sys_call):

```bash
python3 kdiag_shell.py "setprop vendor.kc.diag.status start"
```

## 3.4 AT commands (modem; USB interface 1, bulk 0x02/0x82)

The AT port appears in the same diag composition. The `at_console.py` script
works directly over USB on both OSes:

```bash
python3 at_console.py ATI "AT+CLAC"       # versions + the full command list
python3 at_console.py                     # interactive
```

On Linux the port may also show up as /dev/ttyUSB* (qcserial) - in that case
alternatively `picocom /dev/ttyUSB1`. There are no writing commands in AT on
this model - the channel is essentially read-only.

Useful: `ATI` (versions), `AT+CLAC` (259 commands), `AT$QCPDPP?` (PDP profiles).

## 3.5 What you MUST NOT do from this guide

- ⛔ Do NOT try to `dd`/write anything to block devices via kdiag_shell:
  SELinux forbids it, and `fs_sys_call` will return an open error for foreign
  partitions. The only permitted block partition is chkcode, and we touch it
  only with the scripts from guide 04.
- ⛔ Do NOT erase or flash partitions before the unlock has been obtained
  and guide 05 (restoring normal boot) has been read.
