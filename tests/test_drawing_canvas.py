"""The canvas must follow the real camera frame size, not the requested one."""

import numpy as np
import pytest

from modules.config import Config
from tests.conftest import make_hand


@pytest.fixture
def cv2_real():
    # the canvas uses real OpenCV drawing; skip where it is not installed
    return pytest.importorskip("cv2")


def test_draws_and_renders_when_camera_ignores_requested_resolution(cv2_real):
    from modules.drawing_canvas import DrawingCanvas

    cfg = Config()                                  # asks for 1280x720 ...
    canvas = DrawingCanvas(cfg)
    canvas.toggle()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)  # ... but the camera delivers 640x480

    for x in (0.40, 0.45, 0.50):
        canvas.draw(make_hand("I", wrist_x=x), frame)
    out = canvas.render(frame)

    assert out.shape == frame.shape
    assert out.any()                                # the stroke is visible
