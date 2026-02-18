# config.py
# ==========================================================
# Конфигурация контроллера Beer Tap System
# ==========================================================

import os

# IP-адрес и порт вашего центрального сервера (бэкенда)
# ВАЖНО: Замените "192.168.0.103" на реальный IP вашего компьютера!
SERVER_URL = os.getenv("SERVER_URL", "http://192.168.0.106:8000")

# ID этого крана. Должен быть уникальным для каждого RPi.
# Пока у нас один кран, оставляем значение 1.
TAP_ID = 1

# Цена за 100 мл напитка в условных единицах (копейках, центах).
# В будущем это значение должно приходить с сервера.
PRICE_PER_100ML_CENTS = 150

# Как часто (в секундах) фоновый процесс будет пытаться
# отправить накопленные данные на сервер.
SYNC_INTERVAL_SECONDS = 15

# Пин для управления реле
PIN_RELAY = 18

# Пин для подключения датчика потока
PIN_FLOW_SENSOR = 17

# K-фактор для датчика потока YF-S201
FLOW_SENSOR_K_FACTOR = 7.5



def normalize_token(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {'"', "'"}:
        normalized = normalized[1:-1].strip()
    return normalized

# Токен для внутренней аутентификации
INTERNAL_TOKEN = normalize_token(os.getenv("INTERNAL_TOKEN", "demo-secret-key"))
