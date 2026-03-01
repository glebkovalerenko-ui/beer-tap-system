import sys
import time


class TerminalProgressDisplay:
    def __init__(
        self,
        stream=None,
        time_source=None,
        live_interval_seconds=0.2,
        fallback_interval_seconds=0.5,
        force_live=None,
    ):
        self.stream = stream or sys.stdout
        self._time_source = time_source or time.monotonic
        self._live_interval_seconds = live_interval_seconds
        self._fallback_interval_seconds = fallback_interval_seconds
        self._supports_live = force_live if force_live is not None else bool(getattr(self.stream, "isatty", lambda: False)())
        self._last_render_at = None
        self._last_line_length = 0
        self._line_active = False

    def update(self, current_volume_ml, *, max_volume_ml=None, estimated_cost_cents=None):
        now = self._time_source()
        interval_seconds = self._live_interval_seconds if self._supports_live else self._fallback_interval_seconds
        if self._last_render_at is not None and now - self._last_render_at < interval_seconds:
            return False

        line = self._format_line(
            current_volume_ml=current_volume_ml,
            max_volume_ml=max_volume_ml,
            estimated_cost_cents=estimated_cost_cents,
        )

        if self._supports_live:
            padded_line = line.ljust(max(self._last_line_length, len(line)))
            self.stream.write("\r" + padded_line)
            self._last_line_length = len(padded_line)
            self._line_active = True
        else:
            self.stream.write(line + "\n")

        self.stream.flush()
        self._last_render_at = now
        return True

    def finish(self, total_volume_ml):
        final_line = f"Session finished. Poured: {int(total_volume_ml)} ml"
        if self._supports_live and self._line_active:
            self.stream.write("\r" + " " * self._last_line_length + "\r")
        self.stream.write(final_line + "\n")
        self.stream.flush()
        self._last_render_at = None
        self._last_line_length = 0
        self._line_active = False

    @staticmethod
    def _format_line(current_volume_ml, *, max_volume_ml=None, estimated_cost_cents=None):
        parts = [f"Pouring: {int(current_volume_ml)} ml"]
        if max_volume_ml:
            parts.append(f"/ {int(max_volume_ml)} ml")
        if estimated_cost_cents is not None:
            parts.append(f"| est. cost: {int(estimated_cost_cents)} cents")
        return " ".join(parts)
