# shell.nix — окружение для разблокировки BALMUDA Phone (A101BM)
# Часть репозитория A101BM-unlock.
#
# Использование:
#   nix-shell            # из корня репозитория
#   cd tools && python3 cve31317.py ...
#
# Замечания:
#  - udev-правила для USB без root на NixOS:
#      services.udev.extraRules = ''
#        SUBSYSTEM=="usb", ATTR{idVendor}=="0482", MODE="0666"
#      '';
#    На обычном Linux можно temporary: sudo chmod 666 /dev/bus/usb/*/* или udev-файл из TOOLS.md.
#  - На не-NixOS дистрибутивах без nix — ставить по TOOLS.md репозитория.

{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "a101bm-unlock";

  buildInputs = with pkgs; [
    # python + единственная зависимость скриптов tools/
    (python3.withPackages (ps: with ps; [
      pyusb
    ]))

    # бэкенд libusb для pyusb
    libusb1

    # adb + fastboot (нативные Linux)
    android-tools

    # диагностика USB (lsusb)
    usbutils

    # AT-порт как tty, если qcserial занял интерфейс (альтернатива at_console.py)
    picocom

    # вспомогательное для работы с образами разделов (не обязательно для анлока)
    e2fsprogs      # mke2fs/debugfs — ext4 (metadata)
    f2fs-tools     # mkfs.f2fs/sload.f2fs — userdata
    xz             # распаковка образов
  ];


}
