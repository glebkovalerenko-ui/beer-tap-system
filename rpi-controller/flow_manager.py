import logging
import time
import uuid

from config import PRICE_PER_100ML_CENTS, TAP_ID
from display_formatters import format_money_minor_units, format_volume
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
    FLOW_TAIL_IDLE_SECONDS = 0.5
    FLOW_TAIL_MAX_SECONDS = 3.0
    CLOSED_VALVE_FLOW_REPORT_MIN_VOLUME_ML = 5
    CLOSED_VALVE_FLOW_RESET_SECONDS = 1.0
    FLOW_EVENT_PROGRESS_INTERVAL_SECONDS = 1.0

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
        runtime_publisher=None,
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
        self._runtime_publisher = runtime_publisher
        self._unexpected_flow_started_at = None
        self._unexpected_flow_last_seen_at = None
        self._unexpected_flow_volume_liters = 0.0
        self._unexpected_flow_reported = False
        self._unexpected_flow_event_id = None
        self._unexpected_flow_last_report_at = None
        self._last_session_summary = None

    @staticmethod
    def _legacy_price_cents(volume_ml):
        return int((max(int(volume_ml), 0) / 100.0) * PRICE_PER_100ML_CENTS)

    @staticmethod
    def _liters_to_ml(volume_liters: float) -> int:
        return int(max(float(volume_liters or 0.0), 0.0) * 1000)

    @staticmethod
    def _projected_remaining_balance(balance_cents_at_authorize, current_cost_cents):
        if balance_cents_at_authorize is None:
            return None
        return int(balance_cents_at_authorize) - int(current_cost_cents or 0)

    def _publish_runtime(self, **payload):
        if self._runtime_publisher is None:
            return None
        return self._runtime_publisher.publish(**payload)

    def _publish_card_removal_state(self, *, card_present: bool):
        reason = self._card_must_be_removed_reason or "card_must_be_removed"
        if reason == "session_completed" and self._last_session_summary:
            summary = dict(self._last_session_summary)
            summary["card_present"] = card_present
            self._publish_runtime(**summary)
            return

        denied_reasons = {
            "lost_card",
            "insufficient_funds",
            "no_active_visit",
            "card_in_use_on_other_tap",
            "authorize_rejected",
            "backend_unreachable",
        }
        phase = "denied" if reason in denied_reasons else "blocked"
        self._publish_runtime(
            phase=phase,
            reason_code=reason,
            card_present=card_present,
        )

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

    def _reset_unexpected_flow_state(self):
        self._unexpected_flow_started_at = None
        self._unexpected_flow_last_seen_at = None
        self._unexpected_flow_volume_liters = 0.0
        self._unexpected_flow_reported = False
        self._unexpected_flow_event_id = None
        self._unexpected_flow_last_report_at = None
        self._log_throttle.reset("unexpected_closed_valve_flow")

    def _new_flow_event_id(self, prefix: str) -> str:
        return f"{prefix}:{TAP_ID}:{int(self._time_source() * 1000)}"

    def _report_flow_event(
        self,
        *,
        event_id: str,
        event_status: str,
        tap_id: int,
        volume_ml: int,
        duration_ms: int,
        card_present: bool,
        session_state: str,
        reason: str,
        valve_open: bool,
        card_uid: str | None = None,
        short_id: str | None = None,
    ):
        self.sync_manager.report_flow_event(
            event_id=event_id,
            event_status=event_status,
            tap_id=tap_id,
            volume_ml=volume_ml,
            duration_ms=duration_ms,
            card_present=card_present,
            session_state=session_state,
            reason=reason,
            valve_open=valve_open,
            card_uid=card_uid,
            short_id=short_id,
        )

    def _maybe_report_authorized_flow_event(
        self,
        *,
        client_tx_id: str,
        short_id: str,
        card_uid: str,
        total_volume_ml: int,
        duration_ms: int,
        card_present: bool,
        reported: bool,
        last_report_at,
    ):
        if total_volume_ml < self.CLOSED_VALVE_FLOW_REPORT_MIN_VOLUME_ML:
            return reported, last_report_at

        now = self._time_source()
        if not reported:
            self._report_flow_event(
                event_id=client_tx_id,
                event_status="started",
                tap_id=TAP_ID,
                volume_ml=total_volume_ml,
                duration_ms=duration_ms,
                card_present=card_present,
                session_state="authorized_session",
                reason="authorized_pour_in_progress",
                valve_open=True,
                card_uid=card_uid,
                short_id=short_id,
            )
            return True, now

        if last_report_at is not None and now - last_report_at < self.FLOW_EVENT_PROGRESS_INTERVAL_SECONDS:
            return reported, last_report_at

        self._report_flow_event(
            event_id=client_tx_id,
            event_status="updated",
            tap_id=TAP_ID,
            volume_ml=total_volume_ml,
            duration_ms=duration_ms,
            card_present=card_present,
            session_state="authorized_session",
            reason="authorized_pour_in_progress",
            valve_open=True,
            card_uid=card_uid,
            short_id=short_id,
        )
        return True, now

    def _stop_authorized_flow_event(
        self,
        *,
        client_tx_id: str,
        short_id: str,
        card_uid: str,
        total_volume_ml: int,
        duration_ms: int,
        card_present: bool,
    ):
        if total_volume_ml < self.CLOSED_VALVE_FLOW_REPORT_MIN_VOLUME_ML:
            return

        self._report_flow_event(
            event_id=client_tx_id,
            event_status="stopped",
            tap_id=TAP_ID,
            volume_ml=total_volume_ml,
            duration_ms=duration_ms,
            card_present=card_present,
            session_state="authorized_session",
            reason="authorized_pour_in_progress",
            valve_open=False,
            card_uid=card_uid,
            short_id=short_id,
        )

    def _observe_closed_valve_flow(self, *, card_present: bool, session_state: str):
        volume_delta_liters = self.hardware.get_volume_liters()
        if volume_delta_liters > 0:
            now = self._time_source()
            if self._unexpected_flow_started_at is None:
                self._unexpected_flow_started_at = now
                self._unexpected_flow_volume_liters = 0.0
                self._unexpected_flow_reported = False
                self._unexpected_flow_event_id = self._new_flow_event_id("closed-valve")
                self._unexpected_flow_last_report_at = None

            self._unexpected_flow_last_seen_at = now
            self._unexpected_flow_volume_liters += volume_delta_liters
            total_volume_ml = self._liters_to_ml(self._unexpected_flow_volume_liters)
            self._log_throttled(
                "unexpected_closed_valve_flow",
                "Обнаружен пролив при закрытом клапане вне активной сессии. объем=%s карта_вставлена=%s состояние_сессии=%s"
                % (format_volume(total_volume_ml), card_present, session_state),
                level=logging.WARNING,
                interval_seconds=2.0,
                state=(session_state, card_present),
            )
            if (
                not self._unexpected_flow_reported
                and total_volume_ml >= self.CLOSED_VALVE_FLOW_REPORT_MIN_VOLUME_ML
            ):
                duration_ms = int((now - self._unexpected_flow_started_at) * 1000)
                self._report_flow_event(
                    event_id=self._unexpected_flow_event_id,
                    event_status="started",
                    tap_id=TAP_ID,
                    volume_ml=total_volume_ml,
                    duration_ms=duration_ms,
                    card_present=card_present,
                    session_state=session_state,
                    reason="flow_detected_when_valve_closed_without_active_session",
                    valve_open=False,
                )
                self._unexpected_flow_reported = True
                self._unexpected_flow_last_report_at = now
            elif (
                self._unexpected_flow_reported
                and self._unexpected_flow_last_report_at is not None
                and now - self._unexpected_flow_last_report_at >= self.FLOW_EVENT_PROGRESS_INTERVAL_SECONDS
            ):
                duration_ms = int((now - self._unexpected_flow_started_at) * 1000)
                self._report_flow_event(
                    event_id=self._unexpected_flow_event_id,
                    event_status="updated",
                    tap_id=TAP_ID,
                    volume_ml=total_volume_ml,
                    duration_ms=duration_ms,
                    card_present=card_present,
                    session_state=session_state,
                    reason="flow_detected_when_valve_closed_without_active_session",
                    valve_open=False,
                )
                self._unexpected_flow_last_report_at = now
            return

        if self._unexpected_flow_started_at is None:
            return

        now = self._time_source()
        if (
            self._unexpected_flow_last_seen_at is not None
            and now - self._unexpected_flow_last_seen_at >= self.CLOSED_VALVE_FLOW_RESET_SECONDS
        ):
            if self._unexpected_flow_reported:
                duration_ms = int((self._unexpected_flow_last_seen_at - self._unexpected_flow_started_at) * 1000)
                self._report_flow_event(
                    event_id=self._unexpected_flow_event_id,
                    event_status="stopped",
                    tap_id=TAP_ID,
                    volume_ml=self._liters_to_ml(self._unexpected_flow_volume_liters),
                    duration_ms=duration_ms,
                    card_present=card_present,
                    session_state=session_state,
                    reason="flow_detected_when_valve_closed_without_active_session",
                    valve_open=False,
                )
                logging.info(
                    "Пролив при закрытом клапане прекратился. общий_объем=%s длительность_мс=%s",
                    format_volume(self._liters_to_ml(self._unexpected_flow_volume_liters)),
                    duration_ms,
                )
            self._reset_unexpected_flow_state()

    def _collect_post_close_flow(
        self,
        *,
        total_volume_liters: float,
        total_volume_ml: int,
        tail_volume_liters: float,
        max_volume_ml: int,
        price_per_ml_cents: int,
        has_authorized_price: bool,
        progress_display,
    ):
        close_started_at = self._time_source()
        last_tail_flow_at = None

        while True:
            now = self._time_source()
            if now - close_started_at >= self.FLOW_TAIL_MAX_SECONDS:
                return total_volume_liters, total_volume_ml, tail_volume_liters

            volume_delta_liters = self.hardware.get_volume_liters()
            if volume_delta_liters > 0:
                total_volume_liters += volume_delta_liters
                tail_volume_liters += volume_delta_liters
                total_volume_ml = self._liters_to_ml(total_volume_liters)
                last_tail_flow_at = now
                progress_display.update(
                    total_volume_ml,
                    max_volume_ml=max_volume_ml,
                    estimated_cost_cents=(
                        calculate_price_cents(total_volume_ml, price_per_ml_cents)
                        if has_authorized_price
                        else self._legacy_price_cents(total_volume_ml)
                    ),
                )
            elif last_tail_flow_at is not None and now - last_tail_flow_at >= self.FLOW_TAIL_IDLE_SECONDS:
                return total_volume_liters, total_volume_ml, tail_volume_liters
            elif last_tail_flow_at is None and now - close_started_at >= self.FLOW_TAIL_IDLE_SECONDS:
                return total_volume_liters, total_volume_ml, tail_volume_liters

            self._sleep(self.LOOP_INTERVAL_SECONDS)

    def _enter_card_must_be_removed(self, reason: str):
        self.hardware.valve_close()
        if not self.card_must_be_removed or self._card_must_be_removed_reason != reason:
            logging.warning("Переход в режим ожидания снятия карты: причина=%s", reason)
        self.card_must_be_removed = True
        self._card_removed_since = None
        self._card_must_be_removed_reason = reason

    def _handle_card_must_be_removed(self, *, card_present: bool):
        self.hardware.valve_close()
        if card_present:
            self._card_removed_since = None
            self._log_throttled(
                "card_must_be_removed_wait",
                "Извлеките карту из считывателя для продолжения. причина=%s" % self._card_must_be_removed_reason,
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
        self._last_session_summary = None
        logging.info(
            "Режим ожидания снятия карты завершён: считыватель свободен, задержка выдержана. предыдущая_причина=%s",
            released_reason,
        )

    def process(self):
        if self.card_must_be_removed:
            card_present = self.hardware.is_card_present()
            self._observe_closed_valve_flow(
                card_present=card_present,
                session_state="card_present_no_session" if card_present else "no_card_no_session",
            )
            self._publish_card_removal_state(card_present=card_present)
            self._handle_card_must_be_removed(card_present=card_present)
            return

        card_present = self.hardware.is_card_present()
        self._observe_closed_valve_flow(
            card_present=card_present,
            session_state="card_present_no_session" if card_present else "no_card_no_session",
        )

        if self.db_handler.has_unsynced_for_tap(TAP_ID):
            self._publish_runtime(
                phase="blocked",
                reason_code="processing_sync",
                card_present=card_present,
            )
            self._log_throttled(
                "processing_sync_block",
                "Кран занят синхронизацией: есть несинхронизированный налив, новый запуск заблокирован.",
                interval_seconds=self.PROCESSING_SYNC_REMINDER_SECONDS,
                state="blocked",
            )
            if card_present:
                self._enter_card_must_be_removed("processing_sync")
            return
        self._log_throttle.reset("processing_sync_block")

        if not card_present:
            self._publish_runtime(phase="idle", card_present=False)
            return

        card_uid = self.hardware.get_card_uid()
        if not card_uid:
            self._publish_runtime(phase="idle", card_present=card_present)
            return

        card_uid = card_uid.replace(" ", "").lower()
        self._publish_runtime(phase="authorizing", card_present=True)
        auth_result = self.sync_manager.authorize_pour(card_uid=card_uid, tap_id=TAP_ID)
        if not auth_result.get("allowed"):
            reason_code = auth_result.get("reason_code") or "authorize_denied"
            if reason_code == "request_failed" or auth_result.get("status_code") is None:
                reason_code = "backend_unreachable"
            self._log_throttled(
                f"authorize_denied:{reason_code}",
                "Старт налива отклонён для карты %s. код_ответа=%s причина=%s"
                % (card_uid, auth_result.get("status_code"), auth_result.get("reason")),
                level=logging.WARNING,
                interval_seconds=2.0,
                state=reason_code,
            )
            self._publish_runtime(
                phase="denied",
                reason_code=reason_code,
                card_present=True,
            )
            if reason_code == "lost_card":
                self._log_throttled(
                    "authorize_denied_lost_card",
                    "Карта отмечена как потерянная. Налив запрещён. Извлеките карту из считывателя.",
                    level=logging.WARNING,
                    interval_seconds=2.0,
                    state=reason_code,
                )
                self._enter_card_must_be_removed(reason_code)
            elif reason_code == "insufficient_funds":
                self._log_throttled(
                    "authorize_denied_insufficient_funds",
                    "Недостаточно средств для начала налива. Пополните баланс и извлеките карту из считывателя.",
                    level=logging.WARNING,
                    interval_seconds=2.0,
                    state=reason_code,
                )
                self._enter_card_must_be_removed(reason_code)
            else:
                self._enter_card_must_be_removed(reason_code)
            return

        self._log_throttle.reset("authorize_denied:authorize_denied")
        self._log_throttle.reset("authorize_denied:lost_card")
        self._log_throttle.reset("authorize_denied:insufficient_funds")
        self._log_throttle.reset("authorize_denied_lost_card")
        self._log_throttle.reset("authorize_denied_insufficient_funds")

        max_volume_ml = int(auth_result.get("max_volume_ml") or 0)
        price_per_ml_cents = int(auth_result.get("price_per_ml_cents") or 0)
        has_authorized_price = price_per_ml_cents > 0
        balance_cents_at_authorize = int(auth_result.get("balance_cents") or 0)
        guest_first_name = auth_result.get("guest_first_name")
        if max_volume_ml <= 0:
            self._log_throttled(
                "authorize_invalid_contract",
                "Авторизация вернула некорректные лимиты. максимальный_объем_мл=%s цена_за_мл_в_коп=%s"
                % (max_volume_ml, price_per_ml_cents),
                level=logging.ERROR,
                interval_seconds=2.0,
            )
            self._publish_runtime(
                phase="blocked",
                reason_code="authorize_invalid_contract",
                card_present=True,
            )
            self._enter_card_must_be_removed("authorize_invalid_contract")
            return

        logging.info(
            "Авторизация подтверждена для карты %s на кране %s. Открываем клапан, лимит %s.",
            card_uid,
            TAP_ID,
            format_volume(max_volume_ml),
        )
        self.hardware.reset_pulses()
        self.hardware.valve_open()
        started_monotonic = self._time_source()
        total_volume_liters = 0.0
        total_volume_ml = 0
        tail_volume_liters = 0.0
        last_flow_at = started_monotonic
        next_emergency_check_at = started_monotonic + self.EMERGENCY_CHECK_INTERVAL_SECONDS
        client_tx_id = str(uuid.uuid4())
        short_id = client_tx_id.replace("-", "")[:8].upper()
        self._publish_runtime(
            phase="authorized",
            card_present=True,
            guest_first_name=guest_first_name,
            balance_cents_at_authorize=balance_cents_at_authorize,
            price_per_ml_cents=price_per_ml_cents,
            max_volume_ml=max_volume_ml,
            current_volume_ml=0,
            current_cost_cents=0,
            projected_remaining_balance_cents=balance_cents_at_authorize,
            session_short_id=short_id,
        )
        card_removed_by_timeout = False
        stop_reason = "card_removed"
        progress_display = self._progress_factory()
        live_flow_reported = False
        live_flow_last_report_at = None

        try:
            while self.hardware.is_card_present():
                now = self._time_source()
                if now >= next_emergency_check_at:
                    if self.sync_manager.check_emergency_stop():
                        logging.info("Экстренная остановка активна. Закрываем клапан.")
                        stop_reason = "emergency_stop"
                        break
                    next_emergency_check_at = now + self.EMERGENCY_CHECK_INTERVAL_SECONDS

                volume_delta_liters = self.hardware.get_volume_liters()
                if volume_delta_liters > 0:
                    total_volume_liters += volume_delta_liters
                    total_volume_ml = self._liters_to_ml(total_volume_liters)
                    if has_reached_pour_limit(total_volume_ml, max_volume_ml):
                        overflow_ml = max(total_volume_ml - max_volume_ml, 0)
                        if overflow_ml > 0:
                            tail_volume_liters += overflow_ml / 1000.0
                        logging.info(
                            "Клапан закрыт по лимиту авторизации. лимит=%s фактический_объем_до_закрытия=%s",
                            format_volume(max_volume_ml),
                            format_volume(total_volume_ml),
                        )
                        stop_reason = "limit_reached"
                        break
                    last_flow_at = now
                    live_flow_reported, live_flow_last_report_at = self._maybe_report_authorized_flow_event(
                        client_tx_id=client_tx_id,
                        short_id=short_id,
                        card_uid=card_uid,
                        total_volume_ml=total_volume_ml,
                        duration_ms=int((now - started_monotonic) * 1000),
                        card_present=True,
                        reported=live_flow_reported,
                        last_report_at=live_flow_last_report_at,
                    )

                progress_display.update(
                    total_volume_ml,
                    max_volume_ml=max_volume_ml,
                    estimated_cost_cents=(
                        calculate_price_cents(total_volume_ml, price_per_ml_cents)
                        if has_authorized_price
                        else self._legacy_price_cents(total_volume_ml)
                    ),
                )
                current_cost_cents = (
                    calculate_price_cents(total_volume_ml, price_per_ml_cents)
                    if has_authorized_price
                    else self._legacy_price_cents(total_volume_ml)
                )
                self._publish_runtime(
                    phase="pouring" if total_volume_ml > 0 else "authorized",
                    card_present=True,
                    guest_first_name=guest_first_name,
                    balance_cents_at_authorize=balance_cents_at_authorize,
                    price_per_ml_cents=price_per_ml_cents,
                    max_volume_ml=max_volume_ml,
                    current_volume_ml=total_volume_ml,
                    current_cost_cents=current_cost_cents,
                    projected_remaining_balance_cents=self._projected_remaining_balance(
                        balance_cents_at_authorize,
                        current_cost_cents,
                    ),
                    session_short_id=short_id,
                )

                if now - last_flow_at >= self.FLOW_TIMEOUT_SECONDS:
                    logging.info("Клапан закрыт по таймауту")
                    card_removed_by_timeout = True
                    stop_reason = "flow_timeout"
                    timeout_price_cents = (
                        calculate_price_cents(total_volume_ml, price_per_ml_cents)
                        if has_authorized_price
                        else self._legacy_price_cents(total_volume_ml)
                    )
                    logging.info(
                        "Детали таймаута: короткий_номер=%s, объем=%s, сумма=%s",
                        short_id,
                        format_volume(total_volume_ml),
                        format_money_minor_units(timeout_price_cents),
                    )
                    break

                self._sleep(self.LOOP_INTERVAL_SECONDS)
        finally:
            self.hardware.valve_close()
            total_volume_liters, total_volume_ml, tail_volume_liters = self._collect_post_close_flow(
                total_volume_liters=total_volume_liters,
                total_volume_ml=total_volume_ml,
                tail_volume_liters=tail_volume_liters,
                max_volume_ml=max_volume_ml,
                price_per_ml_cents=price_per_ml_cents,
                has_authorized_price=has_authorized_price,
                progress_display=progress_display,
            )
            duration_ms = int((self._time_source() - started_monotonic) * 1000)
            final_card_present = self.hardware.is_card_present()
            self._stop_authorized_flow_event(
                client_tx_id=client_tx_id,
                short_id=short_id,
                card_uid=card_uid,
                total_volume_ml=total_volume_ml,
                duration_ms=duration_ms,
                card_present=final_card_present,
            )
            if not card_removed_by_timeout:
                logging.info("Клапан закрыт: причина=%s", stop_reason)
            progress_display.finish(total_volume_ml)

        if total_volume_ml > 1:
            duration_ms = int((self._time_source() - started_monotonic) * 1000)
            price_cents = (
                calculate_price_cents(total_volume_ml, price_per_ml_cents)
                if has_authorized_price
                else self._legacy_price_cents(total_volume_ml)
            )
            finished_summary = {
                "phase": "finished",
                "reason_code": None,
                "card_present": final_card_present,
                "guest_first_name": guest_first_name,
                "balance_cents_at_authorize": balance_cents_at_authorize,
                "price_per_ml_cents": price_per_ml_cents,
                "max_volume_ml": max_volume_ml,
                "current_volume_ml": total_volume_ml,
                "current_cost_cents": price_cents,
                "projected_remaining_balance_cents": self._projected_remaining_balance(
                    balance_cents_at_authorize,
                    price_cents,
                ),
                "session_short_id": short_id,
            }
            self._last_session_summary = finished_summary
            self._publish_runtime(**finished_summary)
            pour_data = {
                "client_tx_id": client_tx_id,
                "short_id": short_id,
                "card_uid": card_uid,
                "tap_id": TAP_ID,
                "duration_ms": duration_ms,
                "volume_ml": total_volume_ml,
                "tail_volume_ml": self._liters_to_ml(tail_volume_liters),
                "price_cents": price_cents,
                "price_per_ml_at_pour": float(
                    price_per_ml_cents if has_authorized_price else (PRICE_PER_100ML_CENTS / 100.0)
                ),
            }
            self.db_handler.add_pour(pour_data)
            logging.info("Запись о наливе сохранена в локальную БД")

        elif stop_reason == "emergency_stop":
            self._publish_runtime(
                phase="blocked",
                reason_code="emergency_stop",
                card_present=final_card_present,
            )

        if final_card_present:
            self._enter_card_must_be_removed("session_completed" if total_volume_ml > 1 else stop_reason)
