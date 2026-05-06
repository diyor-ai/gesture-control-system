"""
drawing_canvas.py – Finger drawing / virtual canvas.

Gesture : Index finger only, middle curled (no click pinch).
Toggle  : Press 'd' key.
Clear   : Press 'r' key.
"""

import numpy as np
import cv2
from modules.config import Config


class DrawingCanvas:
    def __init__(self, cfg: Config) -> None:
        self._cfg     = cfg
        self._enabled = False
        self._canvas  = np.zeros((cfg.FRAME_HEIGHT, cfg.FRAME_WIDTH, 3), dtype=np.uint8)
        self._prev_pt = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def toggle(self) -> None:
        self._enabled = not self._enabled
        if not self._enabled:
            self._prev_pt = None
        print(f"[Canvas] {'Enabled' if self._enabled else 'Disabled'}")

    def clear(self) -> None:
        self._canvas[:] = 0
        self._prev_pt   = None
        print("[Canvas] Cleared")

    def draw(self, landmarks: list[tuple], frame: np.ndarray) -> None:
        """Draw a line from the previous to the current index-finger-tip position."""
        if not self._enabled:
            return

        h, w = frame.shape[:2]
        ix = int(landmarks[8][0] * w)
        iy = int(landmarks[8][1] * h)

        if self._prev_pt:
            cv2.line(
                self._canvas,
                self._prev_pt,
                (ix, iy),
                self._cfg.DRAW_COLOR,
                self._cfg.DRAW_THICKNESS,
            )
        # Draw a filled circle at the tip for smooth caps
        cv2.circle(self._canvas, (ix, iy), self._cfg.DRAW_THICKNESS // 2,
                   self._cfg.DRAW_COLOR, -1)
        self._prev_pt = (ix, iy)

    def on_hand_lost(self) -> None:
        self._prev_pt = None

    def render(self, frame: np.ndarray) -> np.ndarray:
        """Blend the canvas layer onto the camera frame."""
        if not np.any(self._canvas):
            return frame
        # Wherever the canvas has non-zero pixels, overlay them
        mask = cv2.cvtColor(self._canvas, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)
        frame_bg = cv2.bitwise_and(frame, frame, mask=cv2.bitwise_not(mask))
        return cv2.add(frame_bg, self._canvas)