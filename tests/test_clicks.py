"""Clicks must be edge-triggered: one event per pinch, release required."""

from tests.conftest import make_hand, play

PINCH = make_hand("I", pinch="index")
POINT = make_hand("I")
RIGHT_PINCH = make_hand("M", pinch="middle")


def _events(gestures):
    return [g for g in gestures if g not in ("IDLE", "MOVE_CURSOR")]


def test_held_pinch_fires_exactly_one_click(engine_any, clock):
    out = play(engine_any, clock, PINCH, 60)          # 2 s of pinching
    assert _events(out) == ["CLICK"]


def test_no_alternating_click_double_click(engine_any, clock):
    out = play(engine_any, clock, PINCH, 10)
    assert "DOUBLE_CLICK" not in out


def test_release_then_new_pinch_after_interval_is_a_second_single_click(engine_any, clock):
    out = play(engine_any, clock, PINCH, 5)
    out += play(engine_any, clock, POINT, 5)
    clock.advance(1.0)                              # well past DOUBLE_CLICK_INTERVAL
    out += play(engine_any, clock, PINCH, 5)
    assert _events(out) == ["CLICK", "CLICK"]


def test_two_separate_pinches_within_interval_make_a_double_click(engine_any, clock):
    out = play(engine_any, clock, PINCH, 3)
    out += play(engine_any, clock, POINT, 3)
    out += play(engine_any, clock, PINCH, 3)
    assert _events(out) == ["CLICK", "DOUBLE_CLICK"]


def test_third_pinch_starts_a_fresh_click(engine_any, clock):
    out = []
    for _ in range(3):
        out += play(engine_any, clock, PINCH, 3)
        out += play(engine_any, clock, POINT, 3)
    assert _events(out) == ["CLICK", "DOUBLE_CLICK", "CLICK"]


def test_right_click_fires_once_per_pinch(engine_any, clock):
    out = play(engine_any, clock, RIGHT_PINCH, 30)
    assert _events(out) == ["RIGHT_CLICK"]
    out = play(engine_any, clock, make_hand("M"), 3)
    out += play(engine_any, clock, RIGHT_PINCH, 3)
    assert _events(out) == ["RIGHT_CLICK"]
