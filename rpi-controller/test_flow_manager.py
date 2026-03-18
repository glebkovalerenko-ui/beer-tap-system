import io
import logging

from flow_manager import FlowManager
from terminal_progress import TerminalProgressDisplay


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeHardware:
    def __init__(
        self,
        *,
        card_present_responses,
        volume_deltas_liters=None,
        closed_volume_deltas_liters=None,
        post_close_volume_deltas_liters=None,
    ):
        self.card_present_responses = list(card_present_responses)
        self.open_volume_deltas_liters = list(volume_deltas_liters or [])
        self.closed_volume_deltas_liters = list(closed_volume_deltas_liters or [])
        self.post_close_volume_deltas_liters = list(post_close_volume_deltas_liters or [])
        self.valve_open_calls = 0
        self.valve_close_calls = 0
        self.reset_pulses_calls = 0
        self.valve_is_open = False

    def is_card_present(self):
        if self.card_present_responses:
            return self.card_present_responses.pop(0)
        return False

    def get_card_uid(self):
        return "AA BB CC DD"

    def valve_open(self):
        self.valve_open_calls += 1
        self.valve_is_open = True

    def valve_close(self):
        if self.valve_is_open and self.post_close_volume_deltas_liters:
            self.closed_volume_deltas_liters.extend(self.post_close_volume_deltas_liters)
            self.post_close_volume_deltas_liters = []
        self.valve_close_calls += 1
        self.valve_is_open = False

    def get_volume_liters(self):
        if self.closed_volume_deltas_liters:
            return self.closed_volume_deltas_liters.pop(0)
        if self.valve_is_open and self.open_volume_deltas_liters:
            return self.open_volume_deltas_liters.pop(0)
        return 0.0

    def reset_pulses(self):
        self.reset_pulses_calls += 1


class FakeDbHandler:
    def __init__(self, *, has_unsynced=False):
        self._has_unsynced = has_unsynced
        self.pours = []

    def has_unsynced_for_tap(self, tap_id):
        return self._has_unsynced

    def add_pour(self, pour_data):
        self.pours.append(pour_data)


class FakeSyncManager:
    def __init__(self, auth_result):
        self.auth_result = auth_result
        self.reported_anomalies = []
        self.reported_flow_events = []
        self.sync_cycle_calls = 0
        self.sync_wake_notifications = 0

    def authorize_pour(self, card_uid, tap_id):
        return dict(self.auth_result)

    def check_emergency_stop(self):
        return False

    def report_flow_anomaly(self, **payload):
        self.reported_anomalies.append(payload)
        return True

    def report_flow_event(self, **payload):
        self.reported_flow_events.append(payload)
        return True

    def sync_cycle(self, db_handler):
        self.sync_cycle_calls += 1
        return None

    def notify_sync_needed(self):
        self.sync_wake_notifications += 1


class FakeRuntimePublisher:
    def __init__(self):
        self.snapshots = []

    def publish(self, **payload):
        self.snapshots.append(dict(payload))
        return payload


def test_flow_manager_throttles_processing_sync_logs(caplog):
    clock = FakeClock()
    hardware = FakeHardware(card_present_responses=[False, False, False])
    db_handler = FakeDbHandler(has_unsynced=True)
    sync_manager = FakeSyncManager({"allowed": False})
    manager = FlowManager(
        hardware,
        db_handler,
        sync_manager,
        time_source=clock.monotonic,
        sleep_fn=clock.sleep,
    )

    with caplog.at_level(logging.INFO):
        manager.process()
        manager.process()
        clock.sleep(10.1)
        manager.process()

    messages = [record.message for record in caplog.records if record.levelno == logging.INFO]
    assert len(messages) == 2


def test_flow_manager_shows_progress_and_accumulates_volume():
    clock = FakeClock()
    buffer = io.StringIO()
    hardware = FakeHardware(
        card_present_responses=[True, True, True, False],
        volume_deltas_liters=[0.015, 0.02],
    )
    db_handler = FakeDbHandler()
    sync_manager = FakeSyncManager({"allowed": True, "max_volume_ml": 100})
    manager = FlowManager(
        hardware,
        db_handler,
        sync_manager,
        time_source=clock.monotonic,
        sleep_fn=clock.sleep,
        progress_factory=lambda: TerminalProgressDisplay(
            stream=buffer,
            time_source=clock.monotonic,
            fallback_interval_seconds=0.0,
            force_live=False,
        ),
    )

    manager.process()

    output_lines = buffer.getvalue().splitlines()
    assert "Налив: 15 мл из 100 мл | сумма: 0,22 ₽" in output_lines
    assert "Налив: 35 мл из 100 мл | сумма: 0,52 ₽" in output_lines
    assert output_lines[-1] == "Сессия завершена. Налито: 35 мл"
    assert db_handler.pours[0]["volume_ml"] == 35
    assert db_handler.pours[0]["tail_volume_ml"] == 0
    assert db_handler.pours[0]["price_cents"] == 52
    assert hardware.valve_open_calls == 1
    assert hardware.reset_pulses_calls == 1


