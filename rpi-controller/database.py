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
                    short_id TEXT,
                    card_uid TEXT,
                    tap_id INTEGER,
                    start_ts TEXT,
                    end_ts TEXT,
                    volume_ml INTEGER,
                    price_cents INTEGER,
                    status TEXT DEFAULT 'new',
                    attempts INTEGER DEFAULT 0,
                    price_per_ml_at_pour REAL
                );
            """)
            # Backward-compatible additive migration for existing local DBs.
            columns = {row[1] for row in conn.execute("PRAGMA table_info(pours);").fetchall()}
            if "short_id" not in columns:
                conn.execute("ALTER TABLE pours ADD COLUMN short_id TEXT;")
            conn.close()

    def add_pour(self, pour_data):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            conn.execute(
                """
                INSERT INTO pours (client_tx_id, short_id, card_uid, tap_id, start_ts, end_ts, volume_ml, price_cents, status, attempts, price_per_ml_at_pour)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?);
                """,
                (
                    pour_data["client_tx_id"],
                    pour_data["short_id"],
                    pour_data["card_uid"],
                    pour_data["tap_id"],
                    pour_data["start_ts"],
                    pour_data["end_ts"],
                    pour_data["volume_ml"],
                    pour_data["price_cents"],
                    pour_data.get("attempts", 0),
                    pour_data["price_per_ml_at_pour"]
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

    def has_unsynced_for_tap(self, tap_id):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.execute(
                "SELECT 1 FROM pours WHERE tap_id = ? AND status = 'new' LIMIT 1;",
                (tap_id,),
            )
            row = cursor.fetchone()
            conn.close()
            return row is not None

    def update_status(self, client_tx_id, status):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            conn.execute("UPDATE pours SET status = ? WHERE client_tx_id = ?;", (status, client_tx_id))
            conn.commit()
            conn.close()

    def mark_retry(self, client_tx_id):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            conn.execute(
                "UPDATE pours SET attempts = attempts + 1 WHERE client_tx_id = ?;",
                (client_tx_id,),
            )
            conn.commit()
            conn.close()
