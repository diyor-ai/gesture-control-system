"""
window.py – Keep the camera image undistorted and the window background dark.

The OpenCV Qt window is white where the image does not fill it.  Instead of
relying on its letterboxing, the frame is scaled to fit the current window and
padded with a dark colour before it is shown.
"""

from typing import Tuple
import numpy as np

BACKGROUND = (20, 20, 20)       # BGR, matches the HUD bar


def window_size(frame_shape: Tuple[int, ...], scale: float) -> Tuple[int, int]:
    """Initial window size (width, height) for a frame, e.g. 640x480 at 1.5 -> 960x720."""
    h, w = frame_shape[:2]
    return max(int(round(w * scale)), 1), max(int(round(h * scale)), 1)


def letterbox(frame: np.ndarray, width: int, height: int, color=BACKGROUND) -> np.ndarray:
    """Scale `frame` to fit width x height keeping its aspect ratio; pad the rest with `color`."""
    import cv2

    h, w = frame.shape[:2]
    if width <= 0 or height <= 0:
        return frame
    ratio = min(width / w, height / h)
    new_w, new_h = max(int(round(w * ratio)), 1), max(int(round(h * ratio)), 1)
    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    canvas = np.empty((height, width, 3), dtype=frame.dtype)
    canvas[:] = color
    x, y = (width - new_w) // 2, (height - new_h) // 2
    canvas[y:y + new_h, x:x + new_w] = resized
    return canvas
