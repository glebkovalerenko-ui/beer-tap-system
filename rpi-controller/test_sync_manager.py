import sys
import types

sys.modules.setdefault(
    "requests",
    types.SimpleNamespace(
        Session=lambda: None,
        RequestException=Exception,
    ),
)

from sync_manager import SyncManager


class FakeResponse:
    def __init__(self, *, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return dict(self._payload)


class RecordingSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(
            {
                "method": "get",
                "url": url,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return self.response

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(
            {
                "method": "post",
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return self.response


class SequenceSession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []
        self.closed = False

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(
            {
                "method": "post",
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self):
        self.closed = True


class FakeDbHandler:
    def __init__(self, rows):
        self.rows = rows
        self.updated = []
        self.retried = []

    def get_unsynced_pours(self, limit):
        return list(self.rows[:limit])

    def update_status(self, client_tx_id, status):
        self.updated.append((client_tx_id, status))

    def mark_retry(self, client_tx_id):
        self.retried.append(client_tx_id)


def test_check_emergency_stop_uses_short_timeout():
    manager = SyncManager()
    manager.session = RecordingSession(FakeResponse(payload={"value": "false"}))

    assert manager.check_emergency_stop() is False
    assert manager.session.calls[0]["timeout"] == manager.EMERGENCY_STATUS_TIMEOUT_SECONDS


def test_report_flow_event_queues_without_synchronous_post():
    manager = SyncManager()
    manager.flow_event_session = RecordingSession(FakeResponse(status_code=202))

    assert manager.report_flow_event(
        event_id="event-1",
        event_status="started",
        tap_id=1,
        volume_ml=10,
        duration_ms=500,
        card_present=True,
        session_state="authorized_session",
        reason="authorized_pour_in_progress",
        valve_open=True,
        card_uid="abcd",
        short_id="ABC12345",
    ) is True
    assert manager.flow_event_session.calls == []
    assert manager._flow_event_queue.qsize() == 1


def test_process_flow_event_queue_once_uses_flow_event_session():
    manager = SyncManager()
    manager.flow_event_session = RecordingSession(FakeResponse(status_code=202))

    manager.report_flow_event(
        event_id="event-1",
        event_status="started",
        tap_id=1,
        volume_ml=10,
        duration_ms=500,
        card_present=True,
        session_state="authorized_session",
        reason="authorized_pour_in_progress",
        valve_open=True,
        card_uid="abcd",
        short_id="ABC12345",
    )

    assert manager.process_flow_event_queue_once() is True
    assert manager.flow_event_session.calls[0]["timeout"] == manager.FLOW_EVENT_TIMEOUT_SECONDS
    assert manager.flow_event_session.calls[0]["json"]["event_id"] == "event-1"


def test_sync_cycle_uses_dedicated_sync_session():
    manager = SyncManager()
    control_session = RecordingSession(FakeResponse(status_code=200))
    sync_session = RecordingSession(
        FakeResponse(
            status_code=200,
            payload={
                "results": [
                    {
                        "client_tx_id": "tx-1",
                        "status": "accepted",
                        "outcome": "synced",
                        "reason": "ok",
                    }
                ]
            },
        )
    )
    manager.session = control_session
    manager.sync_session = sync_session
    db_handler = FakeDbHandler(
        [
            {
                "client_tx_id": "tx-1",
                "short_id": "ABC12345",
                "card_uid": "abcd",
                "tap_id": 1,
                "duration_ms": 1000,
                "volume_ml": 25,
                "tail_volume_ml": 0,
                "price_cents": 125,
            }
        ]
    )

    manager.sync_cycle(db_handler)

    assert control_session.calls == []
    assert sync_session.calls[0]["timeout"] == manager.SYNC_TIMEOUT_SECONDS
    assert db_handler.updated == [("tx-1", "confirmed")]


def test_notify_sync_needed_wakes_waiter_immediately():
    manager = SyncManager()

    manager.notify_sync_needed()
    start = manager._time_source()
    manager.wait_for_next_sync_cycle(15)
    elapsed = manager._time_source() - start

    assert elapsed < 1


def test_authorize_pour_retries_once_after_request_exception():
    manager = SyncManager(sleep_fn=lambda _: None)
    first_session = SequenceSession([Exception("timed out")])
    second_session = SequenceSession(
        [
            FakeResponse(
                status_code=200,
                payload={
                    "allowed": True,
                    "guest_first_name": "Test",
                    "min_start_ml": 20,
                    "max_volume_ml": 500,
                    "price_per_ml_cents": 2,
                    "balance_cents": 1000,
                    "allowed_overdraft_cents": 0,
                    "safety_ml": 2,
                },
            )
        ]
    )
    manager.authorize_session = first_session
    manager._new_session = lambda: second_session

    result = manager.authorize_pour("card-uid", 1)

    assert result["allowed"] is True
    assert first_session.closed is True
    assert len(first_session.calls) == 1
    assert len(second_session.calls) == 1
    assert second_session.calls[0]["timeout"] == manager.AUTHORIZE_TIMEOUT_SECONDS


def test_authorize_pour_returns_request_failed_after_retry_exhausted():
    manager = SyncManager(sleep_fn=lambda _: None)
    first_session = SequenceSession([Exception("timed out")])
    second_session = SequenceSession([Exception("timed out again")])
    manager.authorize_session = first_session
    manager._new_session = lambda: second_session

    result = manager.authorize_pour("card-uid", 1)

    assert result["allowed"] is False
    assert result["reason_code"] == "request_failed"
    assert result["status_code"] is None
    assert "timed out again" in result["reason"]
    assert first_session.closed is True
    assert len(first_session.calls) == 1
    assert len(second_session.calls) == 1
