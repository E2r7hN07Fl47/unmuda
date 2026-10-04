# 05 — Возврат нормальной загрузки (снятие магии)

С магией `LOOTBFCK` в chkcode телефон при КАЖДОЙ загрузке входит в
fastboot. Android не стартует. Это ожидаемое поведение сервисного режима,
а не кирпич. Снятие магии возвращает обычную загрузку.

## 5.1 Снятие магии из fastboot (нужен разблокированный/сервисный fastboot)

```bash
# подготовить образ нулей (один раз):
python3 -c "open('chkcode_zero.img','wb').write(bytes(0x80000))"

fastboot flash chkcode chkcode_zero.img
fastboot reboot
```

Телефон загрузится в Android (с предупреждением о разблокированном
загрузчике — оранжевое состояние; это нормально и неизбежно после анлока).

## 5.2 Снятие магии без fastboot (телефон ещё в Android,diag-композиция)

Если телефон ещё в системе и вы просто откатываете эксперимент:

```bash
cd tools
python3 kdiag_shell.py "setprop vendor.kc.diag.status start"
python3 - <<'PY'
from diag_transport import open_transport
from fs_sys_call import FSDiag, O_RDWR, SEEK_SET
fs = FSDiag(open_transport())
fd = fs.open("/dev/block/bootdevice/by-name/chkcode", O_RDWR)
fs.lseek(fd, 0, SEEK_SET)
fs.write(fd, bytes(8))          # 8 нулей поверх LOOTBFCK
fs.lseek(fd, 0, SEEK_SET)
print("после записи:", fs.read(fd, 16).hex())
fs.close(fd)
PY
```

## 5.3 Восстановление из бэкапа (если магию надо снять вместе со всем разделом)

```bash
cd tools
python3 - <<'PY'
import sys
from pathlib import Path
from diag_transport import open_transport
from fs_sys_call import FSDiag, O_RDWR, SEEK_SET
data = Path("chkcode_backup.bin").read_bytes()
assert len(data) == 0x80000, "бэкап не того размера"
fs = FSDiag(open_transport())
fd = fs.open("/dev/block/bootdevice/by-name/chkcode", O_RDWR)
fs.lseek(fd, 0, SEEK_SET)
sent = 0
while sent < len(data):
    sent += fs.write(fd, data[sent:sent+0x400])
fs.lseek(fd, 0, SEEK_SET)
check = fs.read(fd, 16)
print("первые 16 байт после отката:", check.hex())
fs.close(fd)
PY
```

## 5.4 Если что-то пошло не так: карта известных состояний

| Симптом | Причина | Лечение |
|---|---|---|
| После `flashing unlock` телефон циклится: лого → ребут | Разблокировка требует очистки данных, а затёртые/чужеродные userdata/metadata не монтируются | НЕ стирать ничего вслепую. Из fastbootd НЕ делать `fastboot -w`/erase metadata (см. 4.3). Прошивать ГОТОВЫЕ файловые образы разделов, созданные на компьютере (ext4 для metadata; f2fs для userdata), а не полагаться на форматирование на устройстве |
| `fastboot` не видит телефон, телефона нет в | Магия снята, unlock есть, но загрузка падает до инициализации USB | Магия chkcode снимается только записью — держите её, пока не убедитесь, что Android грузится; проверяйте каждый шаг перезагрузкой ПОСЛЕ снятия |
| Device unlocked: false после подтверждения | Подтверждение не принято / таймаут меню | Повторить `flashing unlock`, подтвердить кнопками в течение ~10 c |
| Цикл recovery-установки OTA | В misc записан BCB `boot-recovery` | КРИТИЧНО: до записи BCB убедитесь, что у вас есть способ попасть в fastboot (магия chkcode!) — с магией ABL входит в fastboot ДО обработки BCB-цикла, и misc можно стереть (`fastboot flash misc` нулей). Без магии такой цикл = ловушка (горький опыт авторов) |

## 5.5 Резюме безопасного цикла

```
Android + diag ──► бэкап chkcode ──► запись LOOTBFCK ──► fastboot unlock
                                                                    │
        Android (норм. загрузка) ◄── flash chkcode нулей ◄──────────┘
        (проверка загрузки ДО снятия магии не требуется: с магией
         телефон всегда доступен через fastboot — это и есть страховка)
```
