import logging
import time
import uuid

from config import PRICE_PER_100ML_CENTS, TAP_ID
from log_throttle import LogThrottle
from pour_session import calculate_price_cents, has_reached_pour_limit
from terminal_progress import TerminalProgressDisplay


class FlowManager:
    CARD_REMOVE_DEBOUNCE_SECONDS = 0.8
    CARD_REMOVE_REMINDER_SECONDS = 10.0
    PROCESSING_SYNC_REMINDER_SECONDS = 10.0
    LOOP_INTERVAL_SECONDS = 0.1
    EMERGENCY_CHECK_INTERVAL_SECONDS = 3.0
    FLOW_TIMEOUT_SECONDS = 15.0

    def __init__(
        self,
        hardware,
        db_handler,
        sync_manager,
        *,
        log_throttle=None,
        progress_factory=None,
        time_source=None,
        sleep_fn=None,
    ):
        self.hardware = hardware
        self.db_handler = db_handler
        self.sync_manager = sync_manager
        self.card_must_be_removed = False
        self._card_removed_since = None
        self._card_must_be_removed_reason = None
        self._time_source = time_source or time.monotonic
        self._sleep = sleep_fn or time.sleep
        self._log_throttle = log_throttle or LogThrottle(time_source=self._time_source)
        self._progress_factory = progress_factory or (lambda: TerminalProgressDisplay(time_source=self._time_source))

    @staticmethod
    def _legacy_price_cents(volume_ml):
        return int((max(int(volume_ml), 0) / 100.0) * PRICE_PER_100ML_CENTS)

    def _log_throttled(
        self,
        key: str,
        message: str,
        *,
        level=logging.INFO,
        interval_seconds: float = 3.0,
        state=None,
    ):
        return self._log_throttle.log(
            key,
            message,
            level=level,
            interval_seconds=interval_seconds,
            state=state,
        )

    def _enter_card_must_be_removed(self, reason: str):
        self.hardware.valve_close()
        if not self.card_must_be_removed or self._card_must_be_removed_reason != reason:
            logging.warning("Entering CARD_MUST_BE_REMOVED state: reason=%s", reason)
        self.card_must_be_removed = True
        self._card_removed_since = None
        self._card_must_be_removed_reason = reason

    def _handle_card_must_be_removed(self):
        self.hardware.valve_close()
        if self.hardware.is_card_present():
            self._card_removed_since = None
            self._log_throttled(
                "card_must_be_removed_wait",
                "CARD_MUST_BE_REMOVED: remove card to continue. reason=%s" % self._card_must_be_removed_reason,
                level=logging.WARNING,
                interval_seconds=self.CARD_REMOVE_REMINDER_SECONDS,
                state=self._card_must_be_removed_reason,
            )
            return

        now = self._time_source()
        if self._card_removed_since is None:
            self._card_removed_since = now
            return

        if now - self._card_removed_since < self.CARD_REMOVE_DEBOUNCE_SECONDS:
            return

        self.card_must_be_removed = False
        self._card_removed_since = None
        released_reason = self._card_must_be_removed_reason
        self._card_must_be_removed_reason = None
        self._log_throttle.reset("card_must_be_removed_wait")
        logging.info(
            "CARD_MUST_BE_REMOVED released: reader clear and debounce passed. previous_reason=%s",
            released_reason,
        )

    def process(self):
        if self.card_must_be_removed:
            self._handle_card_must_be_removed()
            return

        if self.db_handler.has_unsynced_for_tap(TAP_ID):
            self._log_throttled(
                "processing_sync_block",
                "Tap is in processing_sync: unsynced pour exists, blocking new pour start.",
                interval_seconds=self.PROCESSING_SYNC_REMINDER_SECONDS,
                state="blocked",
            )
            if self.hardware.is_card_present():
                self._enter_card_must_be_removed("processing_sync")
            return
        self._log_throttle.reset("processing_sync_block")

        if not self.hardware.is_card_present():
            return

        card_uid = self.hardware.get_card_uid()
        if not card_uid:
            return

        card_uid = card_uid.replace(" ", "").lower()
        auth_result = self.sync_manager.authorize_pour(card_uid=card_uid, tap_id=TAP_ID)
        if not auth_result.get("allowed"):
            reason_code = auth_result.get("reason_code") or "authorize_denied"
            self._log_throttled(
                f"authorize_denied:{reason_code}",
                "Authorize denied for card %s. status_code=%s reason=%s"
                % (card_uid, auth_result.get("status_code"), auth_result.get("reason")),
                level=logging.WARNING,
                interval_seconds=2.0,
                state=reason_code,
            )
            if reason_code == "lost_card":
                self._log_throttled(
                    "authorize_denied_lost_card",
                    "Card is marked as lost. Pour denied. Remove the card from the reader.",
                    level=logging.WARNING,
                    interval_seconds=2.0,
                    state=reason_code,
                )
                self._enter_card_must_be_removed("lost_card")
            elif reason_code == "insufficient_funds":
                self._log_throttled(
                    "authorize_denied_insufficient_funds",
                    "Insufficient funds to start pour. Top up balance and remove the card from the reader.",
                    level=logging.WARNING,
                    interval_seconds=2.0,
                    state=reason_code,
                )
                self._enter_card_must_be_removed("insufficient_funds")
            else:
                self._enter_card_must_be_removed("authorize_rejected")
            return

        self._log_throttle.reset("authorize_denied:authorize_denied")
        self._log_throttle.reset("authorize_denied:lost_card")
        self._log_throttle.reset("authorize_denied:insufficient_funds")
        self._log_throttle.reset("authorize_denied_lost_card")
        self._log_throttle.reset("authorize_denied_insufficient_funds")

        max_volume_ml = int(auth_result.get("max_volume_ml") or 0)
        price_per_ml_cents = int(auth_result.get("price_per_ml_cents") or 0)
        has_authorized_price = price_per_ml_cents > 0
        if max_volume_ml <= 0:
            self._log_throttled(
                "authorize_invalid_contract",
                "Authorize returned invalid clamp data. max_volume_ml=%s price_per_ml_cents=%s"
                % (max_volume_ml, price_per_ml_cents),
                level=logging.ERROR,
                interval_seconds=2.0,
            )
            self._enter_card_must_be_removed("authorize_invalid_contract")
            return

        logging.info(
            "Authorize OK for card %s on tap %s. Opening valve with max_volume_ml=%s.",
            card_uid,
            TAP_ID,
            max_volume_ml,
        )
        self.hardware.valve_open()
        started_monotonic = self._time_source()
        total_volume_liters = 0.0
        total_volume_ml = 0
        last_flow_at = started_monotonic
        next_emergency_check_at = started_monotonic + self.EMERGENCY_CHECK_INTERVAL_SECONDS
        client_tx_id = str(uuid.uuid4())
        short_id = client_tx_id.replace("-", "")[:8].upper()
        card_removed_by_timeout = False
        progress_display = self._progress_factory()

        try:
            while self.hardware.is_card_present():
                now = self._time_source()
                if now >= next_emergency_check_at:
                    if self.sync_manager.check_emergency_stop():
                        logging.info("Emergency stop is enabled. Closing valve.")
                        break
                    next_emergency_check_at = now + self.EMERGENCY_CHECK_INTERVAL_SECONDS

                volume_delta_liters = self.hardware.get_volume_liters()
                if volume_delta_liters > 0:
                    total_volume_liters += volume_delta_liters
                    total_volume_ml = int(total_volume_liters * 1000)
                    if has_reached_pour_limit(total_volume_ml, max_volume_ml):
                        total_volume_ml = max_volume_ml
                        logging.info("Valve closed by authorized volume clamp at %s ml", max_volume_ml)
                        break
                    last_flow_at = now

                progress_display.update(
                    total_volume_ml,
                    max_volume_ml=max_volume_ml,
                    estimated_cost_cents=(
                        calculate_price_cents(total_volume_ml, price_per_ml_cents)
                        if has_authorized_price
                        else self._legacy_price_cents(total_volume_ml)
                    ),
                )

                if now - last_flow_at >= self.FLOW_TIMEOUT_SECONDS:
                    logging.info("Valve closed by timeout")
                    card_removed_by_timeout = True
                    timeout_price_cents = (
                        calculate_price_cents(total_volume_ml, price_per_ml_cents)
                        if has_authorized_price
                        else self._legacy_price_cents(total_volume_ml)
                    )
                    logging.info(
                        "Timeout details: short_id=%s, volume_ml=%s, cost_cents=%s",
                        short_id,
                        total_volume_ml,
                        timeout_price_cents,
                    )
                    break

                self._sleep(self.LOOP_INTERVAL_SECONDS)
        finally:
            self.hardware.valve_close()
            if not card_removed_by_timeout:
                logging.info("Valve closed (card removed)")
            progress_display.finish(total_volume_ml)

        if total_volume_ml > 1:
            duration_ms = int((self._time_source() - started_monotonic) * 1000)
            price_cents = (
                calculate_price_cents(total_volume_ml, price_per_ml_cents)
                if has_authorized_price
                else self._legacy_price_cents(total_volume_ml)
            )
            pour_data = {
                "client_tx_id": client_tx_id,
                "short_id": short_id,
                "card_uid": card_uid,
                "tap_id": TAP_ID,
                "duration_ms": duration_ms,
                "volume_ml": total_volume_ml,
                "price_cents": price_cents,
                "price_per_ml_at_pour": float(
                    price_per_ml_cents if has_authorized_price else (PRICE_PER_100ML_CENTS / 100.0)
                ),
            }
            self.db_handler.add_pour(pour_data)
            logging.info("Pour record added to local DB")

        self.hardware.reset_pulses()
        if self.hardware.is_card_present():
            self._enter_card_must_be_removed("session_completed")
