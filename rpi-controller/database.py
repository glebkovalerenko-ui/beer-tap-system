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
                    client_tx_id TEXT PRIMARY KEY,
                    card_uid TEXT,
                    tap_id INTEGER,
                    start_ts TEXT,
                    end_ts TEXT,
                    volume_ml INTEGER,
                    price_cents INTEGER,
                    status TEXT DEFAULT 'new'
                );
            """)
            conn.close()

    def add_pour(self, pour_data):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            conn.execute(
                """
                INSERT INTO pours (client_tx_id, card_uid, tap_id, start_ts, end_ts, volume_ml, price_cents, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'new');
                """,
                (
                    pour_data["client_tx_id"],
                    pour_data["card_uid"],
                    pour_data["tap_id"],
                    pour_data["start_ts"],
                    pour_data["end_ts"],
                    pour_data["volume_ml"],
                    pour_data["price_cents"]
                )
            )
            conn.commit()
            conn.close()

    def get_unsynced_pours(self, limit):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            conn.row_factory = sqlite3.Row
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