"""
privacy.py – Blur the camera image for demos so the face is unrecognisable.

Hand detection runs on the sharp frame first; only the picture that is shown
(with the skeleton and HUD drawn on top afterwards) is blurred.
"""

import numpy as np


def blur_frame(frame: np.ndarray, downscale: int = 16) -> np.ndarray:
    """Return a heavily blurred copy: shrink, upscale smoothly, then Gaussian blur."""
    import cv2

    h, w = frame.shape[:2]
    factor = max(int(downscale), 1)
    small = cv2.resize(frame, (max(w // factor, 1), max(h // factor, 1)), interpolation=cv2.INTER_AREA)
    big = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(big, (31, 31), 0)
