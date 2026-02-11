#!/bin/bash

# ==============================================================================
#  Скрипт автоматической настройки контроллера "Beer Tap System"
#  Версия: 2.0
# ==============================================================================

# Прерывать выполнение скрипта при любой ошибке
set -e

echo "=== Шаг 1: Установка системных пакетов ==="
sudo apt-get update
sudo apt-get install -y \
    python3-pyscard \
    python3-gpiozero \
    python3-pigpio \
    swig \
    libpcsclite-dev \
    build-essential \
    pkg-config

echo "=== Шаг 2: Настройка служб ==="
sudo systemctl enable pcscd && sudo systemctl start pcscd
sudo systemctl enable pigpiod && sudo systemctl start pigpiod

echo "=== Шаг 3: Настройка виртуального окружения ==="
if [ -d "venv" ]; then
    echo "--> Удаление старого окружения 'venv'..."
    rm -rf venv
fi
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install requests
deactivate

echo "=== Шаг 4: Установка прав доступа ==="
sudo chown -R $USER:$USER .

echo "Настройка завершена!"