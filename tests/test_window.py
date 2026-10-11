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


# ── WindowFitter: no feedback loop, any window size ──────────────────────────

def _frame():
    return np.full((480, 640, 3), 200, dtype=np.uint8)


class FakeQt:
    """FREERATIO window: it stretches the image over the client area, so the rect is the window."""

    def __init__(self, w, h):
        self.w, self.h = w, h

    def rect(self):
        return (0, 0, self.w, self.h)


@pytest.mark.parametrize("w,h", [(960, 720), (960, 1010), (1920, 1010), (1920, 1080), (400, 300)])
def test_image_fills_the_height_or_width_in_every_window_size(w, h):
    pytest.importorskip("cv2")
    from modules.window import WindowFitter

    out = WindowFitter(FakeQt(w, h).rect).fit(_frame())
    assert out.shape == (h, w, 3)
    content = (out != BACKGROUND).any(axis=2)
    rows, cols = np.where(content.any(axis=1))[0], np.where(content.any(axis=0))[0]
    # touches both edges of one axis (full height or full width), aspect kept
    assert (rows.max() - rows.min() + 1 == h) or (cols.max() - cols.min() + 1 == w)
    assert (cols.max() - cols.min() + 1) / (rows.max() - rows.min() + 1) == pytest.approx(4 / 3, rel=0.02)


def test_repeated_fitting_converges_and_never_shrinks():
    """Feed the produced size back as the next rect (the old KEEPRATIO feedback loop)."""
    pytest.importorskip("cv2")
    from modules.window import WindowFitter

    rect = [0, 0, 960, 1010]
    fitter = WindowFitter(lambda: tuple(rect))
    sizes = []
    for _ in range(20):
        out = fitter.fit(_frame())
        sizes.append(out.shape[:2])
        rect[2], rect[3] = out.shape[1], out.shape[0]      # the rect "we produced"
    assert set(sizes) == {(1010, 960)}                    # stable from the first frame, no shrinking


def test_tiny_or_failed_rects_keep_the_last_good_size():
    pytest.importorskip("cv2")
    from modules.window import WindowFitter

    rect = [0, 0, 960, 720]

    def get():
        if rect[0] == -1:
            raise RuntimeError("no window")
        return tuple(rect)

    fitter = WindowFitter(get)
    assert fitter.fit(_frame()).shape[:2] == (720, 960)
    rect[2:] = [50, 40]                                   # transient tiny rect
    assert fitter.fit(_frame()).shape[:2] == (720, 960)
    rect[0] = -1                                          # query fails
    assert fitter.fit(_frame()).shape[:2] == (720, 960)


def test_before_any_good_rect_the_frame_is_shown_unchanged():
    from modules.window import WindowFitter

    frame = _frame()
    assert WindowFitter(lambda: (0, 0, 0, 0)).fit(frame) is frame
