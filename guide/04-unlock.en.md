# 04 - Unlocking the bootloader

Before this step, guide 03 MUST have been completed (you have `chkcode_backup.bin`).

## How it works (in one paragraph)

The bootloader (ABL) of this model has a service check `KcFastbootCheck()`:
if the first 8 bytes of the `chkcode` partition are `LOOT`+`BFCK`, ABL considers
the device a service device: it registers ALL fastboot commands and skips the
lock checks inside `flash`/`erase`, and the `flashing unlock` command no longer
requires OEM permission. The "unlocked" state itself, once confirmed on screen,
is written into devinfo via TrustZone. Side effect: with the magic present the
phone boots ONLY into fastboot - Android does not start until the magic is
removed (guide 05).

## 4.1 Writing the magic (phone in Android, diag composition active)

```bash
cd tools
python3 backup_chkcode.py -o chkcode_backup.bin     # if not already done
python3 kdiag_shell.py "setprop vendor.kc.diag.status start"   # kc_diag daemons
python3 unlock_chkcode.py --backup chkcode_backup.bin
```

If `kdiag_shell.py` returned `DIAG_BAD_CMD` and the class did not come up - your
`sysprop` partition is empty (the retail norm): the init trigger for the kc_diag
class requires `vendor.kc.diag.fact=kcfactoff`, which no one is left to set.
Use a direct daemon start instead; this works on any unit:

```bash
python3 cve31317.py --cmd "setprop ctl.start fs_sys_call_diag ;" \
    --check-prop init.svc.fs_sys_call_diag=running
```

The full procedure for this case (with diagnostics for every step) is guide 06;
after that the writing/unlocking steps are identical.

The script will ask for confirmation, write 8 bytes, read them back and verify.
In the case of "ERROR: the magic did not verify" - do NOT reboot the phone,
restore the backup (guide 05, section 5.3) and figure out why the write failed
(usually - the kc_diag class is not running).

## 4.2 Unlocking

```bash
adb reboot bootloader
fastboot devices                       # should show the serial number
fastboot flashing unlock
```

A confirmation prompt will appear on the phone screen -
**select "unlock" with the volume buttons** (Vol Up = confirm).
The procedure will wipe the data - that is by design; there is no external card.

Check:

```bash
fastboot oem device-info | grep -i unlocked     # Linux
fastboot oem device-info | findstr /i unlocked  # Windows
# (bootloader) Device unlocked: true
```

## 4.3 What NOT to do in an unlocked fastboot (a hard-won list)

**General rule.** After the unlock, all fastboot commands are available to you
(`flash`, `erase`, `boot` and others). Running them - directly or indirectly -
can lead to a brick **with possibly no way out**: the model is out of
production, there are no service tools publicly available, there are no
key-combo entry points into fastboot/recovery on user firmware, and EDL requires
a signed programmer file that is not publicly available. Below are the specific
known pitfalls, but the list is not exhaustive: think before every command that
changes something.

- ⛔ **Do NOT interrupt** `fastboot flash ...` on partitions inside `super`
  (system/vendor/product/system_ext/odm). An interrupted flash leaves the
  Virtual A/B COW layout in a corrupted state - it can only be fixed via
  fastbootd (`reboot fastboot` → `delete-logical-partition <name>-cow`), which
  you may also not have for those very partitions.
- ⛔ **Do NOT run** `fastboot -w`, `fastboot erase userdata`,
  `fastboot erase metadata`: on this model recovery/format in some contexts
  cannot reformat metadata ("Permission denied" in mke2fs) - the only cure is
  flashing ready-made filesystem images, for which you need fastboot, which is
  exactly what is unavailable at the moment of the error.
- ⛔ Do NOT flash GPT and the boot chain from foreign packages.
- ⛔ **`fastboot boot <custom image>` - do NOT use it unless necessary.**
  There are no verified images for this model (there is nothing to load), and
  the price of a mistake is high. If you do try your own image, three conditions
  are mandatory:
  1) the image header must be strictly **v2** (v2 fields @1648 populated): with
     header_version 0/1 ABL does not compute DtbOffset/ImageSize and silently
     stays on the logo after OKAY - the kernel will not start at all; v3 is
     unusable: ABL will pull the stock vendor_boot off the flash and mix in a
     foreign init;
  2) the ramdisk test must **self-terminate**: a watchdog reboot
     ("bootloader") after N seconds on every branch, including hung ones;
     `panic=N` in the cmdline is NOT a substitute (a panic = a dirty reset);
  3) check in kernel.config **who feeds the watchdog** (either
     CONFIG_WATCHDOG + the qcom,wdog node, or point 2) - otherwise the
     PMIC watchdog will cut the device off after ~10 seconds of hang.
- ⛔ **Count the slot-retry budget during series of `fastboot boot`**: every
  "dirty" reset (panic/watchdog) before userspace decrements the
  slot-retry-count of the active slot; once exhausted, ABL will mark it
  unbootable and switch to the second slot - where, on devices that have taken
  OTA updates, the old chain lives (an incompatible mix → an eternal loop with
  no entry points: key-combo transitions are closed, USB-host for a FASTBOOT
  flash drive does not come up). Before/after a series, check `fastboot getvar
  slot-retry-count:a/b`; once exhausted - `set_active <slot>` before continuing.
- ✅ Hypothetically safe: `getvar`, `oem device-info`, `flashing
  get_unlock_ability`, flashing an individual partition with an image that
  completed fully and for which you have the original (a backup or an OTA).

## 4.4 After the unlock

The phone is in a fastboot loop (that is the magic, not a breakdown). Go to
guide 05 first - restoring normal boot. Partition dumps are now possible from
fastbootd/bootloader-independent environments, but that is beyond the scope of
this repository; here the unlock is the end goal.
