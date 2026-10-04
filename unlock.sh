#!/usr/bin/env bash


#   Made by Mamkin_Xakep
#   Assisted by Google Gemini


# Строгий режим: прерывать работу при любой ошибке
set -e
set -u
set -o pipefail

echo 'Эта утилита предназначена для разблокировки загрузчика на смартфонах Balmuda Phone.'
echo 'Использование этой программы влечёт собой потерю всех данных на телефоне.'
echo 'Ни автор, ни кто-либо другой не несёт ответственности за возможные убытки.'
echo 'Все действия вы выполняете на свой страх и риск.'
echo

read -p "Вы согласны? [y/N]: " response
response=${response,,}

if [[ "$response" != "y" && "$response" != "yes" ]]; then
    echo "Процедура отменена. Хорошего дня."
    exit 0
fi

echo 'Согласие получено. Производится процедура разблокировки загрузчика...'

# 1. ПРОВЕРКА ЗАВИСИМОСТЕЙ И ПОДКЛЮЧЕНИЯ
command -v adb >/dev/null 2>&1 || { echo "Ошибка: ADB не установлен!"; exit 1; }
command -v fastboot >/dev/null 2>&1 || { echo "Ошибка: Fastboot не установлен!"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Ошибка: Python3 не установлен!"; exit 1; }

echo 'Ожидание устройства в режиме ADB...'
adb wait-for-device
ADB_AUTH=$(adb devices | grep -w "device" | wc -l)
if [ "$ADB_AUTH" -lt 1 ]; then
    echo "Ошибка: Устройство подключено, но не авторизовано. Разрешите отладку на экране телефона!"
    exit 1
fi

# 2. ЭКСПЛУАТАЦИЯ И ЗАПУСК DIAG
echo 'Активация DIAG-интерфейса...'
python3 tools/cve31317.py
python3 kdiag_shell.py "setprop vendor.kc.diag.status start"
echo 'Готово!'

# 3. КРИТИЧЕСКИЙ ЭТАП: БЭКАП CHKCODE
echo 'Производится резервное копирование раздела chkcode...'
if [ -f "chkcode_backup.bin" ]; then
    echo "Предупреждение: Старый файл chkcode_backup.bin удален для создания свежего бэкапа."
    rm chkcode_backup.bin
fi

python3 tools/backup_chkcode.py -o chkcode_backup.bin

# Проверяем, что файл бэкапа существует и он не пустой (размер > 0 байт)
if [ ! -s "chkcode_backup.bin" ]; then
    echo "КРИТИЧЕСКАЯ ОШИБКА: Бэкап раздела chkcode не создался или пуст! Остановка скрипта для предотвращения кирпича."
    exit 1
fi
echo 'Бэкап успешно создан и проверен!'

# 4. МОДИФИКАЦИЯ РАЗДЕЛА CHKCODE
echo 'Запись волшебного слова в раздел chkcode...'
python3 tools/unlock_chkcode.py --backup chkcode_backup.bin
echo 'Готово!'

# 5. ПЕРЕХОД В FASTBOOT С ПРОВЕРКОЙ СВЯЗИ
echo 'Перезагрузка в режим fastboot...'
adb reboot bootloader

echo 'Ожидание подключения в режиме fastboot (около 10 секунд)...'
sleep 7

# Проверяем, видит ли fastboot устройство
FASTBOOT_CHECK=$(fastboot devices)
if [ -z "$FASTBOOT_CHECK" ]; then
    echo "КРИТИЧЕСКАЯ ОШИБКА: Телефон ушел в перезагрузку, но режим Fastboot не определился в системе!"
    echo "Пожалуйста, проверьте USB-кабель/драйверы и НЕ закрывайте этот терминал."
    exit 1
fi
echo 'Устройство успешно найдено в режиме Fastboot!'

# 6. РАЗБЛОКИРОВКА ЗАГРУЗЧИКА
echo 'Выполняется разблокировка загрузчика... Пожалуйста, подтвердите запрос на экране телефона!'
if ! fastboot flashing unlock; then
    echo "Ошибка: Команда разблокировки отклонена устройством или прервана."
    exit 1
fi
echo 'Готово!'

# 7. ОЧИСТКА РАЗДЕЛА (ВОЗВРАТ К СТАНДАРТНОМУ CHKCODE)
echo 'Удаление волшебного слова...'
python3 -c "open('chkcode_zero.img','wb').write(bytes(0x80000))"

if [ ! -s "chkcode_zero.img" ]; then
    echo "Ошибка: Не удалось создать chkcode_zero.img"
    exit 1
fi

if ! fastboot flash chkcode chkcode_zero.img; then
    echo "ВНИМАНИЕ: Ошибка при прошивке чистого chkcode! Не перезагружайте телефон вручную!"
    exit 1
fi
echo 'Готово!'

# 8. ФИНАЛЬНАЯ ПЕРЕЗАГРУЗКА
echo 'Перезагрузка...'
fastboot reboot
echo 'Готово!'

echo 'Разблокировка загрузчика успешно произведена. Если вы столкнулись с какими-то ошибками в работе, сообщите нам пожалуйста в Github Issues.'
