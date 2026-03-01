import logging

from log_throttle import LogThrottle


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def test_log_throttle_dedupes_and_logs_on_state_change(caplog):
    clock = FakeClock()
    throttle = LogThrottle(time_source=clock.monotonic)

    with caplog.at_level(logging.INFO):
        throttle.log("processing", "processing_sync: pending_records=1", state=1, interval_seconds=10.0)
        throttle.log("processing", "processing_sync: pending_records=1", state=1, interval_seconds=10.0)
        clock.advance(1.0)
        throttle.log("processing", "processing_sync: pending_records=2", state=2, interval_seconds=10.0)
        clock.advance(11.0)
        throttle.log("processing", "processing_sync: pending_records=2", state=2, interval_seconds=10.0)

    messages = [record.message for record in caplog.records]
    assert messages == [
        "processing_sync: pending_records=1",
        "processing_sync: pending_records=2",
        "processing_sync: pending_records=2",
    ]
