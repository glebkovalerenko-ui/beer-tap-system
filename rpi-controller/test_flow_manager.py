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

    def authorize_pour(self, card_uid, tap_id):
        return dict(self.auth_result)

    def check_emergency_stop(self):
        return False

    def report_flow_anomaly(self, **payload):
        self.reported_anomalies.append(payload)
        return True


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

    messages = [record.message for record in caplog.records if "Кран занят синхронизацией" in record.message]
    assert messages == [
        "Кран занят синхронизацией: есть несинхронизированный налив, новый запуск заблокирован.",
        "Кран занят синхронизацией: есть несинхронизированный налив, новый запуск заблокирован.",
    ]


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

    manager.process()

    assert db_handler.pours[0]["volume_ml"] == 30
    assert db_handler.pours[0]["tail_volume_ml"] == 10


def test_flow_manager_does_not_carry_closed_valve_flow_into_next_pour():
    clock = FakeClock()
    hardware = FakeHardware(
        card_present_responses=[True, True, False, False, True, True, False, False],
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
    assert len(sync_manager.reported_anomalies) == 1
    assert sync_manager.reported_anomalies[0]["volume_ml"] == 10
    assert sync_manager.reported_anomalies[0]["session_state"] == "no_card_no_session"


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
            "reason": "Insufficient funds: top up guest balance before pouring.",
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
