# unmuda - Утилита для разблокировки загрузчика Balmuda Phone

Позволяет открыть загрузчик для прошивки стороннего ПО на Balmuda Phone 

Метод основан на сервисном DIAG-бэкдоре Kyocera (subsys 0xFC), который
доступен в USB-композиции `diag,modem,adb`, и на сервисной проверке
`KcFastbootCheck()` в загрузчике (магия `LOOTBFCK` в разделе chkcode).

---
# **AI Disclosure - весь скрипт (и часть инструкций) написан с использованием ИИ. Не пользуйтесь данным инструментом, если вас это не устраивает.**
---

> [!WARNING]
> Ни автор, ни кто-либо, участвующий в создании, разработке, тестировании и/или популяризации данного ПО, не несёт ответственности за неисправности, ошибки, потерю данных, неполученную прибыль и прочие возможные убытки, возникшие в результате использования данной утилиты. Все действия вы выполняете на свой страх и риск.

> [!IMPORTANT]
> Разблокировка загрузчика провоцирует стирание всех данных и сброс до заводских настроек, а также может повлечь в аннулировании гарантии. Позаботьтесь о бекапах перед началом процедуры

## Требования

1. Balmuda Phone A101BM на версии прошивки 1.220PO - 1.280PO (X01A на -MI версиях прошивки не тестировались) со включенной отладкой по USB и активированным пунктом "Заводская разблокировка"
2. USB-C кабель с возможностью передачи данных
3. Компьютер\Ноутбук\Планшет с ОС Linux или Windows с WSL (на Windows без WSL и macOS не тестировалось)

## Подготовка

### На телефоне

1. На телефоне открыть "Настройки"
2. Перейти в раздел "О телефоне"
3. 7 раз нажать на пункт "Номер сборки"
4. Подтвердить намерения вводом пароля (при необходимости)
5. Вернуться назад, открыть пункт "Система"
6. Открыть "Для разработчиков"
7. Активировать "Заводская разблокировка" и "Отладка по USB"

### На компьютере

Необходимо установить ряд зависимостей:

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

## Применение

### На Linux

```shell
sh unlock.sh
```

Скрипт предложит произвести процедуру разблокировки, отвечаем `yes`

В случае необходимости, разблокируйте телефон и нажмите "Разрешить" в появившемся окне о запросе разрешения на подключение компьютера ADB и ждём перезагрузки телефона

После перезагрузки телефона в fastboot кнопками громкости выбираем `Unlock the bootloader`

Телефон перезагрузится снова в fastboot, после чего перезапустится уже в систему с полным стиранием всех данных (вы же позаботились о резервной копии важных данных, верно?)


## Ограничения

На телефоне ни в коем случае нельзя производить прошивку через fastboot, это почти со 100% шансом превратит телефон в кирпич, достать из состояния которого будет очень непросто.

## Авторы

В разработке и тестировании утилиты участвовали:

1. E2r7hN07Fl47: [GitHub](https://github.com/E2r7hN07Fl47)
2. Mamkin_Xakep: [e-mail](mailto:mamkin@xakep.xyz), [Telegram](https://t.me/Mamkin_Xakep_bot)
3. radio_mudrec: [4pda](https://4pda.to/forum/index.php?showuser=9245164) - багфиксы в unlock.sh
4. Stoobyy: [GitHub](https://github.com/Stoobyy) - Перевод на английский, багфиксы

## Используемые LLM

Основной моделью для разработки была GLM 5.3 за авторством [Z.ai](https://chat.z.ai) (ex-Zhipu AI)

Вспомогательным инструментом был приватный Telegram-бот за авторством Lach: [GitHub](https://github.com/CertainLach)

Для перевода и внешнего анализа использовалась неизвестная модель Claude за авторством Antropic. (В пользовании Stoobyy)

## Special thanks

This project builds upon the discovery, patching, and subsequent research of **CVE-2024-31317** (Android Zygote Command Injection). Special thanks to the security researchers and teams who made this work possible:

### Vulnerability Discovery
* **Meta Red Team X** — Discovered the original vulnerability in the Android Framework and responsibly disclosed it to Google.

###  Patching & Security Coordination
* **Google Android Security Team** — Validated the vulnerability and released the official fix in the June 2024 Android Security Bulletin.

### Technical Analysis & PoC Development
* **JD Labs (京东獬豸信息安全实验室)** — Conducted an in-depth technical analysis and architectural comparison with historical attacks.
* **agg23** — Created comprehensive documentation and detailed breakdowns of the injection architecture.
* **rabits** — Developed and published the functional Proof-of-Concept (PoC) exploit showcasing privilege escalation via ADB.
