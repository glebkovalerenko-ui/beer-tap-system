import logging
import socket
import time
from urllib.parse import urlsplit

import requests

from config import INTERNAL_TOKEN, SERVER_URL
from log_throttle import LogThrottle


class SyncManager:
    def __init__(self, *, log_throttle=None, time_source=None):
        self.server_url = SERVER_URL.strip().rstrip("/")
        self.session = requests.Session()
        self._time_source = time_source or time.monotonic
        self._log_throttle = log_throttle or LogThrottle(time_source=self._time_source)

    def _resolve_backend_host(self):
        host = urlsplit(self.server_url).hostname or ""
        if not host:
            return "", []

        try:
            resolved = sorted({item[4][0] for item in socket.getaddrinfo(host, None)})
        except socket.gaierror as exc:
            logging.warning("Не удалось разрешить сетевое имя сервера контроллера: узел=%s ошибка=%s", host, exc)
            return host, []

        return host, resolved

    def log_startup_config(self):
        token_state = "задан" if INTERNAL_TOKEN else "отсутствует"
        host, resolved_ips = self._resolve_backend_host()
        resolved_text = ",".join(resolved_ips) if resolved_ips else "<не_определен>"
        logging.info(
            "Конфигурация подключения контроллера: адрес_сервера=%s узел=%s ip_адреса=%s внутренний_токен=%s",
            self.server_url,
            host or "<не_задан>",
            resolved_text,
            token_state,
        )

    def probe_backend(self):
        url = "/".join([self.server_url, "api", "system", "status"])
        headers = {"X-Internal-Token": INTERNAL_TOKEN}
        try:
            response = self.session.get(url, headers=headers, timeout=5)
        except requests.RequestException as exc:
            logging.error("Проверка сервера при запуске не удалась: адрес=%s ошибка=%s", url, exc)
            return False

        if response.status_code == 200:
            logging.info("Проверка сервера при запуске успешна: адрес=%s код_ответа=%s", url, response.status_code)
            return True

        body = (response.text or "").strip()
        logging.error(
            "Проверка сервера при запуске не удалась: адрес=%s код_ответа=%s ответ=%s",
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
            response = self.session.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return str(data.get("value", "")).lower() == "true"
            logging.error("Не удалось проверить статус экстренной остановки: адрес=%s код_ответа=%s", url, response.status_code)
        except requests.RequestException as exc:
            logging.error("Ошибка проверки экстренной остановки: адрес=%s ошибка=%s", url, exc)
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
                "reason": f"authorize_request_failed: {url}: {exc}",
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
        url = "/".join([self.server_url, "api", "controllers", "flow-events"])
        headers = {"X-Internal-Token": INTERNAL_TOKEN}
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
        try:
            response = self.session.post(url, json=payload, headers=headers, timeout=5)
        except requests.RequestException as exc:
            logging.error("Не удалось отправить событие пролива на сервер: адрес=%s ошибка=%s", url, exc)
            return False

        if response.status_code in {200, 202}:
            logging.warning(
                "Событие пролива отправлено на сервер: event_id=%s статус=%s кран=%s объем_мл=%s длительность_мс=%s состояние_сессии=%s",
                event_id,
                event_status,
                tap_id,
                payload["volume_ml"],
                payload["duration_ms"],
                session_state,
            )
            return True

        logging.error(
            "Сервер отклонил событие пролива: адрес=%s код_ответа=%s ответ=%s",
            url,
            response.status_code,
            response.text,
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
            f"Синхронизация налива в очереди: записей={len(pours)}",
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

        try:
            response = self.session.post(url, json=payload, headers=headers, timeout=10)
        except requests.RequestException as exc:
            logging.error("Ошибка синхронизации: адрес=%s ошибка=%s", url, exc)
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
                reason = res.get("reason", "Не указана")

                if result_status == "accepted":
                    db_handler.update_status(client_tx_id, "confirmed")
                    accepted_count += 1
                elif result_status == "audit_only":
                    db_handler.update_status(client_tx_id, "audit_only")
                    audit_only_count += 1
                    logging.warning(
                        "Транзакция %s сохранена только в журнал аудита. результат=%s причина=%s",
                        client_tx_id,
                        outcome,
                        reason,
                    )
                elif result_status in {"rejected", "conflict"}:
                    db_handler.update_status(client_tx_id, "rejected")
                    rejected_count += 1
                    logging.warning(
                        "Транзакция %s отклонена сервером. результат=%s причина=%s",
                        client_tx_id,
                        outcome,
                        reason,
                    )
                else:
                    db_handler.mark_retry(client_tx_id)
                    retry_count += 1
                    logging.warning(
                        "Транзакция %s ещё не завершена. Повторим синхронизацию. результат=%s причина=%s",
                        client_tx_id,
                        outcome,
                        reason,
                    )

            logging.info(
                "Цикл синхронизации завершён: принято=%s audit_only=%s отклонено=%s повторов=%s",
                accepted_count,
                audit_only_count,
                rejected_count,
                retry_count,
            )
            return

        if response.status_code == 409:
            logging.warning("Конфликт синхронизации от сервера (409): адрес=%s ответ=%s", url, response.text)
            return

        logging.error("Синхронизация не удалась: адрес=%s код_ответа=%s ответ=%s", url, response.status_code, response.text)
