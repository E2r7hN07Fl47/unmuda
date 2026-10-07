# 06 - Unlock on a device with an EMPTY sysprop partition (retail norm)

The most important guide in the repository: a universal unlock path that does
not depend on the state of the `sysprop` partition. Verified on A101BM
**1.220PO.0663.a** (the first Android 12 build, SPL 2022-09, factory reset,
sysprop entirely zeroed). If guides 03/04 worked for you "as is" - this guide
gives you the same thing more simply; if they did not work (BAD_CMD for
everything, `vendor.kc.diag.fact` empty) - you are here, and this is the NORMAL
state of the device, not a malfunction.

---

## 6.0 Who this guide is for

Two states of the A101BM phone found in retail:

| Sign | "Service" (minority) | "Retail" (majority) |
|---|---|---|
| The `sysprop` partition | valid (written at the factory/service) | entirely zeroed |
| `getprop vendor.kc.diag.fact` | `kcfactoff` (or `kcfacton`) | empty |
| The `kc_diag` daemon class | starts by itself via the init trigger | NEVER starts |
| `kdiag_shell.py "setprop vendor.kc.diag.status start"` | brings the class up | the class does not come up |
| DIAG subsys 0xFC out of the box | responds | **also responds** - but the daemon has to be started by hand (see 6.3) |

The key fact established by reversing `kdiag_common` (binary 1.230) and the
msm-4.19 kernel (sources 1.200): **registration of the subsys 0xFC handlers in
the kernel is a purely local operation** (`ioctl DIAG_IOCTL_COMMAND_REG` →
`list_add` into the kernel's `cmd_reg_list`; no negotiation with the modem is
required). No "factory DIAG routing initialization" exists - it is enough for
the `fs_sys_call_diag` daemon to simply be running.

## 6.1 Why it might not have worked for you before: two twin bugs

### Bug A: frames without a CRC (the main one)

`tools/diag_transport.py` before the fix sent HDLC frames **without CRC16**:
`escape(payload) + 0x7E`. The diag kernel on a clean boot works in HDLC mode:
`crc_check()` does not pass → `diag_send_error_rsp()` → a BAD_CMD echo `0x13`
**for any command, including VERNO**. The reply arrives in ~65 ms (the internal
timeout of the hdlc decoder), which masked itself as "the modem is thinking and
rejecting".

The bug was invisible on some devices: after certain diag clients start, the
kernel switches to non-HDLC mode (`hdlc_disabled=1`), where the CRC is not
checked. On a clean boot the CRC is always checked.

