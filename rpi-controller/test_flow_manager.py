from flow_manager import FlowManager


class FakeHardware:
    def __init__(self):
        self.card_present = True
        self.card_uid = "CARD-001"
        self.valve_open_calls = 0
        self.valve_close_calls = 0
        self.reset_pulses_calls = 0

    def is_card_present(self):
        return self.card_present

    def get_card_uid(self):
        return self.card_uid

    def valve_open(self):
        self.valve_open_calls += 1

    def valve_close(self):
        self.valve_close_calls += 1

    def get_volume_liters(self):
        return 0.0

    def reset_pulses(self):
        self.reset_pulses_calls += 1


class FakeDbHandler:
    def __init__(self):
        self.added_pours = []

    def has_unsynced_for_tap(self, tap_id):
        return False

    def add_pour(self, pour_data):
        self.added_pours.append(pour_data)


class FakeSyncManager:
    def authorize_pour(self, card_uid, tap_id):
        return {
            "allowed": False,
            "reason": "Insufficient funds: top up guest balance before pouring.",
            "reason_code": "insufficient_funds",
            "status_code": 403,
        }

    def check_emergency_stop(self):
        return False


def test_controller_does_not_open_valve_on_insufficient_funds():
    hardware = FakeHardware()
    db_handler = FakeDbHandler()
    sync_manager = FakeSyncManager()
    manager = FlowManager(hardware=hardware, db_handler=db_handler, sync_manager=sync_manager)

    manager.process()

    assert hardware.valve_open_calls == 0
    assert hardware.valve_close_calls >= 1
    assert manager.card_must_be_removed is True
    assert db_handler.added_pours == []

