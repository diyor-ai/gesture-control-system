"""
zoom_control.py – Pinch-to-zoom using Ctrl + scroll wheel simulation.

Gesture : Thumb + index finger spread / pinched.
Maps pinch distance change to Ctrl+scroll, which triggers zoom in most apps.
"""

import numpy as np
import cv2
from modules.config import Config
from modules.hand_tracker import HandTracker
from modules.input_backend import PyAutoGUIBackend


class ZoomController:
    def __init__(self, cfg: Config, backend=None) -> None:
        self._cfg      = cfg
        self._input    = backend or PyAutoGUIBackend()
        self._prev_d   = None
        self._DEADZONE = 0.025   # palm lengths

    def reset(self) -> None:
        """Forget the previous pinch distance (call when the gesture ends)."""
        self._prev_d = None

    def pinch_zoom(self, landmarks: list[tuple], frame: np.ndarray) -> None:
        """Detect pinch spread/pinch and simulate Ctrl+scroll."""
        d = HandTracker.normalized_distance(landmarks, 4, 8)   # palm lengths

        if self._prev_d is not None:
            delta = d - self._prev_d
            if abs(delta) > self._DEADZONE:
                clicks = int(delta * 6)
                self._input.ctrl_scroll(clicks)

                # Visual feedback
                label = "ZOOM IN" if clicks > 0 else "ZOOM OUT"
                cv2.putText(frame, label,
                            (frame.shape[1] // 2 - 60, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 200), 2)

        self._prev_d = d