"""
scroll_control.py – Scroll the active window using a two-finger gesture.

Gesture : Index + middle fingers extended (peace sign ✌).
Direction: Wrist Y velocity determines scroll up / down.
"""

import time
import numpy as np
import cv2
from modules.config import Config
from modules.hand_tracker import HandTracker
from modules.input_backend import PyAutoGUIBackend


class ScrollController:
    def __init__(self, cfg: Config, backend=None) -> None:
        self._cfg         = cfg
        self._input       = backend or PyAutoGUIBackend()
        self._prev_y      = None
        self._last_scroll = 0.0
        self._COOLDOWN    = 0.06   # seconds between scroll events
        self._DEADZONE    = 0.025  # palm lengths

    def reset(self) -> None:
        """Forget the previous wrist position (call when the gesture ends)."""
        self._prev_y = None

    def scroll(self, landmarks: list[tuple], frame: np.ndarray) -> None:
        """Scroll based on wrist Y-axis velocity."""
        now = time.time()
        if now - self._last_scroll < self._COOLDOWN:
            return

        wrist_y = landmarks[0][1]    # normalised 0–1

        if self._prev_y is not None:
            # Movement in palm lengths, so the same gesture scrolls the same
            # amount near and far from the camera. Positive → hand moved down.
            delta = (wrist_y - self._prev_y) / HandTracker.hand_scale(landmarks)
            if abs(delta) > self._DEADZONE:  # dead-zone to avoid jitter
                clicks = int(delta * 6)      # scale to scroll wheel clicks
                self._input.scroll(-clicks)  # negative = scroll down
                self._last_scroll = now
                # Feedback arrow
                arrow = "▼" if clicks > 0 else "▲"
                cx = int(landmarks[8][0] * frame.shape[1])
                cy = int(landmarks[8][1] * frame.shape[0])
                cv2.putText(frame, arrow, (cx, cy - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 180), 3)

        self._prev_y = wrist_y