# sync_client.py
import sqlite3
import requests
import json
import logging
from config import SERVER_URL

# Настраиваем базовый логгер
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_NAME = "local_journal.db"
BATCH_SIZE = 20 # Отправлять не более 20 записей за раз

def sync_pours_to_server():
    """
    Выбирает пачку неотправленных транзакций из локальной БД,
    отправляет их на центральный сервер и обрабатывает ответ.
    """
    conn = None # Инициализируем переменную conn
    try:
        conn = sqlite3.connect(DB_NAME, timeout=10)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Выбрать пачку неотправленных записей
        cursor.execute("SELECT * FROM pours WHERE status = 'new' LIMIT ?", (BATCH_SIZE,))
        pours_to_send = cursor.fetchall()

        if not pours_to_send:
            # logging.info("[SYNC] Нет новых записей для отправки.")
            return True # Это не ошибка, просто нет работы

        logging.info(f"[SYNC] Найдено {len(pours_to_send)} новых записей для отправки.")

        # 2. Сформировать JSON для API, преобразуя данные в нужные типы
        pours_list = []
        for row in pours_to_send:
            pours_list.append(dict(row))

        payload = {"pours": pours_list}

        # 3. Отправить на сервер
        sync_url = f"{SERVER_URL}/api/sync/pours/"
        response = requests.post(sync_url, json=payload, timeout=10)
        response.raise_for_status() # Вызовет ошибку для статусов 4xx/5xx

        # 4. Обработать ответ от сервера
        response_data = response.json()
        processed_ids = []
        for result in response_data.get('results', []):
            client_tx_id = result['client_tx_id']
            processed_ids.append(client_tx_id)
            if result['status'] == 'accepted':
                cursor.execute("UPDATE pours SET status = 'confirmed' WHERE client_tx_id = ?", (client_tx_id,))
            else:
                # В будущем можно добавить более сложную логику для 'rejected'
                logging.warning(f"[SYNC] Транзакция {client_tx_id} отклонена сервером. Причина: {result.get('reason')}")
                cursor.execute("UPDATE pours SET status = 'failed' WHERE client_tx_id = ?", (client_tx_id,))

        conn.commit()
        logging.info(f"[SYNC] Успешная синхронизация. Обработано {len(processed_ids)} из {len(pours_to_send)} записей.")
        return True

    except requests.exceptions.RequestException as e:
        logging.error(f"[SYNC ERROR] Ошибка сети при подключении к {SERVER_URL}: {e}")
        return False
    except sqlite3.Error as e:
        logging.error(f"[SYNC ERROR] Ошибка локальной базы данных: {e}")
        return False
    except Exception as e:
        logging.error(f"[SYNC ERROR] Неизвестная ошибка: {e}")
        return False
    finally:
        if conn:
            conn.close()
