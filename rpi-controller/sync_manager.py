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
            return {
                "allowed": False,
                "reason": f"authorize_request_failed: {exc}",
                "reason_code": "request_failed",
                "status_code": None,
            }

        if response.status_code == 200:
            body = response.json()
            if body.get("allowed"):
                return {
                    "allowed": True,
                    "reason": "authorized",
                    "reason_code": "authorized",
                    "status_code": response.status_code,
                    "min_start_ml": int(body.get("min_start_ml") or 0),
                    "max_volume_ml": int(body.get("max_volume_ml") or 0),
                    "price_per_ml_cents": int(body.get("price_per_ml_cents") or 0),
                    "balance_cents": int(body.get("balance_cents") or 0),
                    "allowed_overdraft_cents": int(body.get("allowed_overdraft_cents") or 0),
                    "safety_ml": int(body.get("safety_ml") or 0),
                    "lock_set_at": body.get("lock_set_at"),
                }
            return {
                "allowed": False,
                "reason": body.get("reason", "authorize_denied"),
                "reason_code": body.get("reason", "authorize_denied"),
                "status_code": response.status_code,
            }

        reason_code = "authorize_denied"
        detail = ""
        try:
            detail_payload = response.json().get("detail", "")
            if isinstance(detail_payload, dict):
                reason_code = detail_payload.get("reason", reason_code)
                detail = detail_payload.get("message") or detail_payload.get("detail") or reason_code
                context = detail_payload.get("context") or {}
            elif isinstance(detail_payload, str):
                detail = detail_payload
                context = {}
                if "lost_card" in detail_payload:
                    reason_code = "lost_card"
            else:
                detail = str(detail_payload)
                context = {}
        except ValueError:
            detail = (response.text or "").strip()
            context = {}

        detail = detail or f"http_{response.status_code}"
        return {
            "allowed": False,
            "reason": detail,
            "reason_code": reason_code,
            "status_code": response.status_code,
            "min_start_ml": int(context.get("min_start_ml") or 0),
            "max_volume_ml": int(context.get("max_volume_ml") or 0),
            "price_per_ml_cents": int(context.get("price_per_ml_cents") or 0),
            "balance_cents": int(context.get("balance_cents") or 0),
            "allowed_overdraft_cents": int(context.get("allowed_overdraft_cents") or 0),
            "safety_ml": int(context.get("safety_ml") or 0),
        }

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
            short_id = item.get("short_id") or str(item.get("client_tx_id", "")).replace("-", "")[:8].upper()
            payload_item = {
                "client_tx_id": item.get("client_tx_id"),
                "short_id": short_id,
                "card_uid": item.get("card_uid"),
                "tap_id": item.get("tap_id"),
                "duration_ms": item.get("duration_ms"),
                "volume_ml": item.get("volume_ml"),
                "price_cents": item.get("price_cents"),
            }
            if payload_item["duration_ms"] is None and item.get("start_ts") and item.get("end_ts"):
                payload_item["start_ts"] = item.get("start_ts")
                payload_item["end_ts"] = item.get("end_ts")
            payload_rows.append(payload_item)
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
