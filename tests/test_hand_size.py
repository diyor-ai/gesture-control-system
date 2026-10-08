"""Thresholds are in palm lengths, so they work near and far from the camera."""

import pytest

from modules.hand_tracker import HandTracker
from tests.conftest import make_hand, play

SCALES = [0.4, 0.7, 1.0, 1.6]       # far ... close


@pytest.mark.parametrize("scale", SCALES)
def test_hand_scale_follows_apparent_size(scale):
    assert HandTracker.hand_scale(make_hand("I", scale=scale)) == pytest.approx(0.25 * scale)


@pytest.mark.parametrize("scale", SCALES)
def test_pinch_clicks_at_every_distance(engine, clock, scale):
    out = play(engine, clock, make_hand("I", pinch="index", pinch_gap=0.03, scale=scale), 3)
    assert out.count("CLICK") == 1


@pytest.mark.parametrize("scale", SCALES)
def test_open_fingers_do_not_click_at_any_distance(engine, clock, scale):
    out = play(engine, clock, make_hand("I", pinch="index", pinch_gap=0.10, scale=scale), 5)
    assert set(out) == {"MOVE_CURSOR"}


@pytest.mark.parametrize("scale", SCALES)
def test_right_click_pinch_at_every_distance(engine, clock, scale):
    out = play(engine, clock, make_hand("M", pinch="middle", pinch_gap=0.03, scale=scale), 3)
    assert out.count("RIGHT_CLICK") == 1


def test_volume_and_brightness_readings_do_not_depend_on_distance():
    # same pose, different apparent size -> same normalised spread
    near = HandTracker.normalized_distance(make_hand("TP", scale=1.6), 4, 20)
    far = HandTracker.normalized_distance(make_hand("TP", scale=0.4), 4, 20)
    assert near == pytest.approx(far)
