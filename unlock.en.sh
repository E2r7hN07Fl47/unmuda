#!/usr/bin/env bash


#   Made by Mamkin_Xakep
#   Assisted by Google Gemini
#   (English version of unlock.sh - logic unchanged, strings translated)


# Strict mode: abort on any error
set -e
set -u
set -o pipefail

echo 'This utility is intended for unlocking the bootloader on Balmuda Phone smartphones.'
echo 'Using this program entails the loss of all data on the phone.'
echo 'Neither the author nor anyone else is liable for possible losses.'
echo 'You perform all actions at your own risk.'
echo

read -p "Do you agree? [y/N]: " response
response=${response,,}

if [[ "$response" != "y" && "$response" != "yes" ]]; then
    echo "Procedure cancelled. Have a good day."
    exit 0
fi

echo 'Consent received. Performing the bootloader unlocking procedure...'

# 1. CHECKING DEPENDENCIES AND CONNECTION
command -v adb >/dev/null 2>&1 || { echo "Error: ADB is not installed!"; exit 1; }
command -v fastboot >/dev/null 2>&1 || { echo "Error: Fastboot is not installed!"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Error: Python3 is not installed!"; exit 1; }

echo 'Waiting for the device in ADB mode...'
adb wait-for-device
ADB_AUTH=$(adb devices | grep -w "device" | wc -l)
if [ "$ADB_AUTH" -lt 1 ]; then
    echo "Error: the device is connected but not authorized. Allow debugging on the phone screen!"
    exit 1
fi

# 2. EXPLOITATION AND STARTING DIAG
echo 'Activating the DIAG interface...'
python3 tools/cve31317.py
python3 tools/kdiag_shell.py "setprop vendor.kc.diag.status start"
echo 'Done!'

# 3. CRITICAL STAGE: CHKCODE BACKUP
echo 'Backing up the chkcode partition...'
if [ -f "chkcode_backup.bin" ]; then
    echo "Warning: the old chkcode_backup.bin file was removed to create a fresh backup."
    rm chkcode_backup.bin
fi

python3 tools/backup_chkcode.py -o chkcode_backup.bin

# Check that the backup file exists and is not empty (size > 0 bytes)
if [ ! -s "chkcode_backup.bin" ]; then
    echo "CRITICAL ERROR: the chkcode partition backup was not created or is empty! Stopping the script to prevent a brick."
    exit 1
fi
echo 'The backup was created successfully and verified!'

# 4. MODIFYING THE CHKCODE PARTITION
echo 'Writing the magic word into the chkcode partition...'
python3 tools/unlock_chkcode.py --backup chkcode_backup.bin
echo 'Done!'

# 5. REBOOTING INTO FASTBOOT WITH A LINK CHECK
echo 'Rebooting into fastboot mode...'
adb reboot bootloader

echo 'Waiting for a connection in fastboot mode (about 10 seconds)...'
sleep 12

# Check whether fastboot can see the device
FASTBOOT_CHECK=$(fastboot devices)
if [ -z "$FASTBOOT_CHECK" ]; then
    echo "CRITICAL ERROR: the phone went for a reboot, but fastboot mode was not detected by the system!"
    echo "Please check the USB cable/drivers and do NOT close this terminal."
    exit 1
fi
echo 'The device was successfully found in fastboot mode!'

# 6. UNLOCKING THE BOOTLOADER
echo 'Performing the bootloader unlock...'
fastboot flashing unlock
echo 'Please confirm the request on the phone screen!'
sleep 12
echo 'Done!'

# 7. CLEARING THE PARTITION (RETURNING TO THE STANDARD CHKCODE)
echo 'Removing the magic word...'
python3 -c "open('chkcode_zero.img','wb').write(bytes(0x80000))"

if [ ! -s "chkcode_zero.img" ]; then
    echo "Error: failed to create chkcode_zero.img"
    exit 1
fi

if ! fastboot flash chkcode chkcode_zero.img; then
    echo "WARNING: error while flashing the clean chkcode! Do not reboot the phone manually!"
    exit 1
fi
echo 'Done!'

# 8. FINAL REBOOT
echo 'Rebooting...'
fastboot reboot
echo 'Done!'

echo 'The bootloader unlock was completed successfully. If you encountered any errors in its operation, please report them to us in GitHub Issues.'
