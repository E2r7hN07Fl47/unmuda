# 06 — Анлок на устройстве с ПУСТЫМ разделом sysprop (retail-норма)

Самый главный гайд репозитория: универсальный путь анлока, не зависящий от
состояния раздела `sysprop`. Проверен на A101BM **1.220PO.0663.a** (первый
билд Android 12, SPL 2022-09, factory reset, sysprop полностью нулевой).
Если гайд 03/04 у вас заработал «как есть» — этот гайд даёт то же самое
проще; если не заработал (BAD_CMD на всё, `vendor.kc.diag.fact` пуст) —
вы здесь и это НОРМАЛЬНОЕ состояние устройства, а не поломка.

---

## 6.0 Кто этот гайд

Два состояния телефона A101BM, встречающиеся в рознице:

| Признак | «Сервисный» (меньшинство) | «Розничный» (большинство) |
|---|---|---|
| Раздел `sysprop` | валидный (записан на заводе/сервисе) | полностью нулевой |
| `getprop vendor.kc.diag.fact` | `kcfactoff` (или `kcfacton`) | пусто |
| Класс демонов `kc_diag` | стартует сам по init-триггеру | НЕ стартует никогда |
| `kdiag_shell.py "setprop vendor.kc.diag.status start"` | поднимает класс | класс не поднимается |
| DIAG subsys 0xFC из коробки | отвечает | **тоже отвечает** — но демон надо запустить руками (см. 6.3) |

Ключевой факт, установленный реверсом `kdiag_common` (бинарник 1.230) и
ядра msm-4.19 (исходники 1.200): **регистрация обработчиков subsys 0xFC в
ядре — чисто локальная операция** (`ioctl DIAG_IOCTL_COMMAND_REG` →
`list_add` в `cmd_reg_list` ядра; согласование с модемом НЕ требуется).
Никакой «заводской инициализации DIAG routing» не существует — демону
`fs_sys_call_diag` достаточно просто быть запущенным.

## 6.1 Почему у вас могло «не работать» раньше: два бага-двойника

### Баг A: фреймы без CRC (главный)

`tools/diag_transport.py` до фикса отправляла HDLC-фреймы **без CRC16**:
`escape(payload) + 0x7E`. Ядро diag на чистом буте работает в HDLC-режиме:
`crc_check()` не проходит → `diag_send_error_rsp()` → BAD_CMD-эхо `0x13`
**на любую команду, включая VERNO**. Ответ приходит за ~65 мс (внутренний
таймаут hdlc-декодера), что маскировалось под «модем думает и отвергает».

Баг был незаметен на части устройств: после старта некоторых диаг-клиентов
ядро переходит в non-HDLC режим (`hdlc_disabled=1`), где CRC не проверяется.
На чистом буте CRC проверяется всегда.

С фиксом (коммит «diag_transport: CRC16 в TX-фрейме + автовыбор режима»)
транспорт сам подбирает режим: шлёт с CRC, при BAD_CMD-эхе перещёлкнется
на без-CRC и перешлёт. Никаких флагов пользователю не нужно.

**Диагностика до/после фикса** (сырой эталонный запрос, если сомневаетесь):

```python
# tools/: python3 -c "from diag_transport import open_transport; \
#   t=open_transport(); print('DIAG OK' if t.ping() else 'нет ответа')"
```

`ping()` = VERNO (0x00). Правильный ответ начинается с `0x00` и содержит
строку вида «Aug 19 2022 ... saipan.g» (это отвечает ядро/AP, не модем).
Ответ `13 00 7e` (или длинное эхо запроса с `0x13` в начале) — команда
отвергнута: либо транспорт без фикса, либо не запущен демон (6.3).

### Баг B: триггер класса kc_diag зависит от sysprop

Старый путь (гайд 04 §4.1) поднимал демены через
`kdiag_shell.py "setprop vendor.kc.diag.status start"`. Это срабатывало
только при живом init-триггере:

```
on property:vendor.kc.diag.status=start && property:vendor.kc.diag.fact=kcfactoff
    class_start kc_diag
```

`vendor.kc.diag.fact` выставляет `kcjprop_d`, читая раздел `sysprop`.
Пустой раздел → свойство никогда не установится → класс не стартует.
**Обход: запустить сервис напрямую** — `setprop ctl.start <имя>`.
init выполняет ctl.start для любого объявленного сервиса, минуя триггеры,
классы и условия. Ровно так же init запустил бы его сам (тот же seclabel,
тот же домен, те же группы) — это не обход SELinux, а штатный механизм
управления сервисами, доступный uid=1000 через CVE-2024-31317.

## 6.2 Что НЕ нужно пробовать (выстраданный список, не теряйте время)

- **kcjprop HAL** (`getService()/get()/set()` из wrapper через APK-CLASSPATH):
  работает (RC=0 у reset-ключей), но инициализировать пустой `sysprop` им
  нельзя — в интерфейсе нет create/init; все data-ключи возвращают RC=9
  «key unknown». Тупик, зафиксирован на практике.
