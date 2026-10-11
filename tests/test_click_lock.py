"""Click lock and fast double click: both clicks of a double-pinch hit one pixel."""

import numpy as np
import pytest

from modules.config import Config
from tests.conftest import FakeClock, make_hand, play


class RecordingBackend:
    """Input backend that records every event with the fake time."""

    name = "recording"

    def __init__(self, clock):
        self.clock = clock
        self.pos = (0, 0)
        self.events = []

    def move_to(self, x, y):
        self.pos = (x, y)

    def click(self):
        self.events.append((self.clock(), "click", self.pos))

    def right_click(self):
        self.events.append((self.clock(), "right_click", self.pos))


def _hand(tip):
    lm = [(0.5, 0.5, 0.0)] * 21
    lm[8] = (tip[0], tip[1], 0.0)
    return lm


@pytest.fixture
def rig(gui_stubs):
    from modules.cursor_controller import CursorController

    clock = FakeClock()
    backend = RecordingBackend(clock)
    cursor = CursorController(
        Config(), backend, clock=clock, sleep=lambda s: clock.advance(s)
    )
    return cursor, backend, clock


def test_cursor_does_not_move_during_the_click_lock(rig):
    cursor, backend, clock = rig
    cursor.move(_hand((0.4, 0.4)))
    cursor.click(_hand((0.4, 0.4)))
    pos = backend.pos
    clock.advance(Config().CLICK_LOCK_TIME - 0.01)
    cursor.move(_hand((0.7, 0.7)))                  # thumb opening shifts the fingertip
    assert backend.pos == pos


def test_cursor_follows_the_finger_again_after_the_lock(rig):
    cursor, backend, clock = rig
    cursor.click(_hand((0.4, 0.4)))
    pos = backend.pos
    clock.advance(Config().CLICK_LOCK_TIME + 0.01)
    cursor.move(_hand((0.7, 0.7)))
    assert backend.pos != pos


def test_lock_covers_the_whole_double_click_window():
    cfg = Config()
    assert cfg.CLICK_LOCK_TIME >= cfg.DOUBLE_CLICK_INTERVAL


def test_double_click_sends_two_fast_clicks_at_the_locked_position(rig):
    cursor, backend, clock = rig
    cursor.move(_hand((0.4, 0.4)))
    cursor.click(_hand((0.4, 0.4)))                  # first pinch
    clock.advance(0.55)                              # slow human double-pinch
    cursor.move(_hand((0.9, 0.9)))                   # still locked: ignored
    cursor.double_click(_hand((0.9, 0.9)))           # second pinch
    clicks = backend.events
    assert [e[1] for e in clicks] == ["click"] * 3
    assert len({e[2] for e in clicks}) == 1          # one pixel for all clicks
    (t2, _, _), (t3, _, _) = clicks[1], clicks[2]
    assert t3 - t2 == pytest.approx(Config().FAST_DOUBLE_CLICK_GAP)
    assert t3 - t2 < 0.1                             # well inside the OS double-click time


def test_double_pinch_through_the_engine_clicks_at_one_position(rig, engine):
    """Slow double-pinch (0.5 s between pinch starts) is a DOUBLE_CLICK at one pixel."""
    cursor, backend, clock = rig
    engine._clock = clock                             # one shared fake clock
    point, pinch = make_hand("I"), make_hand("I", pinch="index")

    def run(hand, frames):
        for g in play(engine, clock, hand, frames):
            if g == "MOVE_CURSOR":
                cursor.move(_hand((0.5 + 0.2 * np.random.rand(), 0.5)))
            elif g == "CLICK":
                cursor.click(hand)
            elif g == "DOUBLE_CLICK":
                cursor.double_click(hand)

    run(point, 3)
    run(pinch, 3)
    run(point, 12)                                    # ~0.4 s of finger wobbling
    run(pinch, 3)
    kinds = [e[1] for e in backend.events]
    assert kinds == ["click", "click", "click"]
    assert len({e[2] for e in backend.events}) == 1


def test_debug_log_prints_every_click_only_in_debug_mode(rig, capsys):
    from modules.cursor_controller import CursorController

    cursor, backend, clock = rig
    cursor.click(_hand((0.5, 0.5)))
    assert capsys.readouterr().out == ""

    loud = CursorController(Config(), backend, clock=clock, sleep=lambda s: None, debug=True)
    loud.click(_hand((0.5, 0.5)))
    loud.double_click(_hand((0.5, 0.5)))
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 3 and all(l.startswith("[click]") and "x=" in l and "y=" in l for l in lines)
