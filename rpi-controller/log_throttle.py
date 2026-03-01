import logging
import time
from dataclasses import dataclass


_UNSET = object()


@dataclass
class _LogEntry:
    last_logged_at: float
    last_state: object = _UNSET


class LogThrottle:
    def __init__(self, time_source=None):
        self._time_source = time_source or time.monotonic
        self._entries = {}

    def log(self, key, message, *, level=logging.INFO, interval_seconds=3.0, state=_UNSET, logger=None):
        now = self._time_source()
        target_logger = logger or logging.getLogger()
        entry = self._entries.get(key)

        if entry is None:
            self._entries[key] = _LogEntry(last_logged_at=now, last_state=state)
            target_logger.log(level, message)
            return True

        if state is not _UNSET and entry.last_state != state:
            entry.last_state = state
            entry.last_logged_at = now
            target_logger.log(level, message)
            return True

        if now - entry.last_logged_at >= interval_seconds:
            entry.last_logged_at = now
            if state is not _UNSET:
                entry.last_state = state
            target_logger.log(level, message)
            return True

        return False

    def reset(self, key):
        self._entries.pop(key, None)
