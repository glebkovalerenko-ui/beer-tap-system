import requests
import logging
from config import SERVER_URL

class SyncManager:
    def __init__(self):
        self.server_url = SERVER_URL

    def check_emergency_stop(self):
        try:
            response = requests.get(f"{self.server_url}/api/system/status")
            if response.status_code == 200:
                data = response.json()
                return str(data.get("value", "")).lower() == "true"
        except requests.RequestException as e:
            logging.error(f"Error checking emergency stop: {e}")
        return False

    def sync_cycle(self, db_handler):
        pours = db_handler.get_unsynced_pours(limit=20)
        if not pours:
            return

        payload = {"pours": [dict(row) for row in pours]}
        try:
            response = requests.post(f"{self.server_url}/api/sync/pours/", json=payload)
            if response.status_code == 200:
                results = response.json().get("results", [])
                for res in results:
                    if res.get("status") == "accepted":
                        db_handler.update_status(res["client_tx_id"], "confirmed")
            else:
                logging.error(f"Sync failed with status code {response.status_code}")
        except requests.RequestException as e:
            logging.error(f"Error during sync: {e}")