import requests
import logging
from config import SERVER_URL, INTERNAL_TOKEN

class SyncManager:
    def __init__(self):
        base = SERVER_URL.strip().rstrip('/')
        self.server_url = base
        self.session = requests.Session()

    def check_emergency_stop(self):
        url = "/".join([self.server_url, "api", "system", "status"])
        headers = {"X-Internal-Token": INTERNAL_TOKEN}
        try:
            response = self.session.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return str(data.get("value", "")).lower() == "true"
            else:
                logging.error(f"Emergency stop check failed with status code {response.status_code}")
        except requests.RequestException as e:
            logging.error(f"Error checking emergency stop: {e}")
        return False

    def sync_cycle(self, db_handler):
        pours = db_handler.get_unsynced_pours(limit=20)
        if not pours:
            return

        logging.info(f"Found {len(pours)} records for synchronization...")
        payload = {"pours": [dict(row) for row in pours]}
        url = "/".join([self.server_url, "api", "sync", "pours"])
        headers = {"X-Internal-Token": INTERNAL_TOKEN}
        try:
            response = self.session.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                results = response.json().get("results", [])
                for res in results:
                    client_tx_id = res.get("client_tx_id")
                    if res.get("status") == "accepted":
                        db_handler.update_status(client_tx_id, "confirmed")
                    else:
                        reason = res.get("reason", "Not specified")
                        db_handler.update_status(client_tx_id, "failed")
                        logging.warning(f"Transaction {client_tx_id} rejected by server. Reason: {reason}")
                logging.info("Синхронизация завершена успешно")
            else:
                logging.error(f"Sync failed with status code {response.status_code}")
        except requests.RequestException as e:
            logging.error(f"Error during sync: {e}")

    def check_card_auth(self, card_uid):
        url = "/".join([self.server_url, "api", "guests"])
        headers = {"X-Internal-Token": INTERNAL_TOKEN}
        try:
            clean_uid = card_uid.replace(" ", "").lower()

            response = self.session.get(url, headers=headers, timeout=5)
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
