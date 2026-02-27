import logging
import time
import uuid

from config import PRICE_PER_100ML_CENTS, TAP_ID


class FlowManager:
    CARD_REMOVE_DEBOUNCE_SECONDS = 0.8

    def __init__(self, hardware, db_handler, sync_manager):
        self.hardware = hardware
        self.db_handler = db_handler
        self.sync_manager = sync_manager
        self.card_must_be_removed = False
        self._card_removed_since = None
        self._last_logs = {}

    def _log_throttled(self, key: str, message: str, level=logging.INFO, interval_seconds: float = 3.0):
        now = time.monotonic()
        last = self._last_logs.get(key, 0.0)
        if now - last < interval_seconds:
            return
        self._last_logs[key] = now
        logging.log(level, message)

    def _enter_card_must_be_removed(self, reason: str):
        self.hardware.valve_close()
        if not self.card_must_be_removed:
            logging.warning("Entering CARD_MUST_BE_REMOVED state: reason=%s", reason)
        self.card_must_be_removed = True
        self._card_removed_since = None

    def _handle_card_must_be_removed(self):
        self.hardware.valve_close()
        if self.hardware.is_card_present():
            self._card_removed_since = None
            self._log_throttled(
                "card_must_be_removed_wait",
                "CARD_MUST_BE_REMOVED: remove card to continue.",
                level=logging.WARNING,
                interval_seconds=2.0,
            )
            return

        now = time.monotonic()
        if self._card_removed_since is None:
            self._card_removed_since = now
            return

        if now - self._card_removed_since < self.CARD_REMOVE_DEBOUNCE_SECONDS:
            return

        self.card_must_be_removed = False
        self._card_removed_since = None
        logging.info("CARD_MUST_BE_REMOVED released: reader clear and debounce passed.")

    def process(self):
        if self.card_must_be_removed:
            self._handle_card_must_be_removed()
            return

        if self.db_handler.has_unsynced_for_tap(TAP_ID):
            self._log_throttled(
                "processing_sync_block",
                "Tap is in processing_sync: unsynced pour exists, blocking new pour start.",
                interval_seconds=3.0,
            )
            if self.hardware.is_card_present():
                self._enter_card_must_be_removed("processing_sync")
            return

        if not self.hardware.is_card_present():
            return

        card_uid = self.hardware.get_card_uid()
        if not card_uid:
            return

        card_uid = card_uid.replace(" ", "").lower()
        auth_result = self.sync_manager.authorize_pour(card_uid=card_uid, tap_id=TAP_ID)
        if not auth_result.get("allowed"):
            reason_code = auth_result.get("reason_code")
            logging.warning(
                "Authorize denied for card %s. status_code=%s reason=%s",
                card_uid,
                auth_result.get("status_code"),
                auth_result.get("reason"),
            )
            if reason_code == "lost_card":
                logging.warning("Карта помечена как потерянная. Налив запрещен, снимите карту с ридера.")
                self._enter_card_must_be_removed("lost_card")
            else:
                self._enter_card_must_be_removed("authorize_rejected")
            return

        logging.info("Authorize OK for card %s on tap %s. Opening valve.", card_uid, TAP_ID)
        self.hardware.valve_open()
        started_monotonic = time.monotonic()
        total_volume_ml = 0
        last_volume_ml = 0
        timeout_counter = 0
        emergency_check_counter = 0
        client_tx_id = str(uuid.uuid4())
        short_id = client_tx_id.replace("-", "")[:8].upper()
        card_removed_by_timeout = False

        try:
            while self.hardware.is_card_present():
                emergency_check_counter += 1

                if emergency_check_counter >= 6:
                    if self.sync_manager.check_emergency_stop():
                        logging.info("Emergency stop is enabled. Closing valve.")
                        break
                    emergency_check_counter = 0

                current_volume_ml = int(self.hardware.get_volume_liters() * 1000)
                if current_volume_ml > last_volume_ml:
                    total_volume_ml = current_volume_ml
                    last_volume_ml = current_volume_ml
                    timeout_counter = 0
                else:
                    timeout_counter += 1

                if timeout_counter >= 30:
                    logging.info("Valve closed by timeout")
                    card_removed_by_timeout = True
                    timeout_price_cents = int((total_volume_ml / 100.0) * PRICE_PER_100ML_CENTS)
                    logging.info(
                        "Timeout details: short_id=%s, volume_ml=%s, cost_cents=%s",
                        short_id,
                        total_volume_ml,
                        timeout_price_cents,
                    )
                    break

                time.sleep(0.5)
        finally:
            self.hardware.valve_close()
            if not card_removed_by_timeout:
                logging.info("Valve closed (card removed)")
            logging.info("Session finished. Poured: %s ml", total_volume_ml)

        if total_volume_ml > 1:
            duration_ms = int((time.monotonic() - started_monotonic) * 1000)
            price_cents = int((total_volume_ml / 100.0) * PRICE_PER_100ML_CENTS)
            pour_data = {
                "client_tx_id": client_tx_id,
                "short_id": short_id,
                "card_uid": card_uid,
                "tap_id": TAP_ID,
                "duration_ms": duration_ms,
                "volume_ml": total_volume_ml,
                "price_cents": price_cents,
                "price_per_ml_at_pour": float(PRICE_PER_100ML_CENTS / 100.0),
            }
            self.db_handler.add_pour(pour_data)
            logging.info("Pour record added to local DB")

        self.hardware.reset_pulses()
        if self.hardware.is_card_present():
            self._enter_card_must_be_removed("session_completed")
