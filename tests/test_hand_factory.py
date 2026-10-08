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
