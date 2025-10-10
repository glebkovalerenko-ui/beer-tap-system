# main_controller.py (версия 9.0, стабильный прототип)
import sqlite3
import sys
import uuid
import time
from datetime import datetime, timezone
import select

from smartcard.System import readers
from smartcard.util import toHexString
from smartcard.Exceptions import NoCardException, CardConnectionException

import threading
from config import TAP_ID, PRICE_PER_100ML_CENTS, SYNC_INTERVAL_SECONDS
from sync_client import sync_pours_to_server

# --- Конфигурация ---
DB_NAME = "local_journal.db"
#TAP_ID = 1 #--- Переменные для локального теста
#PRICE_PER_100ML_CENTS = 150 #--- Переменные для локального теста

def background_sync_task():
    """
    Функция, которая будет выполняться в фоновом потоке.
    Бесконечно пытается синхронизировать данные с сервером.
    """
    print("[SYNC_THREAD] Фоновый процесс синхронизации запущен.")
    while True:
        try:
            sync_pours_to_server()
        except Exception as e:
            print(f"[SYNC_THREAD] Произошла ошибка в фоновом процессе: {e}")
        
        time.sleep(SYNC_INTERVAL_SECONDS)

def init_db():
    """
    Инициализирует базу данных: создает файл и таблицу, если их нет.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Создаем таблицу, если она не существует
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pours (
            client_tx_id TEXT PRIMARY KEY,
            card_uid TEXT NOT NULL,
            tap_id INTEGER NOT NULL,
            start_ts TEXT NOT NULL,
            end_ts TEXT NOT NULL,
            volume_ml INTEGER NOT NULL,
            price_cents INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'new'
        )
    """)
    conn.commit()
    conn.close()
    print("[DB] База данных проверена/инициализирована.")

# --- Функции-помощники (без изменений) ---
def get_reader():
    try:
        r = readers()
        if not r: return None
        return r[0]
    except Exception as e:
        print(f"[ERROR] Не удалось получить список считывателей: {e}")
        return None

def log_pour_to_db(card_uid, volume_ml, price_cents, start_time, end_time):
    client_tx_id = str(uuid.uuid4())
    pour_data = (client_tx_id, card_uid, TAP_ID, start_time.isoformat(), end_time.isoformat(), volume_ml, price_cents, 'new', 0)
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pours (client_tx_id, card_uid, tap_id, start_ts, end_ts, volume_ml, price_cents, status, attempts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", pour_data)
        conn.commit()
        conn.close()
        print(f"✅ [УСПЕХ] Налив сохранен в БД. TX_ID: {client_tx_id}")
    except sqlite3.Error as e:
        print(f"❌ [ОШИБКА БД] Не удалось сохранить налив: {e}")

# --- Основной цикл с финальной, правильной логикой ---
def main_loop():
    print("=============================================")
    print(f"    Контроллер крана #{TAP_ID} запущен (v9.0)")
    print("=============================================")
    
    reader = get_reader()
    if not reader:
        sys.exit("Критическая ошибка: RFID-считыватель не найден. Выход.")
        
    print(f"Используется считыватель: {reader}")
    print("\n>>> Ожидание RFID-карты... (Для выхода нажмите Ctrl+C)")

    try:
        while True:
            try:
                # 1. Попытка установить соединение. Если карты нет, вызовет NoCardException.
                connection = reader.createConnection()
                connection.connect()

                # --- ЕСЛИ МЫ ЗДЕСЬ, ЗНАЧИТ ОПЕРАЦИЯ НАЧАЛАСЬ ---
                
                # 2. Читаем UID
                GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
                data, sw1, sw2 = connection.transmit(GET_UID)

                if (sw1, sw2) != (0x90, 0x00):
                    print("❌ Не удалось прочитать UID. Уберите и приложите карту заново.")
                    while True: 
                        try: connection.getATR(); time.sleep(0.5)
                        except: break # Ждем, пока уберут проблемную карту
                    continue

                uid = toHexString(data).replace(" ", "")
                print(f"\n💳 Карта приложена. UID: {uid}")

                # 3. Ожидание ввода
                print("    Нажмите Enter, чтобы 'налить' (q для отмены). У вас 10 сек...")
                user_choice = None
                start_wait = time.time()
                while time.time() - start_wait < 10:
                    connection.getATR() # Проверка наличия карты
                    if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                        user_choice = sys.stdin.readline().strip().lower()
                        break
                
                if user_choice is None: print("\n🚫 Время на выбор истекло."); continue
                if user_choice == 'q': print("🚫 Налив отменен пользователем."); continue

                # 4. Эмуляция налива
                print("    ...эмуляция налива, не убирайте карту...")
                start_ts = datetime.now(timezone.utc)
                for _ in range(int(1.5 / 0.1)):
                    connection.getATR(); time.sleep(0.1)

                # 5. Успешное завершение
                end_ts = datetime.now(timezone.utc)
                volume_poured_ml = 250
                price = int(volume_poured_ml / 100 * PRICE_PER_100ML_CENTS)
                print(f"    Налито: {volume_poured_ml} мл. Стоимость: {price / 100:.2f} у.е.")
                log_pour_to_db(uid, volume_poured_ml, price, start_ts, end_ts)
                
                print("...пожалуйста, уберите карту...")
                while True:
                    try: connection.getATR(); time.sleep(0.5)
                    except: break
                print("\n✅ Карта убрана. Система готова.")
                print("\n>>> Ожидание RFID-карты... (Для выхода нажмите Ctrl+C)")

            except NoCardException:
                # ШТАТНЫЙ РЕЖИМ ОЖИДАНИЯ. Ничего не делаем, просто ждем.
                time.sleep(0.5)
                continue

            except CardConnectionException:
                # ОПЕРАЦИЯ БЫЛА ПРЕРВАНА. Сообщаем об этом.
                print("\n🚫 Карта убрана. Операция отменена.")
                print("\n>>> Ожидание RFID-карты... (Для выхода нажмите Ctrl+C)")
                time.sleep(1)
                continue

            except Exception as e:
                print(f"\nПроизошла непредвиденная ошибка: {e}")
                time.sleep(5)

    except KeyboardInterrupt:
        print("\nПолучен сигнал завершения (Ctrl+C). Выход.")
        sys.exit(0)

if __name__ == "__main__":
    init_db() # Убедимся, что БД и таблица существуют

    # Создаем и запускаем фоновый поток для синхронизации.
    # daemon=True означает, что поток автоматически завершится,
    # когда завершится основная программа.
    sync_thread = threading.Thread(target=background_sync_task, daemon=True)
    sync_thread.start()
    
    # Запускаем основной цикл ожидания RFID-карт
    main_loop()
