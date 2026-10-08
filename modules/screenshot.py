"""
screenshot.py – Capture a full-screen screenshot via gesture.

Gesture : All five fingers spread wide, held ≥ SCREENSHOT_HOLD_TIME seconds.
Saves PNG to ./screenshots/ with a timestamp filename.
"""

import os
import time
import cv2
import numpy as np
from modules.config import Config
from modules.input_backend import PyAutoGUIBackend


class ScreenshotModule:
    def __init__(self, cfg: Config, backend=None) -> None:
        self._cfg      = cfg
        self._input    = backend or PyAutoGUIBackend()
        self._save_dir = cfg.SCREENSHOT_SAVE_DIR
        os.makedirs(self._save_dir, exist_ok=True)
        self._last_capture = 0.0
        self._COOLDOWN     = cfg.SCREENSHOT_COOLDOWN

    def capture(self, frame: np.ndarray) -> None:
        """Take a screenshot and save it. Debounced by COOLDOWN."""
        now = time.time()
        if now - self._last_capture < self._COOLDOWN:
            print(f"[INFO] Screenshot ignored (cooldown, {now - self._last_capture:.1f}s since last)")
            return

        self._last_capture = now
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self._save_dir, f"screenshot_{timestamp}.png")

        if not self._input.screenshot(path):
            print("[Screenshot] Failed – on GNOME/Wayland install gnome-screenshot "
                  "(sudo dnf install gnome-screenshot)")
            return
        folder = getattr(self._input, "screenshot_location", None)
        if folder:
            print(f"[Screenshot] Taken with the GNOME shortcut → saved in {folder}")
        else:
            print(f"[Screenshot] Saved → {path}")

        # Flash white on the camera frame as confirmation
        white = np.ones_like(frame, dtype=np.uint8) * 255
        frame[:] = cv2.addWeighted(frame, 0.3, white, 0.7, 0)