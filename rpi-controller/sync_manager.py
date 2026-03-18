import logging
import queue
import socket
import threading
import time
from urllib.parse import urlsplit

import requests

from config import INTERNAL_TOKEN, SERVER_URL
from log_throttle import LogThrottle


class SyncManager:
    PROBE_TIMEOUT_SECONDS = 5
    EMERGENCY_STATUS_TIMEOUT_SECONDS = 1
    AUTHORIZE_TIMEOUT_SECONDS = 5
    AUTHORIZE_RETRY_ATTEMPTS = 2
    AUTHORIZE_RETRY_BACKOFF_SECONDS = 0.2
    FLOW_EVENT_TIMEOUT_SECONDS = 5
    SYNC_TIMEOUT_SECONDS = 10
    FLOW_EVENT_WORKER_POLL_SECONDS = 0.5

    def __init__(self, *, log_throttle=None, time_source=None, sleep_fn=None):
        self.server_url = SERVER_URL.strip().rstrip("/")
        self.session = self._new_session()
        self.authorize_session = self._new_session() or self.session
        self.sync_session = self._new_session() or self.session
        self.flow_event_session = self._new_session() or self.session
        self._time_source = time_source or time.monotonic
        self._sleep = sleep_fn or time.sleep
        self._log_throttle = log_throttle or LogThrottle(time_source=self._time_source)
        self._flow_event_queue = queue.Queue()
        self._flow_event_worker = None
        self._sync_wake_event = threading.Event()

    @staticmethod
    def _new_session():
        factory = getattr(requests, "Session", None)
        if not callable(factory):
            return None
        return factory()

    @staticmethod
    def _close_session(session):
        close = getattr(session, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                logging.debug("Ignoring session close failure", exc_info=True)

    def _replace_authorize_session(self):
        self._close_session(self.authorize_session)
        self.authorize_session = self._new_session() or self.session
        return self.authorize_session

    def start_flow_event_worker(self):
        worker = self._flow_event_worker
        if worker is not None and worker.is_alive():
            return worker

        worker = threading.Thread(
            target=self._flow_event_worker_loop,
            name="beer-tap-flow-events",
            daemon=True,
        )
        worker.start()
        self._flow_event_worker = worker
        return worker

    def _flow_event_worker_loop(self):
        while True:
            self.process_flow_event_queue_once(
                block=True,
                timeout=self.FLOW_EVENT_WORKER_POLL_SECONDS,
            )

    def notify_sync_needed(self):
        self._sync_wake_event.set()

    def wait_for_next_sync_cycle(self, interval_seconds):
        self._sync_wake_event.wait(timeout=max(float(interval_seconds or 0), 0.0))
        self._sync_wake_event.clear()

    def _resolve_backend_host(self):
        host = urlsplit(self.server_url).hostname or ""
        if not host:
            return "", []

        try:
            resolved = sorted({item[4][0] for item in socket.getaddrinfo(host, None)})
        except socket.gaierror as exc:
            logging.warning("Failed to resolve backend host: host=%s error=%s", host, exc)
            return host, []

        return host, resolved

    def log_startup_config(self):
        token_state = "set" if INTERNAL_TOKEN else "missing"
        host, resolved_ips = self._resolve_backend_host()
        resolved_text = ",".join(resolved_ips) if resolved_ips else "<unresolved>"
        logging.info(
            "Controller backend config: server_url=%s host=%s resolved_ips=%s internal_token=%s",
            self.server_url,
            host or "<unset>",
            resolved_text,
            token_state,
        )

    def probe_backend(self):
        url = "/".join([self.server_url, "api", "system", "status"])
        headers = {"X-Internal-Token": INTERNAL_TOKEN}
        try:
            response = self.session.get(url, headers=headers, timeout=self.PROBE_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            logging.error("Backend startup probe failed: url=%s error=%s", url, exc)
            return False

        if response.status_code == 200:
            logging.info("Backend startup probe succeeded: url=%s status_code=%s", url, response.status_code)
            return True

        body = (getattr(response, "text", "") or "").strip()
        logging.error(
            "Backend startup probe failed: url=%s status_code=%s response=%s",
            url,
            response.status_code,
            body,
        )
        return False

    def _log_throttled(self, key: str, message: str, *, level=logging.INFO, interval_seconds: float = 3.0, state=None):
        return self._log_throttle.log(
            key,
            message,
            level=level,
            interval_seconds=interval_seconds,
            state=state,
        )

    def check_emergency_stop(self):
        url = "/".join([self.server_url, "api", "system", "status"])
        headers = {"X-Internal-Token": INTERNAL_TOKEN}
        try:
            response = self.session.get(url, headers=headers, timeout=self.EMERGENCY_STATUS_TIMEOUT_SECONDS)
            if response.status_code == 200:
                data = response.json()
                return str(data.get("value", "")).lower() == "true"
            logging.error("Emergency stop status request failed: url=%s status_code=%s", url, response.status_code)
        except requests.RequestException as exc:
            logging.error("Emergency stop status request failed: url=%s error=%s", url, exc)
        return False

    def authorize_pour(self, card_uid, tap_id):
        url = "/".join([self.server_url, "api", "visits", "authorize-pour"])
        headers = {"X-Internal-Token": INTERNAL_TOKEN}
        payload = {"card_uid": card_uid, "tap_id": tap_id}
        response = None
        last_error = None
        for attempt in range(1, self.AUTHORIZE_RETRY_ATTEMPTS + 1):
            session = self.authorize_session or self.session
            if session is None or not hasattr(session, "post"):
                return {
                    "allowed": False,
                    "reason": f"authorize_request_failed: {url}: no_http_session",
                    "reason_code": "request_failed",
                    "status_code": None,
                }

            try:
                response = session.post(url, json=payload, headers=headers, timeout=self.AUTHORIZE_TIMEOUT_SECONDS)
                break
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.AUTHORIZE_RETRY_ATTEMPTS:
                    return {
                        "allowed": False,
                        "reason": f"authorize_request_failed: {url}: {exc}",
                        "reason_code": "request_failed",
                        "status_code": None,
                    }

                logging.warning(
                    "Authorize request failed: url=%s attempt=%s/%s error=%s; retrying",
                    url,
                    attempt,
                    self.AUTHORIZE_RETRY_ATTEMPTS,
                    exc,
                )
                self._replace_authorize_session()
                self._sleep(self.AUTHORIZE_RETRY_BACKOFF_SECONDS)

        if response is None:
            return {
                "allowed": False,
                "reason": f"authorize_request_failed: {url}: {last_error or 'unknown_error'}",
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
                    "guest_first_name": body.get("guest_first_name"),
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
            detail = (getattr(response, "text", "") or "").strip()
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

    def report_flow_event(
        self,
        *,
        event_id,
        event_status,
        tap_id,
        volume_ml,
        duration_ms,
        card_present,
        session_state,
        reason,
        valve_open=False,
        card_uid=None,
        short_id=None,
    ):
        payload = {
            "event_id": event_id,
            "event_status": event_status,
            "tap_id": tap_id,
            "volume_ml": int(volume_ml or 0),
            "duration_ms": int(duration_ms or 0),
            "card_present": bool(card_present),
            "valve_open": bool(valve_open),
            "session_state": session_state,
            "card_uid": card_uid,
            "short_id": short_id,
            "reason": reason,
        }
        self._flow_event_queue.put_nowait(payload)
        return True

    def process_flow_event_queue_once(self, *, block=False, timeout=0.0, session=None):
        try:
            if block:
                payload = self._flow_event_queue.get(timeout=timeout)
            else:
                payload = self._flow_event_queue.get_nowait()
        except queue.Empty:
            return None

        try:
            return self._send_flow_event_payload(payload, session=session)
        finally:
            self._flow_event_queue.task_done()

    def _send_flow_event_payload(self, payload, *, session=None):
        url = "/".join([self.server_url, "api", "controllers", "flow-events"])
        headers = {"X-Internal-Token": INTERNAL_TOKEN}
        session = session or self.flow_event_session or self.session
        if session is None or not hasattr(session, "post"):
            logging.error("Flow event delivery failed: url=%s error=no_http_session", url)
            return False

        try:
            response = session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.FLOW_EVENT_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            logging.error("Flow event delivery failed: url=%s error=%s", url, exc)
            return False

        if response.status_code in {200, 202}:
            logging.warning(
                "Flow event delivered: event_id=%s status=%s tap_id=%s volume_ml=%s duration_ms=%s session_state=%s",
                payload["event_id"],
                payload["event_status"],
                payload["tap_id"],
                payload["volume_ml"],
                payload["duration_ms"],
                payload["session_state"],
            )
            return True

        logging.error(
            "Flow event rejected: url=%s status_code=%s response=%s",
            url,
            response.status_code,
            getattr(response, "text", ""),
        )
        return False

    def report_flow_anomaly(self, *, tap_id, volume_ml, duration_ms, card_present, session_state, reason):
        event_id = f"closed-valve:{tap_id}:{int(time.time() * 1000)}"
        return self.report_flow_event(
            event_id=event_id,
            event_status="started",
            tap_id=tap_id,
            volume_ml=volume_ml,
            duration_ms=duration_ms,
            card_present=card_present,
            session_state=session_state,
            reason=reason,
            valve_open=False,
        )

    def sync_cycle(self, db_handler):
        pours = db_handler.get_unsynced_pours(limit=20)
        if not pours:
            self._log_throttle.reset("sync_processing")
            return

        self._log_throttled(
            "sync_processing",
            f"Pending pour sync records={len(pours)}",
            interval_seconds=10.0,
            state=len(pours),
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
                "tail_volume_ml": int(item.get("tail_volume_ml") or 0),
                "price_cents": item.get("price_cents"),
            }
            if payload_item["duration_ms"] is None and item.get("start_ts") and item.get("end_ts"):
                payload_item["start_ts"] = item.get("start_ts")
                payload_item["end_ts"] = item.get("end_ts")
            payload_rows.append(payload_item)
        payload = {"pours": payload_rows}
        url = "/".join([self.server_url, "api", "sync", "pours"])
        headers = {"X-Internal-Token": INTERNAL_TOKEN}
        session = self.sync_session or self.session

        try:
            response = session.post(url, json=payload, headers=headers, timeout=self.SYNC_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            logging.error("Pour sync failed: url=%s error=%s", url, exc)
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
                reason = res.get("reason", "not_specified")

                if result_status == "accepted":
                    db_handler.update_status(client_tx_id, "confirmed")
                    accepted_count += 1
                elif result_status == "audit_only":
                    db_handler.update_status(client_tx_id, "audit_only")
                    audit_only_count += 1
                    logging.warning(
                        "Pour sync stored as audit_only: client_tx_id=%s outcome=%s reason=%s",
                        client_tx_id,
                        outcome,
                        reason,
                    )
                elif result_status in {"rejected", "conflict"}:
                    db_handler.update_status(client_tx_id, "rejected")
                    rejected_count += 1
                    logging.warning(
                        "Pour sync rejected: client_tx_id=%s outcome=%s reason=%s",
                        client_tx_id,
                        outcome,
                        reason,
                    )
                else:
                    db_handler.mark_retry(client_tx_id)
                    retry_count += 1
                    logging.warning(
                        "Pour sync will retry: client_tx_id=%s outcome=%s reason=%s",
                        client_tx_id,
                        outcome,
                        reason,
                    )

            logging.info(
                "Pour sync cycle completed: accepted=%s audit_only=%s rejected=%s retries=%s",
                accepted_count,
                audit_only_count,
                rejected_count,
                retry_count,
            )
            return

        if response.status_code == 409:
            logging.warning("Pour sync conflict: url=%s response=%s", url, getattr(response, "text", ""))
            return

        logging.error(
            "Pour sync failed: url=%s status_code=%s response=%s",
            url,
            response.status_code,
            getattr(response, "text", ""),
        )
