"""
cursor_controller.py – Translates hand landmark positions into
smooth, responsive mouse cursor movements and click actions.

Features
--------
* Exponential moving average smoothing to eliminate jitter
* Configurable control zone (avoid edge dead-zones)
* Single click, double click, and right-click support
* Hand-loss recovery (cursor freezes rather than snapping to 0,0)
"""

import pyautogui
import numpy as np
from modules.config import Config
from modules.hand_tracker import HandTracker


# Disable PyAutoGUI's built-in pause between actions and fail-safe
pyautogui.PAUSE     = 0
pyautogui.FAILSAFE  = False


class CursorController:
    """Maps index-finger tip coordinates to screen cursor position."""

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._sw  = cfg.SCREEN_W
        self._sh  = cfg.SCREEN_H
        self._fw  = cfg.FRAME_WIDTH
        self._fh  = cfg.FRAME_HEIGHT

        # Smoothed screen position
        self._smooth_x: float = self._sw / 2
        self._smooth_y: float = self._sh / 2

        # Control zone boundaries (normalised, 0–1)
        m = cfg.CONTROL_ZONE_MARGIN
        self._zone_x_min = m
        self._zone_x_max = 1 - m
        self._zone_y_min = m
        self._zone_y_max = 1 - m

        self._alpha = cfg.SMOOTHING_FACTOR  # EMA weight (higher → more responsive)

    # ── Public API ─────────────────────────────────────────────────────────────

    def move(self, landmarks: list[tuple]) -> None:
        """
        Move the cursor to the position indicated by the index finger tip.
        Applies exponential moving average smoothing.
        """
        tip_x, tip_y = landmarks[8][:2]   # index finger tip (normalised)

        # Clamp to control zone
        cx = np.clip(tip_x, self._zone_x_min, self._zone_x_max)
        cy = np.clip(tip_y, self._zone_y_min, self._zone_y_max)

        # Re-map from control zone to 0–1
        nx = (cx - self._zone_x_min) / (self._zone_x_max - self._zone_x_min)
        ny = (cy - self._zone_y_min) / (self._zone_y_max - self._zone_y_min)

        # Convert to screen pixels
        target_x = nx * self._sw
        target_y = ny * self._sh

        # Exponential moving average
        self._smooth_x = self._alpha * target_x + (1 - self._alpha) * self._smooth_x
        self._smooth_y = self._alpha * target_y + (1 - self._alpha) * self._smooth_y

        pyautogui.moveTo(int(self._smooth_x), int(self._smooth_y))

    def click(self, landmarks: list[tuple]) -> None:
        """Perform a single left-click at the current cursor position."""
        self.move(landmarks)
        pyautogui.click()

    def double_click(self, landmarks: list[tuple]) -> None:
        """Perform a double left-click at the current cursor position."""
        self.move(landmarks)
        pyautogui.doubleClick()

    def right_click(self, landmarks: list[tuple]) -> None:
        """Perform a right-click at the current cursor position."""
        self.move(landmarks)
        pyautogui.rightClick()

    def on_hand_lost(self) -> None:
        """
        Called when no hand is detected.
        The cursor freezes at its last position – no jarring snap.
        """
        # Nothing to do; smooth_x / smooth_y retain their last values.
        pass