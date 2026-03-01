import io

from terminal_progress import TerminalProgressDisplay


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def test_terminal_progress_fallback_rate_limits_lines():
    clock = FakeClock()
    buffer = io.StringIO()
    display = TerminalProgressDisplay(
        stream=buffer,
        time_source=clock.monotonic,
        fallback_interval_seconds=0.5,
        force_live=False,
    )

    display.update(12, estimated_cost_cents=18)
    clock.advance(0.2)
    display.update(13, estimated_cost_cents=19)
    clock.advance(0.5)
    display.update(18, estimated_cost_cents=27)
    display.finish(18)

    assert buffer.getvalue().splitlines() == [
        "Pouring: 12 ml | est. cost: 18 cents",
        "Pouring: 18 ml | est. cost: 27 cents",
        "Session finished. Poured: 18 ml",
    ]


def test_terminal_progress_live_mode_uses_carriage_return():
    clock = FakeClock()
    buffer = io.StringIO()
    display = TerminalProgressDisplay(
        stream=buffer,
        time_source=clock.monotonic,
        live_interval_seconds=0.0,
        force_live=True,
    )

    display.update(10, estimated_cost_cents=15)
    display.update(20, estimated_cost_cents=30)
    display.finish(20)

    output = buffer.getvalue()
    assert "\rPouring: 10 ml | est. cost: 15 cents" in output
    assert "\rPouring: 20 ml | est. cost: 30 cents" in output
    assert output.endswith("Session finished. Poured: 20 ml\n")
