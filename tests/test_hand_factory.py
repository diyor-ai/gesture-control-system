"""Sanity checks for the synthetic landmark factory used by all other tests."""

import pytest

from modules.hand_tracker import HandTracker
from tests.conftest import make_hand


@pytest.mark.parametrize("up", ["I", "IM", "IMR", "IMRP", "P", "R", "IP", ""])
@pytest.mark.parametrize("mirror", [False, True])
def test_non_thumb_fingers_match_request(up, mirror):
    states = HandTracker.fingers_up(make_hand(up, mirror=mirror))
    assert states[1:] == [f in up for f in "IMRP"]


def test_hand_has_21_landmarks():
    assert len(make_hand("IM")) == 21


@pytest.mark.parametrize("mirror", [False, True], ids=["right-hand-shape", "left-hand-shape"])
def test_thumb_detection_works_for_both_hands(mirror):
    assert HandTracker.fingers_up(make_hand("T", mirror=mirror))[0] is True
    assert HandTracker.fingers_up(make_hand("", mirror=mirror))[0] is False
    assert HandTracker.fingers_up(make_hand("TIMRP", mirror=mirror)) == [True] * 5