- **Fact-версии демонов** (`fs_sys_call_diag_fact`, `kdiag_common_fact`,
  `kdiag_shell_fact`, класс `kc_fact_diag`, user root): у них в init.kdmc.rc
  `group root` **без** `vendor_qti_diag` → `/dev/diag` недоступен по DAC,
  а `cap_dac_override` в их SELinux-домене запрещён (AVC permissive=0) →
  процесс умирает на `Diag_LSM_Init`. Не работают В ПРИНЦИПЕ, не стартуйте.
- **`setprop vendor.kc.diag.fact=kcfactoff` руками** — свойство пишется,
  но kcjprop_d его перетирает/не подтверждает; даже если бы держалось —
  у класса kc_diag другие условия. Просто используйте ctl.start.
- **AT-команды** (интерфейс 1 в композиции): базовые Qualcomm есть,
  заводских/factory — нет. Не путь к разделам.
- **Обновление/даунгрейд прошивки ради diag**: DIAG жив на любой версии,
  дело было в транспорте (баг A) и в незапущенном демоне (баг B).

## 6.3 Пошаговая процедура (Linux; отличия Windows — в скобках)

Все команды — из каталога `tools/`. Устройство: загрузчен Android, adb
авторизован, экран разблокирован (после каждой перезагрузки — заново).

### Шаг 1. Подъём diag-композиции

```bash
adb shell getprop sys.usb.config        # ожидаем mtp,adb (после ребута)
python3 cve31317.py                     # (Windows: python cve31317.py --adb adb)
adb shell getprop sys.usb.config        # теперь diag,modem,adb
lsusb | grep 0a9d                       # (Windows: диспетчер устройств/Zadig, см. 02 §2.2)
```

USB переенумерация: adb на миг пропадает — это нормально. Если после
переенумерации `adb devices` пуст или `no permissions` — перезапустите
adb-сервер и/или поправьте права на ноду устройства:

```bash
adb kill-server; adb start-server
# Linux: lsusb | grep 0482:0a9d  → Bus 001 Device 0NN
sudo chmod 666 /dev/bus/usb/001/0NN     # или udev-правило
```

Если все 12 попыток инъекции не сработали (`sys.usb.config=mtp,adb`) —
перезагрузите телефон и повторите: на свежезагруженном USAP-пул пуст,
инъекция срабатывает легче (деградация после 15–20 инъекций без ребута —
норма; симптом: Settings/IME подвисают — лечится только ребутом).

### Шаг 2. Запуск демона fs_sys_call_diag (ядро гайда)

```bash
python3 cve31317.py --cmd "setprop ctl.start fs_sys_call_diag ;" \
    --check-prop init.svc.fs_sys_call_diag=running
adb shell getprop init.svc.fs_sys_call_diag   # running
adb shell ps -A | grep fs_sys_call_diag       # живой процесс (user system)
```

Обычно хватает 1 попытки. Сервис `oneshot` и после запуска висит вечно
(спит в read на /dev/diag) — перезапускать до перезагрузки не нужно.

Дополнительно можно поднять и `kdiag_common` (нужен для `kdiag_shell.py`,
гайд 03): та же команда с `kdiag_common`. Для записи/чтения chkcode он
НЕ требуется.

### Шаг 3. Проверка канала (обязательная, read-only)

```bash
python3 -c "from diag_transport import open_transport; \
  t = open_transport(); print('DIAG OK' if t.ping() else 'НЕТ ОТВЕТА')"
python3 fs_sys_call.py --debug /dev/block/bootdevice/by-name/chkcode --size 16
```

Ожидание по второй команде: пары `req/resp` с заголовком `4b fc 00 20 ...`,
ответ НЕ начинается с `13`, в ответе на read — нули (залоченный сток).
Если ответ = эхо запроса с `0x13` в первом байте — демон не запущен
(вернитесь к шагу 2) либо транспорт старый (обновите репозиторий).

### Шаг 4. Бэкап chkcode (без него unlock_chkcode откажется)

```bash
python3 backup_chkcode.py -o chkcode_backup.bin
# Сохранено: chkcode_backup.bin (524288 байт)
# SHA-256: ... — зафиксируйте в записях
# Первые 16 байт: 00 00 ... — чистый раздел, это нормально
```

Файл и `.sha256` появятся в текущем каталоге. Храните вместе с записью
о юните (это ваш путь отката).

### Шаг 5. Запись магии LOOTBFCK

```bash
python3 unlock_chkcode.py --backup chkcode_backup.bin --yes
# Контрольное чтение (первые 16): 4c 4f 4f 54 42 46 43 4b 00 ...
# OK: LOOTBFCK записан и подтверждён.
```

Скрипт пишет ровно 8 байт по смещению 0 и перечитывает их для контроля.
С этого момента **телефон при каждой загрузке будет уходить в fastboot** —
это побочный эффект магии, а не поломка (снимается в гайде 05).

### Шаг 6. Разблокировка

