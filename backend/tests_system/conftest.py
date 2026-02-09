# backend/tests_system/conftest.py
import pytest
import subprocess
import time
import os

@pytest.fixture(scope="module")
def system_environment():
    """
    Эта фикстура управляет полным циклом docker-compose.
    scope="module" означает, что она запустится ОДИН раз для всех тестов
    в одном файле, что экономит массу времени.
    """
    print("\n--- [System Test Setup] ---")
    
    # 1. Гарантированная очистка перед запуском
    print("Остановка и удаление старых контейнеров и volumes...")
    subprocess.run(["docker-compose", "down", "-v"], check=True, capture_output=True)
    
    # 2. Запуск системы в фоновом режиме
    print("Запуск 'docker-compose up -d'...")
    subprocess.run(["docker-compose", "up", "-d"], check=True, capture_output=True)
    
    # 3. Ожидание, пока база данных станет 'healthy'
    # В реальном проекте здесь будет более умный цикл, который опрашивает 'docker ps'.
    # Для начала, простое ожидание достаточно.
    print("Ожидание готовности PostgreSQL (30 секунд)...")
    time.sleep(30)
    
    # 4. Передаем управление тестам
    yield
    
    # 5. Очистка после выполнения всех тестов в модуле
    print("\n--- [System Test Teardown] ---")
    print("Остановка и удаление контейнеров...")
    subprocess.run(["docker-compose", "down", "-v"], check=True, capture_output=True)
    print("Очистка завершена.")