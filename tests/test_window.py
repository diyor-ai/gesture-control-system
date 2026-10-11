"""Window sizing and dark letterboxing (real OpenCV, no window needed)."""

import numpy as np
import pytest

from modules.config import Config
from modules.window import BACKGROUND, letterbox, window_size


def test_window_size_scales_the_real_frame_size():
    assert window_size((480, 640, 3), 1.5) == (960, 720)
    assert window_size((720, 1280, 3), 0.5) == (640, 360)
    assert Config().WINDOW_SCALE == 1.5


def test_taller_window_gets_dark_bars_above_and_below_not_a_stretched_image():
    pytest.importorskip("cv2")
    frame = np.full((480, 640, 3), 200, dtype=np.uint8)
    out = letterbox(frame, 960, 900)                  # window taller than 4:3
    assert out.shape == (900, 960, 3)
    assert tuple(out[0, 0]) == BACKGROUND and tuple(out[-1, -1]) == BACKGROUND
    assert tuple(out[450, 480]) == (200, 200, 200)    # image in the middle
    rows = np.where((out != BACKGROUND).any(axis=(1, 2)))[0]
    assert (rows.max() - rows.min() + 1) == 720       # 960 wide -> 720 tall: 4:3 kept


def test_wider_window_gets_bars_left_and_right():
    pytest.importorskip("cv2")
    frame = np.full((480, 640, 3), 200, dtype=np.uint8)
    out = letterbox(frame, 1200, 720)
    cols = np.where((out != BACKGROUND).any(axis=(0, 2)))[0]
    assert (cols.max() - cols.min() + 1) == 960
    assert tuple(out[360, 0]) == BACKGROUND


def test_exact_fit_changes_nothing_but_size():
    pytest.importorskip("cv2")
    frame = np.full((480, 640, 3), 90, dtype=np.uint8)
    assert (letterbox(frame, 640, 480) == frame).all()


def test_invalid_window_size_returns_the_frame():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    assert letterbox(frame, 0, 0) is frame
