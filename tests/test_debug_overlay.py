"""--debug flag and overlay (OpenCV is stubbed, so no window is needed)."""

import numpy as np

from tests.conftest import make_hand, play


def test_debug_flag_defaults_to_off_and_can_be_enabled(gui_stubs):
    from main import parse_args

    assert parse_args([]).debug is False
    assert parse_args(["--debug"]).debug is True


def test_engine_exposes_finger_states_and_poses_for_the_overlay(engine, clock):
    play(engine, clock, make_hand("IM"), 2)
    info = engine.debug["Right"]
    assert info["fingers"] == [False, True, True, False, False]
    assert info["raw"] == "SCROLL" and info["stable"] == "SCROLL"
    assert info["gesture"] == "SCROLL" and info["primary"] is True


def test_overlay_prints_gesture_finger_states_and_fps(gui_stubs, engine, clock):
    from modules.config import Config
    from modules.ui_overlay import UIOverlay

    play(engine, clock, make_hand("IM"), 2)
    UIOverlay(Config()).draw_debug(
        np.zeros((720, 1280, 3), dtype=np.uint8), engine.debug, fps=29.5, avg_fps=30.0
    )
    texts = [call.args[1] for call in gui_stubs.cv2.putText.call_args_list]
    assert any("fps  29.5" in t for t in texts)
    assert any("gesture: SCROLL" in t for t in texts)
    assert any(t == "I:1" for t in texts) and any(t == "T:0" for t in texts)
