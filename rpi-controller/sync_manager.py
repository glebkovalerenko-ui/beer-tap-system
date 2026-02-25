import logging
import time

import requests

from config import INTERNAL_TOKEN, SERVER_URL


class SyncManager:
    def __init__(self):
        base = SERVER_URL.strip().rstrip("/")
        self.server_url = base
        self.session = requests.Session()
        self._last_logs = {}

    def _log_throttled(self, key: str, message: str, level=logging.INFO, interval_seconds: float = 3.0):
        now = time.monotonic()
        last = self._last_logs.get(key, 0.0)
        if now - last < interval_seconds:
            return
        self._last_logs[key] = now
        logging.log(level, message)

    def check_emergency_stop(self):
        url = "/".join([self.server_url, "api", "system", "status"])
        headers = {"X-Internal-Token": INTERNAL_TOKEN}
        try:
            response = self.session.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return str(data.get("value", "")).lower() == "true"
            logging.error("Emergency stop check failed with status code %s", response.status_code)
        except requests.RequestException as exc:
            logging.error("Error checking emergency stop: %s", exc)
        return False

    def authorize_pour(self, card_uid, tap_id):
        url = "/".join([self.server_url, "api", "visits", "authorize-pour"])
        headers = {"X-Internal-Token": INTERNAL_TOKEN}
        payload = {"card_uid": card_uid, "tap_id": tap_id}
        try:
            response = self.session.post(url, json=payload, headers=headers, timeout=5)
        except requests.RequestException as exc:
            return {"allowed": False, "reason": f"authorize_request_failed: {exc}", "status_code": None}

        if response.status_code == 200:
            body = response.json()
            if body.get("allowed"):
                return {"allowed": True, "reason": "authorized", "status_code": response.status_code}
            return {"allowed": False, "reason": body.get("reason", "authorize_denied"), "status_code": response.status_code}

        detail = ""
        try:
            detail_payload = response.json().get("detail", "")
            detail = detail_payload if isinstance(detail_payload, str) else str(detail_payload)
        except ValueError:
            detail = (response.text or "").strip()

        detail = detail or f"http_{response.status_code}"
        return {"allowed": False, "reason": detail, "status_code": response.status_code}

    def sync_cycle(self, db_handler):
        pours = db_handler.get_unsynced_pours(limit=20)
        if not pours:
            return

        self._log_throttled(
            "sync_processing",
            f"processing_sync: pending_records={len(pours)}",
            interval_seconds=3.0,
        )
        payload_rows = []
        for row in pours:
            item = dict(row)
            if not item.get("short_id"):
                item["short_id"] = str(item.get("client_tx_id", "")).replace("-", "")[:8].upper()
            payload_rows.append(item)
        payload = {"pours": payload_rows}
        url = "/".join([self.server_url, "api", "sync", "pours"])
        headers = {"X-Internal-Token": INTERNAL_TOKEN}

        try:
            response = self.session.post(url, json=payload, headers=headers, timeout=10)
        except requests.RequestException as exc:
            logging.error("Error during sync: %s", exc)
            return

        if response.status_code == 200:
            results = response.json().get("results", [])
            accepted_count = 0
            audit_only_count = 0
            rejected_count = 0
            retry_count = 0
            for res in results:
                client_tx_id = res.get("client_tx_id")
                result_status = res.get("status")
                outcome = res.get("outcome", "unknown")
                reason = res.get("reason", "Not specified")

                if result_status == "accepted":
                    db_handler.update_status(client_tx_id, "confirmed")
                    accepted_count += 1
                elif result_status == "audit_only":
                    db_handler.update_status(client_tx_id, "audit_only")
                    audit_only_count += 1
                    logging.warning(
                        "Transaction %s stored as audit-only. outcome=%s reason=%s",
                        client_tx_id,
                        outcome,
                        reason,
                    )
                elif result_status in {"rejected", "conflict"}:
                    db_handler.update_status(client_tx_id, "rejected")
                    rejected_count += 1
                    logging.warning(
                        "Transaction %s rejected by backend. outcome=%s reason=%s",
                        client_tx_id,
                        outcome,
                        reason,
                    )
                else:
                    db_handler.mark_retry(client_tx_id)
                    retry_count += 1
                    logging.warning(
                        "Transaction %s not terminal yet. Will retry. outcome=%s reason=%s",
                        client_tx_id,
                        outcome,
                        reason,
                    )

            logging.info(
                "sync cycle completed: accepted=%s audit_only=%s rejected=%s retried=%s",
                accepted_count,
                audit_only_count,
                rejected_count,
                retry_count,
            )
            return

        if response.status_code == 409:
            logging.warning("Sync conflict from backend (409): %s", response.text)
            return

        logging.error("Sync failed with status code %s", response.status_code)
