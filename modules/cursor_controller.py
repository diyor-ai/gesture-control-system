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

import time
import numpy as np
from typing import Callable, List, Optional
from modules.config import Config
from modules.hand_tracker import HandTracker
from modules.input_backend import PyAutoGUIBackend



class CursorController:
    """Maps index-finger tip coordinates to screen cursor position."""

    def __init__(
        self,
        cfg: Config,
        backend=None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        debug: bool = False,
    ) -> None:
        self._cfg = cfg
        self._clock = clock
        self._sleep = sleep
        self._debug = debug
        self._locked_until = float("-inf")     # cursor frozen until this time (click lock)
        self._last_click_log = float("-inf")
        self._input = backend or PyAutoGUIBackend()
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

    def move(self, landmarks: List[tuple]) -> None:
        """
        Move the cursor to the position indicated by the index finger tip.
        Applies exponential moving average smoothing.
        """
        if self._clock() < self._locked_until:
            return          # click lock: opening the thumb shifts the index tip

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

        self._input.move_to(int(self._smooth_x), int(self._smooth_y))

    # Clicks happen where the cursor already is: moving to the fingertip here
    # would drag the pointer while the thumb closes in on the index finger.
    # Every click also locks the cursor for CLICK_LOCK_TIME: releasing the
    # pinch moves the index tip, and a second pinch must land on the same pixel.

    def _lock(self) -> None:
        self._locked_until = self._clock() + self._cfg.CLICK_LOCK_TIME

    def _log(self, kind: str) -> None:
        """--debug only: one line per click sent (time, gap since previous, cursor)."""
        if not self._debug:
            return
        now = self._clock()
        gap = now - self._last_click_log
        self._last_click_log = now
        gap_s = "   -  " if gap == float("inf") else f"{gap:6.3f}"
        print(f"[click] t={now:10.3f}  +{gap_s}s  {kind:<12} x={int(self._smooth_x)} y={int(self._smooth_y)}")

    def click(self, landmarks: List[tuple]) -> None:
        """Perform a single left-click at the current cursor position."""
        self._lock()
        self._input.click()
        self._log("CLICK")

    def double_click(self, landmarks: List[tuple]) -> None:
        """
        Complete a double click.  The first pinch of the pair already sent a
        click.  A human double-pinch is slower than the OS double-click time
        (about 0.4 s on GNOME), so two pinches alone would not register as a
        double click.  So we send two clicks FAST_DOUBLE_CLICK_GAP (~50 ms)
        apart: that is always inside the OS time, and the click lock keeps the
        pointer on the pixel of the first pinch.

        Why this is safe: the clicks land where the user already clicked, so
        the worst case is one extra click on the same target (the OS sees the
        first pinch's click, then a double click).  pyautogui.doubleClick()
        stays avoided so the backends need no new API.
        """
        self._lock()
        self._input.click()
        self._log("DOUBLE_CLICK 1/2")
        self._sleep(self._cfg.FAST_DOUBLE_CLICK_GAP)
        self._input.click()
        self._log("DOUBLE_CLICK 2/2")

    def right_click(self, landmarks: List[tuple]) -> None:
        """Perform a right-click at the current cursor position."""
        self._lock()
        self._input.right_click()
        self._log("RIGHT_CLICK")

    def on_hand_lost(self) -> None:
        """
        Called when no hand is detected.
        The cursor freezes at its last position – no jarring snap.
        """
        # Nothing to do; smooth_x / smooth_y retain their last values.
        pass