"""
brightness_control.py – Screen brightness control via gesture.

Gesture : Thumb + ring finger spread.
Distance maps to brightness 0–100 % (cross-platform).

* Windows : screen_brightness_control library
* Linux   : xrandr via subprocess (or brightnessctl)
* macOS   : osascript
"""

import platform
import subprocess
import numpy as np
import cv2
from modules.config import Config
from modules.hand_tracker import HandTracker


class BrightnessController:
    def __init__(self, cfg: Config) -> None:
        self._cfg      = cfg
        self._platform = platform.system()
        self._level    = 0.5   # cached 0–1

    def adjust(self, landmarks: list[tuple], frame: np.ndarray) -> None:
        """Map thumb–ring distance to screen brightness."""
        d = HandTracker.distance(landmarks[4], landmarks[16])

        bri = float(np.clip(np.interp(
            d,
            [self._cfg.BRIGHTNESS_MIN_DIST, self._cfg.BRIGHTNESS_MAX_DIST],
            [0.0, 1.0],
        ), 0.0, 1.0))

        self._level = bri
        self._set_brightness(bri)

        # Reuse volume bar renderer
        h = frame.shape[0]
        bar_h = 200
        x, top = frame.shape[1] - 80, h // 2 - bar_h // 2
        bottom = top + bar_h
        fill_y = int(bottom - bri * bar_h)
        cv2.rectangle(frame, (x, top), (x + 25, bottom), (50, 50, 50), -1)
        cv2.rectangle(frame, (x, fill_y), (x + 25, bottom), (255, 220, 0), -1)
        cv2.rectangle(frame, (x, top), (x + 25, bottom), (200, 200, 200), 1)
        cv2.putText(frame, f"BRI: {int(bri * 100)}%",
                    (x - 10, top - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (255, 255, 255), 1)

    def _set_brightness(self, bri: float) -> None:
        pct = int(bri * 100)
        if self._platform == "Windows":
            try:
                import screen_brightness_control as sbc  # type: ignore
                sbc.set_brightness(pct)
            except ImportError:
                pass
        elif self._platform == "Linux":
            try:
                subprocess.run(
                    ["xrandr", "--output", "eDP-1", "--brightness", f"{bri:.2f}"],
                    capture_output=True, check=False,
                )
            except FileNotFoundError:
                pass
        elif self._platform == "Darwin":
            # AppleScript brightness: 0.0–1.0
            subprocess.run(
                ["osascript", "-e", f"tell application \"System Events\" to set brightness to {bri:.2f}"],
                capture_output=True, check=False,
            )