# 02 — Подъём diag-режима (USB-композиция diag,modem,adb)

Диаг-бэкдор Kyocera живёт в USB-интерфейсе, который телефон выставляет
только в композиции `diag,modem,adb`. После каждой перезагрузки телефона
композиция сбрасывается в `mtp,adb` — шаг придётся повторять.

## 2.1 Переключение композиции

Из каталога `tools/`:

```bash
python3 cve31317.py            # Linux
python cve31317.py --adb adb   # Windows (adb.exe в PATH)
```

Скрипт: отключает USAP-пул, собирает payload CVE-2024-31317, толкает на
телефон и дёргает спавн приложения до переключения `sys.usb.config`
(до 12 попыток; после перезагрузки телефона срабатывает легче).

Успех:

```bash
adb shell getprop sys.usb.config   # diag,modem,adb
```

USB-устройство переенумерируется: **0482:0a9d** (было 0482:0a74).

## 2.2 Драйвер на Windows (Linux пропустить)

Композиция — составное USB-устройство: интерфейс 0 = DIAG, 1 = modem(AT),
2 = adb. adb работает через штатный драйвер Android; для DIAG-интерфейса
нужен WinUSB:

1. Скачайте Zadig (https://zadig.akeo.ie).
2. Options → List All Devices.
3. В выпадающем списке выберите **BALMUDA_Android (Interface 0)**
   (НЕ родительский composite и НЕ Interface 2 — иначе сломаете adb!).
4. Стрелками выберите целевой драйвер **WinUSB** → Replace Driver.
5. Проверка: `python -c "import usb.core; print(usb.core.find(idVendor=0x0482,idProduct=0x0a9d))"`
   должен печатать объект устройства, а не None.

Возврат стока драйвера после работы (когда вернётесь в mtp,adb):
диспетчер устройств → удалить устройство с драйвером WinUSB → переподключить.

## 2.3 Проверка диаг-канала

```bash
cd tools
python3 -c "from diag_transport import open_transport; t=open_transport(); print('DIAG OK' if t.ping() else 'нет ответа')"
```

(Windows: то же с `python`.)

Диаг-канал отвечает — переходим к гайду 03 (дампы без анлока) или 04 (анлок).

## Troubleshooting

| Симптом | Причина/лечение |
|---|---|
| cve31317: все попытки `sys.usb.config=mtp,adb` | Перезагрузите телефон и повторите; проверьте SPL (гайд 01); на свежезагруженном устройстве USAP-пул пуст |
| `ping()` печатает `нет ответа`, но VERNO сырым фреймом с CRC отвечает | всё в порядке — обновите репозиторий: транспорт старой версии шлёт фреймы без CRC (гайд 06 §6.1, баг A) |
| `Device or resource busy` при open_transport (Linux) | `sudo rmmod qcserial` или отпустить интерфейс: `sudo fuser -k /dev/bus/usb/...` |
| Windows: `No backend available` | Не установлен libusb — см. TOOLS.md (pyusb + libusb dll) |
| adb пропал после переключения | Это нормально на миг переенумерации; вернётся как Interface 2. Если нет — переподключите кабель |
