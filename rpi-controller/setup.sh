#!/bin/bash

# ==============================================================================
#  Скрипт автоматической настройки контроллера "Beer Tap System"
#  Версия: 1.0
#  Назначение: Выполняет все необходимые системные настройки на "чистой"
#              системе Raspberry Pi OS Lite.
# ==============================================================================

# Прерывать выполнение скрипта при любой ошибке
set -e

echo "=== Шаг 1: Обновление системы и установка системных зависимостей ==="
sudo apt-get update
sudo apt-get install -y pcscd libpcsclite-dev python3-dev swig python3-venv sqlite3 git

echo ""
echo "=== Шаг 2: Настройка прав доступа и драйверов ==="

# 2.1. Отключение конфликтующих модулей ядра
echo "--> Создание black-листа для модулей NFC..."
sudo tee /etc/modprobe.d/raspi-blacklist.conf > /dev/null <<EOF
blacklist nfc
blacklist pn533
blacklist pn533_usb
EOF

# 2.2. Настройка прав доступа Polkit
echo "--> Создание правила Polkit для доступа к PC/SC..."
sudo tee /etc/polkit-1/rules.d/50-pcscd.rules > /dev/null <<EOF
// Allow users in the plugdev group to access the PCSC service and smart cards
polkit.addRule(function(action, subject) {
    if ((action.id == "org.debian.pcsc-lite.access_pcsc" || 
         action.id == "org.debian.pcsc-lite.access_card") &&
        subject.isInGroup("plugdev")) {
        return polkit.Result.YES;
    }
});
EOF

# 2.3. Добавление текущего пользователя в группу plugdev
echo "--> Добавление пользователя $USER в группу 'plugdev'..."
sudo usermod -aG plugdev $USER

echo ""
echo "=== Шаг 3: Настройка Python-окружения ==="

# 3.1. Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "--> Создание виртуального окружения 'venv'..."
    python3 -m venv venv
else
    echo "--> Виртуальное окружение 'venv' уже существует."
fi

# 3.2. Установка зависимостей из requirements.txt
echo "--> Активация venv и установка зависимостей из requirements.txt..."
source venv/bin/activate
pip install -r requirements.txt
deactivate

echo ""
echo "=============================================================================="
echo "✅ Настройка успешно завершена!"
echo "ВАЖНО: Для применения всех изменений, особенно членства в группе, "
echo "       необходимо перезагрузить Raspberry Pi."
echo "Пожалуйста, выполните команду: sudo reboot"
echo "=============================================================================="