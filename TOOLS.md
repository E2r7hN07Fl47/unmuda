# TOOLS — полный перечень инструментов

Всё ставится на обычный Linux (x86_64) или Windows 10/11 (x64). WSL не нужен.
Альтернатива на Nix — `nix-shell` из корня репозитория (см. `shell.nix`):
готовое окружение с python+pyusb, libusb, adb/fastboot и утилитами для образов.

## 1. Обязательное

| Инструмент | Версия | Linux | Windows | Зачем |
|---|---|---|---|---|
| Python | ≥ 3.9 | `sudo apt install python3 python3-pip` (или дистрибутив python.org) | https://python.org (галка Add to PATH) | все скрипты tools/ |
| pyusb | ≥ 1.2 | `pip3 install --user pyusb` | `pip install pyusb` | USB-DIAG |
| libusb-1.0 | 1.0.x | `sudo apt install libusb-1.0-0` | см. п. 3 (Zadig ставит WinUSB сам; для pyusb нужна libusb.dll — см. ниже) | бэкенд pyusb |
| Android platform-tools | ≥ 34 | `sudo apt install adb fastboot` ИЛИ https://developer.android.com/studio/releases/platform-tools | тот же сайт (zip, распаковать, добавить в PATH) | adb, fastboot |

### Windows: libusb-backend для pyusb (один раз)

pyusb работает с libusb-1.0.dll:

1. Скачать https://github.com/libusb/libusb/releases (напр. libusb-1.0.27.7z).
2. Из архива `VS2015-x64/dll/libusb-1.0.dll` положить в ту же папку, где
   python.exe (или в системный PATH).
3. Проверка: `python -c "import usb; print(usb.backend.libusb1.get_backend())"`
   — должен вернуться объект, не None.

### Windows: WinUSB-драйвер на DIAG-интерфейс телефона — Zadig

https://zadig.akeo.ie → Options → List All Devices → выбрать
**BALMUDA_Android (Interface 0)** → драйвер **WinUSB** → Replace.
НЕ менять драйвер у родительского composite-устройства и у Interface 2
(сломаете adb/MTP).

### Linux: права на USB без root (по желанию)

```bash
sudo tee /etc/udev/rules.d/51-balmuda.rules <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="0482", MODE="0666"
EOF
sudo udevadm control --reload && sudo udevadm trigger
```

(Или запускать скрипты через sudo. Для diag-композиции qcserial может
занять интерфейс: `sudo rmmod qcserial` перед работой.)

## 2. Используется в инструкции опционально

| Инструмент | Зачем | Где |
|---|---|---|
| picocom/minicom (Linux) | AT-порт как tty | `sudo apt install picocom` (появляется /dev/ttyUSB* при qcserial) |
| 7-Zip / tar | распаковка | штатно |

## 3. Уже включено в репозиторий (tools/)

| Файл | Назначение |
|---|---|
| `diag_transport.py` | QCDM/HDLC-транспорт поверх USB (обе ОС) |
| `cve31317.py` | переключение USB-композиции в diag,modem,adb (CVE-2024-31317) |
| `kdiag_shell.py` | shell-команды на телефоне (subsys 0xFC cmd 0x2080/0x2081) |
| `fs_sys_call.py` | open/read/write/lseek через fs_sys_call_diag (0x2000) |
| `backup_chkcode.py` | дамп chkcode (обязателен перед анлоком) |
| `unlock_chkcode.py` | запись LOOTBFCK с проверками и защитой от отсутствия бэкапа |
| `exfil.py` | вытягивание произвольных файлов с телефона |
| `at_console.py` | AT-команды модему (interface 1) |
| `requirements.txt` | `pip install -r requirements.txt` |

## 4. Что НЕ требуется (важно)

- WSL, usbipd, виртуальные машины — не нужны нигде.
- Root, Magisk, TWRP — не нужны для самого анлока.
- Платные unlock-сервисы — не нужны и бессмысленны для этого метода.