```bash
adb reboot bootloader
fastboot devices                 # (Windows: fastboot.exe) серийник в списке
fastboot getvar unlocked         # unlocked: no (пока)
fastboot flashing unlock         # OKAY
fastboot getvar unlocked         # unlocked: yes
```

Нюанс: на части билдов `flashing unlock` возвращает `OKAY` мгновенно, без
экрана подтверждения; на других — появляется меню, подтвердите громкостью
ВВЕРХ. Сразу после unlock устройство переенумерируется (`fastboot getvar`
может один раз показать `< waiting for any device >`) — повторите команду.

### Шаг 7. Возврат нормальной загрузки

Данные при unlock стираются. Полный порядок — гайд 05 (снять магию:
`fastboot flash chkcode chkcode_backup.bin` — теперь разрешено, т.к.
unlocked; затем `fastboot reboot`, первичная настройка, заново авторизовать
adb по USB-отладке).

## 6.4 Разбор сбоев по шагам

| Симптом | Причина | Действие |
|---|---|---|
| cve31317: все попытки мимо | USAP-пул не пуст / деградация | перезагрузить телефон, повторить |
| `adb devices` пуст после 6.1 | adb-сервер/права ноды | kill-server/start-server; chmod 666 ноды |
| `pyusb: Resource busy` на open | интерфейс занят (qcserial/другой скрипт) | `sudo rmmod qcserial`; закрыть другие скрипты |
| ping() нет ответа | композиция не та / WinUSB не на том интерфейсе | гайд 02 §2.2-2.3 |
| fs_sys_call: BAD_CMD-эхо | демон не запущен | шаг 2; проверить `ps -A | grep fs_sys` |
| fs_sys_call: «нет свободного fd-слота» | утечка слотов от прошлых сессий | `python3 fs_sys_call.py --close-slots` |
| unlock: «магия не подтвердилась» | сбой записи | НЕ перезагружать; восстановить бэкап (05 §5.3); повторить |
| fastboot: `flashing unlock` → FAIL not allowed | магии нет/стёрта | перечитать chkcode через fs_sys_call |
| unlock OKAY, но `unlocked: no` | не дождались переенумерации | повторить getvar через пару секунд |
| после `fastboot boot` телефон циклится без USB | вероятное исчерпание slot-retry активного слота и переключение на несовместимый старый (гайд 04 §4.3) | из любого доступного fastboot: `getvar current-slot`, `slot-retry-count:a/b`, затем `set_active <живой-слот>` |

## 6.5 Как это работает (справка для аудита)

1. **CVE-2024-31317** — инъекция аргументов в Zygote через настройку
   `hidden_api_blacklist_exemptions`: выполняет произвольную команду от
   uid=1000 (system) в домене system_app.
2. **`setprop ctl.start fs_sys_call_diag`** — штатный интерфейс init к
   управлению сервисами (доступен uid=1000). init форкает
   `/vendor/bin/fs_sys_call_diag` с seclabel из vendor file contexts:
   user system, group root+vendor_qti_diag — ровно как при «родном»
   старте класса kc_diag. SELinux-домен демона разрешает открыть
   `/dev/diag` и rw **только** blk_file класса `chkcode_block_device`.
3. **Регистрация 0xFC/0x2000–0x2004** — демон при старте делает
   `Diag_LSM_Init()` + `diagpkt_tbl_reg()`; ядро добавляет диапазон в
   локальный `cmd_reg_list` (`diag_cmd_add_reg`, proc=APPS_DATA). Никакого
   участия модема. (Проверено реверсом kdiag_common 1.230 и чтением
   drivers/char/diag из исходников ядра 1.200.)
4. **HDLC/CRC** — вход USB: `diagfwd_mux_read_done →
   diag_process_hdlc_pkt`: decode + `crc_check()`; в non-HDLC режиме
   (`hdlc_disabled=1`, выставляется некоторыми диаг-клиентами) CRC
   не проверяется. Отсюда автовыбор режима в транспорте.
5. **LOOTBFCK → KcFastbootCheck()** — см. гайд 04 §«как это работает»:
   ABL регистрирует полную таблицу fastboot-команд и пропускает проверки
   блокировки; `SetDeviceUnlock` для user-билдов требует только
   `KcFastbootCheck()==TRUE` (исходник ABL FastbootCmds.c, ветка
   TargetBuildVariantUser).

## 6.6 Отличия от «сервисного» пути (гайды 03–04)

| | Гайд 03/04 (sysprop валиден) | Этот гайд (sysprop пуст) |
|---|---|---|
| Подъём демонов | `kdiag_shell.py "setprop vendor.kc.diag.status start"` | `cve31317.py --cmd "setprop ctl.start fs_sys_call_diag ;"` |
| Что доступно | shell (0x2081) + файловый I/O (0x2000) | только файловый I/O (0x2000) — достаточно для chkcode |
| Запись LOOTBFCK | одинаково: `unlock_chkcode.py --backup ... --yes` | то же |

Если хотите shell-команды на пустом sysprop — дополнительно
`ctl.start kdiag_common` (шаг 2), после этого `kdiag_shell.py` работает
как в гайде 03.
