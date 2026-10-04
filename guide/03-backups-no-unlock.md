# 03 — Дампы БЕЗ разблокировки загрузчика

Что реально доступно до анлока, а что нет — честная таблица
(проверено на 1.280PO.0686.a):

| Цель | Путь | Статус |
|---|---|---|
| **Раздел chkcode** (512 КиБ) | fs_sys_call read — SELinux домена ровно это и разрешает | ✅ проверено |
| Произвольные файлы (vendor, система, /mnt/vendor/persist) | exfil.py через kdiag_shell | ✅ проверено |
| Вывод shell-команд (uid=system) | kdiag_shell.py 0x2081 | ✅ проверено |
| AT-команды модема | USB interface 1 (см. ниже) | ✅ проверено |
| Разделы boot/system/vendor/… | НЕТ до анлока: ни один диаг-домен не имеет SELinux-права на их blk_device | ❌ невозможно этим методом |
| devinfo | НЕТ (SELinux; состояние и так дублируется в fastboot `getvar`) | ❌ |

Всё выполняется с диаг-композицией из гайда 02.

## 3.1 Бэкап chkcode — обязателен перед любым анлоком

```bash
cd tools
python3 backup_chkcode.py -o chkcode_backup.bin
```

Результат: `chkcode_backup.bin` + `.sha256`. На стоковом устройстве раздел
обычно целиком нули/FF — файл всё равно сохраняйте (это ваш эталон для восстановления).

## 3.2 Произвольные файлы (exfil)

```bash
python3 exfil.py /vendor/bin/fs_sys_call_diag .      # пример: бинарник демона
python3 exfil.py /vendor/etc/init/init.kdmc.rc .     # конфиг diag-сервисов
```

Скорость ~1 КиБ/с (чанки по 200 байт) — для больших файлов терпеливо.
Файлы, запрещённые SELinux для uid=system, вернут ошибку/0 байт — это
ограничение метода, а не сбой скрипта.

## 3.3 Shell-команды (диагностика)

```bash
python3 kdiag_shell.py "id"
# uid=1000(system) gid=0(root) groups=0(root),1000(system),2901(vendor_qti_diag)
# context=u:r:kdiag_common:s0

python3 kdiag_shell.py "getprop ro.build.fingerprint"
python3 kdiag_shell.py "ls -la /dev/block/bootdevice/by-name/"
```

Запуск diag-демонов (нужен для fs_sys_call):

```bash
python3 kdiag_shell.py "setprop vendor.kc.diag.status start"
```

## 3.4 AT-команды (модем; USB interface 1, bulk 0x02/0x82)

AT-порт появляется в той же диаг-композиции. Скрипт `at_console.py`
работает напрямую через USB на обеих ОС:

```bash
python3 at_console.py ATI "AT+CLAC"       # версии + полный список команд
python3 at_console.py                     # интерактивно
```

На Linux порт может также определиться как /dev/ttyUSB* (qcserial) —
тогда альтернативно `picocom /dev/ttyUSB1`. Записывающих команд в AT
у этой модели нет — канал по сути read-only.

Полезное: `ATI` (версии), `AT+CLAC` (259 команд), `AT$QCPDPP?` (PDP-профили).

## 3.5 Что НЕЛЬЗЯ делать из этого гайда

- ⛔ НЕ пытаться `dd`/записывать что-либо в blочные устройства через
  kdiag_shell: SELinux запрещает, а `fs_sys_call` на чужие разделы вернёт
  ошибку open. Единственный разрешённый блочный раздел — chkcode,
  и его трогаем только скриптами из гайда 04.
- ⛔ НЕ стирать и не прошивать разделы до того, как получен анлок
  и прочитан гайд 05 (возврат нормальной загрузки).
