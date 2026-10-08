"""Hand-loss grace period and the state resets main.py relies on."""

import numpy as np

from modules.config import Config
from modules.gesture_engine import HandLossGrace


def test_grace_ignores_short_dropouts():
    grace = HandLossGrace(5)
    results = [grace.update(False) for _ in range(5)]    # 5 frames without a hand
    assert results == [False] * 5
    assert grace.update(True) is False                    # hand is back: nothing to reset


def test_grace_fires_once_when_the_hand_stays_lost():
    grace = HandLossGrace(5)
    results = [grace.update(False) for _ in range(20)]
    assert results.count(True) == 1
    assert results.index(True) == 5                       # the 6th missing frame


def test_grace_counter_restarts_after_the_hand_returns():
    grace = HandLossGrace(3)
    [grace.update(False) for _ in range(3)]
    grace.update(True)
    assert [grace.update(False) for _ in range(4)] == [False, False, False, True]


def test_default_grace_period_is_positive():
    assert Config().HAND_LOSS_GRACE_FRAMES > 0


def _hand_at(wrist_y=0.5, tip=(0.5, 0.5)):
    lm = [(0.5, 0.5, 0.0)] * 21
    lm[0] = (0.5, wrist_y, 0.0)
    lm[4] = (0.5, 0.5, 0.0)
    lm[8] = (tip[0], tip[1], 0.0)
    return lm


def test_scroll_reset_forgets_the_previous_wrist_position(gui_stubs):
    from modules.scroll_control import ScrollController

    ctrl = ScrollController(Config())
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    ctrl.scroll(_hand_at(wrist_y=0.2), frame)
    ctrl.reset()
    ctrl._last_scroll = 0.0
    ctrl.scroll(_hand_at(wrist_y=0.9), frame)             # would be a huge jump without reset
    gui_stubs.pyautogui.scroll.assert_not_called()


def test_zoom_reset_forgets_the_previous_pinch_distance(gui_stubs):
    from modules.zoom_control import ZoomController

    ctrl = ZoomController(Config())
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    ctrl.pinch_zoom(_hand_at(tip=(0.5, 0.45)), frame)
    ctrl.reset()
    ctrl.pinch_zoom(_hand_at(tip=(0.5, 0.05)), frame)     # would zoom without reset
    gui_stubs.pyautogui.scroll.assert_not_called()


def test_clicks_do_not_move_the_pointer_and_double_click_adds_one_click(gui_stubs):
    from modules.cursor_controller import CursorController

    cursor = CursorController(Config())
    hand = _hand_at()
    cursor.click(hand)
    cursor.right_click(hand)
    gui_stubs.pyautogui.moveTo.assert_not_called()
    gui_stubs.pyautogui.click.assert_called_once()
    gui_stubs.pyautogui.rightClick.assert_called_once()

    gui_stubs.pyautogui.click.reset_mock()
    cursor.double_click(hand)
    gui_stubs.pyautogui.click.assert_called_once()
    gui_stubs.pyautogui.doubleClick.assert_not_called()