def test_flow_manager_accounts_post_close_tail_in_current_pour():
    clock = FakeClock()
    hardware = FakeHardware(
        card_present_responses=[True, True, False],
        volume_deltas_liters=[0.02],
        post_close_volume_deltas_liters=[0.01],
    )
    db_handler = FakeDbHandler()
    sync_manager = FakeSyncManager({"allowed": True, "max_volume_ml": 100})
    manager = FlowManager(
        hardware,
        db_handler,
        sync_manager,
        time_source=clock.monotonic,
        sleep_fn=clock.sleep,
        progress_factory=lambda: TerminalProgressDisplay(
            stream=io.StringIO(),
            time_source=clock.monotonic,
            fallback_interval_seconds=0.0,
            force_live=False,
        ),
    )
    manager.AUTHORIZED_CARD_ABSENCE_DEBOUNCE_SECONDS = 0.0

    manager.process()

    assert db_handler.pours[0]["volume_ml"] == 30
    assert db_handler.pours[0]["tail_volume_ml"] == 10


def test_flow_manager_queues_zero_volume_terminal_sync_when_card_removed_without_pour():
    clock = FakeClock()
    hardware = FakeHardware(card_present_responses=[True, True, False])
    db_handler = FakeDbHandler()
    sync_manager = FakeSyncManager({"allowed": True, "max_volume_ml": 100})
    manager = FlowManager(
        hardware,
        db_handler,
        sync_manager,
        time_source=clock.monotonic,
        sleep_fn=clock.sleep,
        progress_factory=lambda: TerminalProgressDisplay(
            stream=io.StringIO(),
            time_source=clock.monotonic,
            fallback_interval_seconds=0.0,
            force_live=False,
        ),
    )
    manager.AUTHORIZED_CARD_ABSENCE_DEBOUNCE_SECONDS = 0.0

    manager.process()

    assert len(db_handler.pours) == 1
    assert db_handler.pours[0]["volume_ml"] == 0
    assert db_handler.pours[0]["tail_volume_ml"] == 0
    assert db_handler.pours[0]["price_cents"] == 0
    assert sync_manager.reported_flow_events == []
    assert sync_manager.sync_cycle_calls == 1


def test_flow_manager_debounces_transient_card_loss_during_authorized_session():
    clock = FakeClock()
    hardware = FakeHardware(card_present_responses=[True, True, False] + [True] * 20)
    db_handler = FakeDbHandler()
    sync_manager = FakeSyncManager({"allowed": True, "max_volume_ml": 100})
    manager = FlowManager(
        hardware,
        db_handler,
        sync_manager,
        time_source=clock.monotonic,
        sleep_fn=clock.sleep,
        progress_factory=lambda: TerminalProgressDisplay(
            stream=io.StringIO(),
            time_source=clock.monotonic,
            fallback_interval_seconds=0.0,
            force_live=False,
        ),
    )
    manager.FLOW_TIMEOUT_SECONDS = 0.6
    manager.AUTHORIZED_CARD_ABSENCE_DEBOUNCE_SECONDS = 0.25

    manager.process()

    assert manager.card_must_be_removed is True
    assert manager._card_must_be_removed_reason == "flow_timeout"
    assert len(db_handler.pours) == 1
    assert db_handler.pours[0]["volume_ml"] == 0
    assert sync_manager.sync_cycle_calls == 1


