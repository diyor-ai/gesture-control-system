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


MIN_WINDOW_PX = 100             # smaller rects are transient (window being created or minimised)


class WindowFitter:
    """
    Letterbox each frame into the window's real client area.

    The window must use WINDOW_FREERATIO: Qt then stretches whatever image it
    gets over the whole client area, and `get_rect` (cv2.getWindowImageRect)
    returns the full window size.  Because the frame we hand over already has
    the window's aspect ratio, nothing is distorted, and the size we produce
    never feeds back into the size we measure.  Rects below MIN_WINDOW_PX are
    ignored and the last good size is kept.
    """

    def __init__(self, get_rect) -> None:
        self._get_rect = get_rect
        self._size = None                   # last good (width, height)

    def fit(self, frame: np.ndarray) -> np.ndarray:
        try:
            _, _, w, h = self._get_rect()
        except Exception:                   # cv2.error before the window exists
            w = h = 0
        if w >= MIN_WINDOW_PX and h >= MIN_WINDOW_PX:
            self._size = (int(w), int(h))
        if self._size is None:
            return frame
        return letterbox(frame, *self._size)
