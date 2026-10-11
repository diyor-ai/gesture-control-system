"""Privacy mode: blurred camera image, PRIVACY in the top bar, off by default."""

import numpy as np
import pytest

from modules.config import Config


def test_privacy_is_off_by_default():
    assert Config().PRIVACY_START is False


def test_blur_destroys_detail_but_keeps_the_frame_shape():
    cv2 = pytest.importorskip("cv2")
    rng = np.random.default_rng(0)
    frame = rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)      # maximum detail
    from modules.privacy import blur_frame

    out = blur_frame(frame, 16)
    assert out.shape == frame.shape and out.dtype == frame.dtype
    assert out.std() < frame.std() / 5                               # detail is gone
    assert frame.std() > 50                                          # input was not modified
    assert cv2 is not None


def test_hud_shows_privacy_only_when_enabled(gui_stubs):
    from modules.ui_overlay import UIOverlay

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    overlay = UIOverlay(Config())

    overlay.draw_hud(frame, 30.0, "IDLE")
    texts = [c.args[1] for c in gui_stubs.cv2.putText.call_args_list]
    assert "PRIVACY" not in texts

    gui_stubs.cv2.putText.reset_mock()
    overlay.draw_hud(frame, 30.0, "IDLE", privacy=True)
    texts = [c.args[1] for c in gui_stubs.cv2.putText.call_args_list]
    assert "PRIVACY" in texts
