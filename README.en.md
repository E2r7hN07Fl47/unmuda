# unmuda - Bootloader unlock utility for the Balmuda Phone

Lets you open the bootloader for flashing third-party software on the Balmuda Phone.

The method is based on Kyocera's service DIAG backdoor (subsys 0xFC), which is
available in the USB composition `diag,modem,adb`, and on the service check
`KcFastbootCheck()` in the bootloader (the `LOOTBFCK` magic in the chkcode
partition).

---
# **AI Disclosure - the entire script (and part of the instructions) was written with the use of AI. Do not use this tool if that does not suit you.**
---

> [!WARNING]
> Neither the author, nor anyone involved in the creation, development, testing and/or popularization of this software, is liable for malfunctions, errors, data loss, lost profit and other possible damages arising from the use of this utility. You perform all actions at your own risk.

> [!IMPORTANT]
> Unlocking the bootloader triggers erasure of all data and a reset to factory settings, and may also result in the warranty being voided. Take care of backups before starting the procedure.

## Requirements

1. Balmuda Phone A101BM on firmware version 1.220PO - 1.280PO (X01A on -MI firmware versions was not tested) with USB debugging enabled and the "Factory unlock" item activated
2. A USB-C cable capable of data transfer
3. A computer\laptop\tablet with Linux or Windows with WSL (Windows without WSL and macOS were not tested)

## Preparation

### On the phone

1. On the phone, open "Settings"
2. Go to the "About phone" section
3. Tap the "Build number" item 7 times
4. Confirm your intent by entering your password (if required)
5. Go back, open the "System" section
6. Open "For developers"
7. Enable "Factory unlock" and "USB debugging"

### On the computer

A number of dependencies need to be installed:

### Debian/Ubuntu

```shell
sudo apt install python3 python3-pyusb libusb-1.0-0 android-tools-adb android-tools-fastboot usbutils picocom
```

### Fedora

```shell
sudo dnf install python3 python3-pyusb libusb1 android-tools usbutils picocom
```

### Arch Linux

```shell
sudo pacman -S python python-pyusb libusb android-tools usbutils picocom
```

### Nix OS

```shell
cd tools
nix-shell
```

## Usage

### On Linux

```shell
bash unlock.sh
```

The script will offer to perform the unlocking procedure; answer `yes`.

If necessary, unlock the phone and press "Allow" in the window that appears
asking for permission to connect the computer via ADB, then wait for the phone
to reboot.

After the phone reboots into fastboot, use the volume buttons to select
`Unlock the bootloader`.

The phone will reboot into fastboot again, after which it will restart into the
system with a full wipe of all data (you did take care of a backup of your
important data, right?).


## Limitations

You must never flash via fastboot on this phone - it will almost certainly turn
the phone into a brick, and getting it out of that state will be very difficult.

## Authors

The following took part in the development and testing of the utility:

1. E2r7hN07Fl47: [GitHub](https://github.com/E2r7hN07Fl47)
2. Mamkin_Xakep: [e-mail](mailto:mamkin@xakep.xyz), [Telegram](https://t.me/Mamkin_Xakep_bot)

## LLMs used

The main model used for development was GLM 5.3 by [Z.ai](https://chat.z.ai) (ex-Zhipu AI).

An auxiliary tool was a private Telegram bot by Lach: [GitHub](https://github.com/CertainLach)

## Special thanks

This project builds upon the discovery, patching, and subsequent research of **CVE-2024-31317** (Android Zygote Command Injection). Special thanks to the security researchers and teams who made this work possible:

### Vulnerability Discovery
* **Meta Red Team X** - Discovered the original vulnerability in the Android Framework and responsibly disclosed it to Google.

###  Patching & Security Coordination
* **Google Android Security Team** - Validated the vulnerability and released the official fix in the June 2024 Android Security Bulletin.

### Technical Analysis & PoC Development
* **JD Labs (京东獬豸信息安全实验室)** - Conducted an in-depth technical analysis and architectural comparison with historical attacks.
* **agg23** - Created comprehensive documentation and detailed breakdowns of the injection architecture.
* **rabits** - Developed and published the functional Proof-of-Concept (PoC) exploit showcasing privilege escalation via ADB.

### Others
*  radio_mudrec: [4pda](https://4pda.to/forum/index.php?showuser=9245164) - for finding problems in unlock.sh