def test_flow_manager_does_not_carry_closed_valve_flow_into_next_pour():
    clock = FakeClock()
    hardware = FakeHardware(
        card_present_responses=[True, True, False, False, False, True, True, False, False, False],
        volume_deltas_liters=[0.02, 0.015],
        post_close_volume_deltas_liters=[0.01],
    )
    db_handler = FakeDbHandler()
    sync_manager = FakeSyncManager({"allowed": True, "max_volume_ml": 100})
    manager = FlowManager(
        hardware,
        db_handler,
        sync_manager,
        time_source=clock.monotonic,
        sleep_fn=clock.sleep,
        progress_factory=lambda: TerminalProgressDisplay(
            stream=io.StringIO(),
            time_source=clock.monotonic,
            fallback_interval_seconds=0.0,
            force_live=False,
        ),
    )
    manager.AUTHORIZED_CARD_ABSENCE_DEBOUNCE_SECONDS = 0.0

    manager.process()
    manager.process()

    assert db_handler.pours[0]["volume_ml"] == 30
    assert db_handler.pours[1]["volume_ml"] == 15
    assert db_handler.pours[1]["tail_volume_ml"] == 0


def test_flow_manager_reports_closed_valve_flow_without_session():
    clock = FakeClock()
    hardware = FakeHardware(
        card_present_responses=[False, False],
        closed_volume_deltas_liters=[0.01],
    )
    db_handler = FakeDbHandler()
    sync_manager = FakeSyncManager({"allowed": False})
    manager = FlowManager(
        hardware,
        db_handler,
        sync_manager,
        time_source=clock.monotonic,
        sleep_fn=clock.sleep,
    )

    manager.process()
    clock.sleep(1.1)
    manager.process()

    assert db_handler.pours == []
    assert sync_manager.reported_anomalies == []
    assert [item["event_status"] for item in sync_manager.reported_flow_events] == ["started", "stopped"]
    assert sync_manager.reported_flow_events[0]["volume_ml"] == 10
    assert sync_manager.reported_flow_events[0]["session_state"] == "no_card_no_session"
    assert sync_manager.reported_flow_events[1]["volume_ml"] == 10


def test_flow_manager_reports_live_authorized_pour_updates():
    clock = FakeClock()
    hardware = FakeHardware(
        card_present_responses=[True, True, True, False],
        volume_deltas_liters=[0.015, 0.02],
    )
    db_handler = FakeDbHandler()
    sync_manager = FakeSyncManager({"allowed": True, "max_volume_ml": 100})
    manager = FlowManager(
        hardware,
        db_handler,
        sync_manager,
        time_source=clock.monotonic,
        sleep_fn=clock.sleep,
        progress_factory=lambda: TerminalProgressDisplay(
            stream=io.StringIO(),
            time_source=clock.monotonic,
            fallback_interval_seconds=0.0,
            force_live=False,
        ),
    )

    manager.process()

    assert sync_manager.reported_flow_events[0]["event_status"] == "started"
    assert sync_manager.reported_flow_events[-1]["event_status"] == "stopped"
    assert sync_manager.reported_flow_events[-1]["session_state"] == "authorized_session"
    assert sync_manager.reported_flow_events[-1]["volume_ml"] == 35


def test_flow_manager_wakes_sync_worker_after_pour_is_saved():
    clock = FakeClock()
    hardware = FakeHardware(
        card_present_responses=[True, True, False],
        volume_deltas_liters=[0.02],
    )
    db_handler = FakeDbHandler()
    sync_manager = FakeSyncManager({"allowed": True, "max_volume_ml": 100})
    manager = FlowManager(
        hardware,
        db_handler,
        sync_manager,
        time_source=clock.monotonic,
        sleep_fn=clock.sleep,
        progress_factory=lambda: TerminalProgressDisplay(
            stream=io.StringIO(),
            time_source=clock.monotonic,
            fallback_interval_seconds=0.0,
            force_live=False,
        ),
    )

    manager.process()

    assert db_handler.pours[0]["volume_ml"] == 20
    assert sync_manager.sync_wake_notifications == 1


def test_flow_manager_deny_does_not_start_progress():
    clock = FakeClock()
    hardware = FakeHardware(card_present_responses=[True])
    db_handler = FakeDbHandler()
    sync_manager = FakeSyncManager(
        {
            "allowed": False,
            "reason_code": "lost_card",
            "reason": "lost_card",
            "status_code": 403,
        }
    )
    created = {"count": 0}

    manager = FlowManager(
        hardware,
        db_handler,
        sync_manager,
        time_source=clock.monotonic,
        sleep_fn=clock.sleep,
        progress_factory=lambda: created.__setitem__("count", created["count"] + 1),
    )

    manager.process()

    assert created["count"] == 0
    assert db_handler.pours == []
    assert manager.card_must_be_removed is True