With the fix (the commit "diag_transport: CRC16 in the TX frame + automatic mode
selection") the transport picks the mode itself: it sends with a CRC, and on a
BAD_CMD echo it switches over to no-CRC and resends. The user needs no flags.

**Diagnostics before/after the fix** (a raw reference request, if you are in doubt):

```python
# tools/: python3 -c "from diag_transport import open_transport; \
#   t=open_transport(); print('DIAG OK' if t.ping() else 'no response')"
```

`ping()` = VERNO (0x00). A correct reply starts with `0x00` and contains a string
like "Aug 19 2022 ... saipan.g" (it is the kernel/AP answering, not the modem).
A reply of `13 00 7e` (or a long echo of the request with `0x13` at the start) -
the command was rejected: either the transport is without the fix, or the daemon
is not running (6.3).

### Bug B: the kc_diag class trigger depends on sysprop

The old path (guide 04 §4.1) brought the daemons up via
`kdiag_shell.py "setprop vendor.kc.diag.status start"`. That only worked with a
live init trigger:

```
on property:vendor.kc.diag.status=start && property:vendor.kc.diag.fact=kcfactoff
    class_start kc_diag
```

`vendor.kc.diag.fact` is set by `kcjprop_d`, which reads the `sysprop` partition.
An empty partition → the property will never be set → the class does not start.
**Workaround: start the service directly** - `setprop ctl.start <name>`.
init executes ctl.start for any declared service, bypassing triggers, classes and
conditions. This is exactly how init would have started it itself (the same
seclabel, the same domain, the same groups) - this is not an SELinux bypass but
the standard service-management mechanism, available to uid=1000 via
CVE-2024-31317.

## 6.2 What NOT to try (a hard-won list - don't waste time)

- **The kcjprop HAL** (`getService()/get()/set()` from the wrapper via
  APK-CLASSPATH): it works (RC=0 for the reset keys), but you cannot initialize
  an empty `sysprop` with it - there is no create/init in the interface; all data
  keys return RC=9 "key unknown". A dead end, recorded in practice.
- **The fact versions of the daemons** (`fs_sys_call_diag_fact`,
  `kdiag_common_fact`, `kdiag_shell_fact`, the `kc_fact_diag` class, user root):
  in their init.kdmc.rc there is `group root` **without** `vendor_qti_diag` →
  `/dev/diag` is unreachable by DAC, and `cap_dac_override` is forbidden in their
  SELinux domain (AVC permissive=0) → the process dies at `Diag_LSM_Init`. They
  do not work IN PRINCIPLE; do not start them.
- **`setprop vendor.kc.diag.fact=kcfactoff` by hand** - the property is written,
  but kcjprop_d overwrites it/does not confirm it; and even if it held - the
  kc_diag class has other conditions. Just use ctl.start.
- **AT commands** (interface 1 in the composition): the basic Qualcomm ones are
  there, the factory ones are not. Not a path to the partitions.
- **Updating/downgrading the firmware for the sake of diag**: DIAG is alive on
  any version; the problem was the transport (bug A) and the daemon not running
  (bug B).

## 6.3 Step-by-step procedure (Linux; Windows differences in brackets)

All commands are run from the `tools/` directory. Device: Android booted, adb
authorized, screen unlocked (again after each reboot).

### Step 1. Bringing up the diag composition

```bash
adb shell getprop sys.usb.config        # expecting mtp,adb (after a reboot)
python3 cve31317.py                     # (Windows: python cve31317.py --adb adb)
adb shell getprop sys.usb.config        # now diag,modem,adb
lsusb | grep 0a9d                       # (Windows: Device Manager/Zadig, see 02 §2.2)
```

USB re-enumeration: adb disappears for a moment - that is normal. If after the
re-enumeration `adb devices` is empty or says `no permissions` - restart the adb
server and/or fix the permissions on the device node:

```bash
adb kill-server; adb start-server
# Linux: lsusb | grep 0482:0a9d  → Bus 001 Device 0NN
sudo chmod 666 /dev/bus/usb/001/0NN     # or a udev rule
```

If all 12 injection attempts failed (`sys.usb.config=mtp,adb`) - reboot the phone
and repeat: on a freshly booted device the USAP pool is empty, so the injection
succeeds more easily (degradation after 15-20 injections without a reboot is
normal; the symptom: Settings/IME hang - curable only by a reboot).

### Step 2. Starting the fs_sys_call_diag daemon (the core of the guide)

```bash
python3 cve31317.py --cmd "setprop ctl.start fs_sys_call_diag ;" \
    --check-prop init.svc.fs_sys_call_diag=running
adb shell getprop init.svc.fs_sys_call_diag   # running
adb shell ps -A | grep fs_sys_call_diag       # a live process (user system)
```

Usually 1 attempt is enough. The service is `oneshot` and hangs forever after
starting (it sleeps in a read on /dev/diag) - there is no need to restart it
until a reboot.

Optionally you can also bring up `kdiag_common` (needed for `kdiag_shell.py`,
guide 03): the same command with `kdiag_common`. It is NOT required for
writing/reading chkcode.

### Step 3. Channel check (mandatory, read-only)

```bash
python3 -c "from diag_transport import open_transport; \
  t = open_transport(); print('DIAG OK' if t.ping() else 'NO RESPONSE')"
python3 fs_sys_call.py --debug /dev/block/bootdevice/by-name/chkcode --size 16
```

Expectation for the second command: `req/resp` pairs with the header
`4b fc 00 20 ...`, the reply does NOT start with `13`, and the reply to the read
contains zeros (the locked stock state). If the reply is an echo of the request
with `0x13` in the first byte - the daemon is not running (go back to step 2) or
the transport is old (update the repository).

### Step 4. chkcode backup (without it unlock_chkcode will refuse)

```bash
python3 backup_chkcode.py -o chkcode_backup.bin
# Saved: chkcode_backup.bin (524288 bytes)
# SHA-256: ... - record it in your notes
# First 16 bytes: 00 00 ... - a clean partition, that is normal
```

The file and `.sha256` will appear in the current directory. Keep them together
with the record about the unit (this is your rollback path).

### Step 5. Writing the LOOTBFCK magic

```bash
python3 unlock_chkcode.py --backup chkcode_backup.bin --yes
# Verification read (first 16): 4c 4f 4f 54 42 46 43 4b 00 ...
# OK: LOOTBFCK written and confirmed.
```

The script writes exactly 8 bytes at offset 0 and re-reads them for verification.
From this moment on, **the phone will go into fastboot on every boot** - that is
a side effect of the magic, not a breakdown (it is removed in guide 05).

### Step 6. Unlocking

```bash
adb reboot bootloader
fastboot devices                 # (Windows: fastboot.exe) the serial number is in the list
fastboot getvar unlocked         # unlocked: no (for now)
fastboot flashing unlock         # OKAY
fastboot getvar unlocked         # unlocked: yes
```

A nuance: on some builds `flashing unlock` returns `OKAY` instantly, without a
confirmation screen; on others a menu appears - confirm with volume UP.
Immediately after the unlock the device re-enumerates (`fastboot getvar` may show
`< waiting for any device >` once) - repeat the command.

### Step 7. Restoring normal boot

The data is wiped during the unlock. The full order is in guide 05 (remove the
magic: `fastboot flash chkcode chkcode_backup.bin` - now permitted, since it is
unlocked; then `fastboot reboot`, initial setup, authorize adb over USB debugging
again).

## 6.4 Troubleshooting by step

| Symptom | Cause | Action |
|---|---|---|
| cve31317: all attempts miss | the USAP pool is not empty / degradation | reboot the phone, repeat |
| `adb devices` empty after 6.1 | adb server / node permissions | kill-server/start-server; chmod 666 the node |
| `pyusb: Resource busy` on open | the interface is busy (qcserial/another script) | `sudo rmmod qcserial`; close the other scripts |
| ping() no response | wrong composition / WinUSB on the wrong interface | guide 02 §2.2-2.3 |
| fs_sys_call: BAD_CMD echo | the daemon is not running | step 2; check `ps -A | grep fs_sys` |
| fs_sys_call: "no free fd slot" | slot leakage from previous sessions | `python3 fs_sys_call.py --close-slots` |
| unlock: "the magic did not verify" | a write failure | do NOT reboot; restore the backup (05 §5.3); repeat |
| fastboot: `flashing unlock` → FAIL not allowed | no magic / it was erased | re-read chkcode via fs_sys_call |
| unlock OKAY, but `unlocked: no` | did not wait for the re-enumeration | repeat getvar after a couple of seconds |
| after `fastboot boot` the phone loops with no USB | probable exhaustion of the active slot's slot-retry and a switch to an incompatible old one (guide 04 §4.3) | from any accessible fastboot: `getvar current-slot`, `slot-retry-count:a/b`, then `set_active <live slot>` |

## 6.5 How it works (a reference for audit)

1. **CVE-2024-31317** - argument injection into Zygote via the
   `hidden_api_blacklist_exemptions` setting: it executes an arbitrary command as
   uid=1000 (system) in the system_app domain.
2. **`setprop ctl.start fs_sys_call_diag`** - the standard init interface for
   managing services (available to uid=1000). init forks
   `/vendor/bin/fs_sys_call_diag` with the seclabel from the vendor file
   contexts: user system, group root+vendor_qti_diag - exactly as with the
   "native" start of the kc_diag class. The daemon's SELinux domain permits
   opening `/dev/diag` and rw **only** for blk_file of the class
   `chkcode_block_device`.
3. **Registration of 0xFC/0x2000-0x2004** - on start the daemon does
   `Diag_LSM_Init()` + `diagpkt_tbl_reg()`; the kernel adds the range to the
   local `cmd_reg_list` (`diag_cmd_add_reg`, proc=APPS_DATA). No involvement of
   the modem. (Verified by reversing kdiag_common 1.230 and by reading
   drivers/char/diag from the 1.200 kernel sources.)
4. **HDLC/CRC** - the USB input: `diagfwd_mux_read_done →
   diag_process_hdlc_pkt`: decode + `crc_check()`; in non-HDLC mode
   (`hdlc_disabled=1`, set by some diag clients) the CRC is not checked. Hence
   the automatic mode selection in the transport.
5. **LOOTBFCK → KcFastbootCheck()** - see guide 04 §"how it works": ABL registers
   the full fastboot command table and skips the lock checks; `SetDeviceUnlock`
   for user builds requires only `KcFastbootCheck()==TRUE` (ABL source
   FastbootCmds.c, the TargetBuildVariantUser branch).

## 6.6 Differences from the "service" path (guides 03-04)

| | Guide 03/04 (sysprop valid) | This guide (sysprop empty) |
|---|---|---|
| Bringing up the daemons | `kdiag_shell.py "setprop vendor.kc.diag.status start"` | `cve31317.py --cmd "setprop ctl.start fs_sys_call_diag ;"` |
| What is available | shell (0x2081) + file I/O (0x2000) | only file I/O (0x2000) - enough for chkcode |
| Writing LOOTBFCK | identical: `unlock_chkcode.py --backup ... --yes` | the same |

If you want shell commands on an empty sysprop - additionally
`ctl.start kdiag_common` (step 2), after which `kdiag_shell.py` works as in
guide 03.
