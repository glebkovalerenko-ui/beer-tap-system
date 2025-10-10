# database_setup.py (версия 2.0, объединенная)
import sqlite3
import os

DB_NAME = "local_journal.db"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, DB_NAME)

# --- Финальная, согласованная схема БД ---
SQL_SCRIPT = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

/* 
  Таблица для хранения записей о наливах.
  Объединяет лучшие идеи из первоначального файла sqlite_schema.sql
  и предложений ассистента.
*/
CREATE TABLE IF NOT EXISTS pours (
    pour_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client_tx_id    TEXT UNIQUE NOT NULL,
    card_uid        TEXT NOT NULL,
    tap_id          INTEGER NOT NULL,
    start_ts        TEXT NOT NULL,        -- Время начала налива в формате ISO (UTC)
    end_ts          TEXT NOT NULL,        -- Время окончания налива в формате ISO (UTC)
    volume_ml       INTEGER NOT NULL,
    price_cents     INTEGER NOT NULL,
    
    -- Поле статуса с CHECK constraint для целостности данных
    status          TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new', 'sent', 'confirmed', 'failed')),
    
    -- Счетчик попыток отправки - отличная идея из sqlite_schema.sql
    attempts        INTEGER NOT NULL DEFAULT 0
);

/*
  Таблица для логирования важных системных событий.
*/
CREATE TABLE IF NOT EXISTS events (
    event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL, -- Время события в формате ISO (UTC)
    type            TEXT NOT NULL, -- Тип события (e.g., 'SYSTEM_START', 'CONNECTION_LOST')
    payload         TEXT           -- Дополнительная информация в формате JSON
);
"""

def setup_database():
    """Создает и инициализирует локальную базу данных SQLite."""
    print(f"Проверка и настройка базы данных по пути: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.executescript(SQL_SCRIPT)
        conn.commit()
        conn.close()
        print(f"База данных '{DB_NAME}' успешно создана/настроена по объединенной схеме.")
    except sqlite3.Error as e:
        print(f"Ошибка при работе с SQLite: {e}")
        return False
    return True

if __name__ == "__main__":
    # Если файл БД уже существует, этот скрипт безопасно проверит наличие таблиц
    # и не будет ничего перезаписывать благодаря 'CREATE TABLE IF NOT EXISTS'.
    # Для чистого теста можно удалить local_journal.db перед запуском.
    if setup_database():
        print("Настройка завершена успешно.")
    else:
        print("Настройка завершена с ошибками.")
