#!/bin/bash

# ============================================================================== #
#  Скрипт автоматической настройки контроллера "Beer Tap System"
#  Версия: 3.0
# ============================================================================== #

# Прерывать выполнение скрипта при любой ошибке
set -e

echo "=== Шаг 1: Установка системных пакетов ==="
sudo apt-get update
sudo apt-get install -y \
    pcscd \
    libccid \
    python3-pyscard \
    python3-gpiozero \
    python3-lgpio \
    build-essential \
    swig \
    libpcsclite-dev \
    pkg-config

echo "=== Шаг 2: Настройка прав и групп ==="
sudo usermod -aG plugdev $USER
sudo usermod -aG lp $USER
sudo usermod -aG gpio $USER

echo "=== Шаг 3: Настройка Polkit ==="
cat <<EOF | sudo tee /etc/polkit-1/rules.d/45-pcscd.rules
polkit.addRule(function(action, subject) {
    if ((action.id == "org.debian.pcsc-lite.access_pcsc" || 
         action.id == "org.debian.pcsc-lite.access_card") &&
        subject.isInGroup("plugdev")) {
        return polkit.Result.YES;
    }
});
EOF

echo "=== Шаг 4: Настройка служб ==="
sudo systemctl enable pcscd && sudo systemctl start pcscd

echo "=== Шаг 5: Настройка виртуального окружения ==="
if [ -d "venv" ]; then
    echo "--> Удаление старого окружения 'venv'..."
    rm -rf venv
fi
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install gpiozero pyscard requests
deactivate

echo "=== Шаг 6: Финализация ==="
sudo chown -R $USER:$USER .
echo "Настройка завершена! Перезагрузите систему: sudo reboot"