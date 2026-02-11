import sqlite3
from threading import Lock

class DatabaseHandler:
    def __init__(self, db_name="local_journal.db"):
        self.db_name = db_name
        self.lock = Lock()
        self._initialize_database()

    def _initialize_database(self):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pours (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    client_tx_id TEXT
                );
            """)
            conn.close()

    def add_pour(self, pour_data):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            conn.execute("INSERT INTO pours (data) VALUES (?);", (pour_data,))
            conn.commit()
            conn.close()

    def get_unsynced_pours(self, limit):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.execute("SELECT * FROM pours WHERE status = 'new' LIMIT ?;", (limit,))
            rows = cursor.fetchall()
            conn.close()
            return rows

    def update_status(self, client_tx_id, status):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            conn.execute("UPDATE pours SET status = ? WHERE client_tx_id = ?;", (status, client_tx_id))
            conn.commit()
            conn.close()