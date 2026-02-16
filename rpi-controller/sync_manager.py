import requests
import logging
from config import SERVER_URL, INTERNAL_TOKEN

class SyncManager:
    def __init__(self):
        self.server_url = SERVER_URL
        self.session = requests.Session()
        self.session.headers.update({"X-Internal-Token": INTERNAL_TOKEN})

    def check_emergency_stop(self):
        try:
            response = self.session.get(f"{self.server_url}/api/system/status")
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

        logging.info(f"Found {len(pours)} records for synchronization...")
        payload = {"pours": [dict(row) for row in pours]}
        try:
            response = self.session.post(f"{self.server_url}/api/sync/pours", json=payload)
            if response.status_code == 200:
                results = response.json().get("results", [])
                for res in results:
                    client_tx_id = res.get("client_tx_id")
                    if res.get("status") == "accepted":
                        db_handler.update_status(client_tx_id, "confirmed")
                    else:
                        reason = res.get("reason", "Not specified")
                        db_handler.update_status(client_tx_id, "failed")
                        logging.warning(f"Transaction {client_tx_id} REJECTED by server. Reason: {reason}")
                logging.info("Synchronization completed successfully.")
            else:
                logging.error(f"Sync failed with status code {response.status_code}")
        except requests.RequestException as e:
            logging.error(f"Error during sync: {e}")

    def check_card_auth(self, card_uid):
        try:
            clean_uid = card_uid.replace(" ", "").lower()
            logging.info(f"Comparing clean UID {clean_uid} with database...")

            logging.info(f"DEBUG: Sending token '{INTERNAL_TOKEN}' to URL: {self.server_url}/api/guests")
            response = self.session.get(f"{self.server_url}/api/guests")
            logging.info(f"DEBUG: Статус ответа: {response.status_code}, URL: {response.url}")
            if response.status_code == 200:
                guests = response.json()
                for guest in guests:
                    cards = guest.get("cards", [])
                    if any(card.get("card_uid", "").replace(" ", "").lower() == clean_uid for card in cards):
                        return True
            else:
                logging.error(f"Authorization check failed with status code {response.status_code}")
        except requests.RequestException as e:
            logging.error(f"Error checking card authorization: {e}")
        return False