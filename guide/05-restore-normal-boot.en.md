# 05 - Restoring normal boot (removing the magic)

With the `LOOTBFCK` magic in chkcode, the phone enters fastboot on EVERY boot.
Android does not start. This is the expected behaviour of the service mode, not
a brick. Removing the magic restores the normal boot.

## 5.1 Removing the magic from fastboot (requires an unlocked/service fastboot)

```bash
# prepare the zero image (once):
python3 -c "open('chkcode_zero.img','wb').write(bytes(0x80000))"

fastboot flash chkcode chkcode_zero.img
fastboot reboot
```

The phone will boot into Android (with the unlocked-bootloader warning - the
orange state; that is normal and unavoidable after an unlock).

## 5.2 Removing the magic without fastboot (phone still in Android, diag composition)

If the phone is still in the system and you are simply rolling back the experiment:

```bash
cd tools
python3 kdiag_shell.py "setprop vendor.kc.diag.status start"
python3 - <<'PY'
from diag_transport import open_transport
from fs_sys_call import FSDiag, O_RDWR, SEEK_SET
fs = FSDiag(open_transport())
fd = fs.open("/dev/block/bootdevice/by-name/chkcode", O_RDWR)
fs.lseek(fd, 0, SEEK_SET)
fs.write(fd, bytes(8))          # 8 zeros over LOOTBFCK
fs.lseek(fd, 0, SEEK_SET)
print("after the write:", fs.read(fd, 16).hex())
fs.close(fd)
PY
```

## 5.3 Restoring from the backup (if the magic must be removed along with the whole partition)

```bash
cd tools
python3 - <<'PY'
import sys
from pathlib import Path
from diag_transport import open_transport
from fs_sys_call import FSDiag, O_RDWR, SEEK_SET
data = Path("chkcode_backup.bin").read_bytes()
assert len(data) == 0x80000, "the backup is not the right size"
fs = FSDiag(open_transport())
fd = fs.open("/dev/block/bootdevice/by-name/chkcode", O_RDWR)
fs.lseek(fd, 0, SEEK_SET)
sent = 0
while sent < len(data):
    sent += fs.write(fd, data[sent:sent+0x400])
fs.lseek(fd, 0, SEEK_SET)
check = fs.read(fd, 16)
print("first 16 bytes after the rollback:", check.hex())
fs.close(fd)
PY
```

## 5.4 If something went wrong: a map of the known states

| Symptom | Cause | Treatment |
|---|---|---|
| After `flashing unlock` the phone loops: logo → reboot | The unlock requires a data wipe, and the wiped/foreign userdata/metadata do not mount | Do NOT erase anything blindly. From fastbootd do NOT do `fastboot -w`/erase metadata (see 4.3). Flash READY-MADE filesystem images of the partitions, created on the computer (ext4 for metadata; f2fs for userdata), rather than relying on formatting on the device |
| `fastboot` does not see the phone, the phone is not in (the list) | The magic is removed, the unlock is there, but boot fails before USB initialization | The chkcode magic is removed only by writing - keep it until you are sure Android boots; verify each step with a reboot AFTER removing |
| Device unlocked: false after confirmation | The confirmation was not accepted / menu timeout | Repeat `flashing unlock`, confirm with the buttons within ~10 s |
| OTA recovery-install loop | BCB `boot-recovery` written into misc | CRITICAL: before writing a BCB, make sure you have a way to get into fastboot (the chkcode magic!) - with the magic, ABL enters fastboot BEFORE processing the BCB loop, and misc can be erased (`fastboot flash misc` zeros). Without the magic such a loop = a trap (the authors' bitter experience) |

## 5.5 Summary of the safe cycle

```
Android + diag ──► chkcode backup ──► write LOOTBFCK ──► fastboot unlock
                                                                    │
        Android (normal boot) ◄── flash chkcode zeros ◄─────────────┘
        (checking the boot BEFORE removing the magic is not required:
         with the magic the phone is always reachable via fastboot -
         that is the safety net)
```