def test_controller_does_not_open_valve_on_insufficient_funds():
    hardware = FakeHardware(card_present_responses=[True])
    db_handler = FakeDbHandler()
    sync_manager = FakeSyncManager(
        {
            "allowed": False,
            "reason": "Недостаточно средств: пополните баланс гостя перед наливом.",
            "reason_code": "insufficient_funds",
            "status_code": 403,
        }
    )
    manager = FlowManager(
        hardware=hardware,
        db_handler=db_handler,
        sync_manager=sync_manager,
    )

    manager.process()

    assert hardware.valve_open_calls == 0
    assert hardware.valve_close_calls >= 1
    assert manager.card_must_be_removed is True
    assert db_handler.pours == []


def test_flow_manager_publishes_idle_runtime_snapshot():
    clock = FakeClock()
    runtime_publisher = FakeRuntimePublisher()
    manager = FlowManager(
        FakeHardware(card_present_responses=[False]),
        FakeDbHandler(),
        FakeSyncManager({"allowed": False}),
        time_source=clock.monotonic,
        sleep_fn=clock.sleep,
        runtime_publisher=runtime_publisher,
    )

    manager.process()

    assert runtime_publisher.snapshots[-1]["phase"] == "idle"
    assert runtime_publisher.snapshots[-1]["card_present"] is False


def test_flow_manager_publishes_denied_runtime_snapshot():
    clock = FakeClock()
    runtime_publisher = FakeRuntimePublisher()
    manager = FlowManager(
        FakeHardware(card_present_responses=[True]),
        FakeDbHandler(),
        FakeSyncManager(
            {
                "allowed": False,
                "reason_code": "insufficient_funds",
                "reason": "insufficient_funds",
                "status_code": 403,
            }
        ),
        time_source=clock.monotonic,
        sleep_fn=clock.sleep,
        runtime_publisher=runtime_publisher,
    )

    manager.process()

    assert runtime_publisher.snapshots[-1]["phase"] == "denied"
    assert runtime_publisher.snapshots[-1]["reason_code"] == "insufficient_funds"


def test_flow_manager_publishes_finished_runtime_snapshot():
    clock = FakeClock()
    runtime_publisher = FakeRuntimePublisher()
    manager = FlowManager(
        FakeHardware(
            card_present_responses=[True, True, False],
            volume_deltas_liters=[0.02],
        ),
        FakeDbHandler(),
        FakeSyncManager(
            {
                "allowed": True,
                "guest_first_name": "Иван",
                "max_volume_ml": 100,
                "price_per_ml_cents": 2,
                "balance_cents": 1000,
            }
        ),
        time_source=clock.monotonic,
        sleep_fn=clock.sleep,
        progress_factory=lambda: TerminalProgressDisplay(
            stream=io.StringIO(),
            time_source=clock.monotonic,
            fallback_interval_seconds=0.0,
            force_live=False,
        ),
        runtime_publisher=runtime_publisher,
    )
    manager.AUTHORIZED_CARD_ABSENCE_DEBOUNCE_SECONDS = 0.0

    manager.process()

    phases = [snapshot["phase"] for snapshot in runtime_publisher.snapshots]
    assert "authorized" in phases
    assert "pouring" in phases
    assert runtime_publisher.snapshots[-1]["phase"] == "finished"
    assert runtime_publisher.snapshots[-1]["guest_first_name"] == "Иван"
    assert runtime_publisher.snapshots[-1]["current_volume_ml"] == 20


def test_flow_manager_returns_to_idle_after_zero_volume_card_removed_session():
    clock = FakeClock()
    runtime_publisher = FakeRuntimePublisher()
    manager = FlowManager(
        FakeHardware(
            card_present_responses=[True, False, False],
            volume_deltas_liters=[],
        ),
        FakeDbHandler(),
        FakeSyncManager(
            {
                "allowed": True,
                "guest_first_name": "Ivan",
                "max_volume_ml": 100,
                "price_per_ml_cents": 2,
                "balance_cents": 1000,
            }
        ),
        time_source=clock.monotonic,
        sleep_fn=clock.sleep,
        progress_factory=lambda: TerminalProgressDisplay(
            stream=io.StringIO(),
            time_source=clock.monotonic,
            fallback_interval_seconds=0.0,
            force_live=False,
        ),
        runtime_publisher=runtime_publisher,
    )

    manager.process()

    phases = [snapshot["phase"] for snapshot in runtime_publisher.snapshots]
    assert "authorized" in phases
    assert runtime_publisher.snapshots[-1]["phase"] == "idle"
    assert runtime_publisher.snapshots[-1]["card_present"] is False
