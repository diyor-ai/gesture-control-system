"""
volume_control.py – System volume control via hand gesture.

Gesture: thumb + pinky spread (🤙 shape).
The distance between thumb tip and pinky tip maps to system volume 0–100 %.

Cross-platform strategy
-----------------------
* Windows  : pycaw  (Core Audio Wrapper)
* Linux    : amixer / pactl via subprocess
* macOS    : osascript via subprocess
"""

import platform
import subprocess
import numpy as np
import cv2
from modules.config import Config
from modules.hand_tracker import HandTracker


class VolumeController:
    """Maps thumb–pinky spread distance to system volume level."""

    def __init__(self, cfg: Config) -> None:
        self._cfg      = cfg
        self._platform = platform.system()
        self._volume   = 0.5   # cached normalised volume (0–1)

        # Windows: set up pycaw if available
        self._win_vol_ctrl = None
        if self._platform == "Windows":
            try:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self._win_vol_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
            except ImportError:
                pass  # pycaw not installed – fall back to subprocess

    # ── Public API ─────────────────────────────────────────────────────────────

    def adjust(self, landmarks: list[tuple], frame: np.ndarray) -> None:
        """
        Read thumb–pinky distance and set system volume accordingly.
        Also draws a real-time volume bar on the frame.
        """
        thumb_tip = landmarks[4]
        pinky_tip = landmarks[20]

        d = HandTracker.distance(thumb_tip, pinky_tip)

        # Normalise distance to 0–1
        vol_norm = np.interp(
            d,
            [self._cfg.VOLUME_MIN_DIST, self._cfg.VOLUME_MAX_DIST],
            [0.0, 1.0],
        )
        vol_norm = float(np.clip(vol_norm, 0.0, 1.0))
        self._volume = vol_norm

        self._set_system_volume(vol_norm)
        self._draw_bar(frame, vol_norm, label="VOL")

    # ── Private helpers ────────────────────────────────────────────────────────

    def _set_system_volume(self, vol_norm: float) -> None:
        """Set system volume to vol_norm (0.0–1.0), cross-platform."""
        if self._platform == "Windows" and self._win_vol_ctrl:
            # pycaw: set scalar volume directly
            self._win_vol_ctrl.SetMasterVolumeLevelScalar(vol_norm, None)
        elif self._platform == "Linux":
            pct = int(vol_norm * 100)
            try:
                subprocess.run(
                    ["amixer", "-D", "pulse", "sset", "Master", f"{pct}%"],
                    capture_output=True, check=False,
                )
            except FileNotFoundError:
                pass  # amixer not available
        elif self._platform == "Darwin":
            pct = int(vol_norm * 100)
            subprocess.run(
                ["osascript", "-e", f"set volume output volume {pct}"],
                capture_output=True, check=False,
            )

    def _draw_bar(
        self,
        frame: np.ndarray,
        value: float,
        label: str,
        x: int = 50,
        bar_h: int = 200,
        bar_w: int = 25,
    ) -> None:
        """Render a vertical progress bar on the frame."""
        h = frame.shape[0]
        top    = h // 2 - bar_h // 2
        bottom = top + bar_h
        fill_y = int(bottom - value * bar_h)

        # Background
        cv2.rectangle(frame, (x, top), (x + bar_w, bottom), (50, 50, 50), -1)
        # Fill
        cv2.rectangle(frame, (x, fill_y), (x + bar_w, bottom), (0, 255, 180), -1)
        # Border
        cv2.rectangle(frame, (x, top), (x + bar_w, bottom), (200, 200, 200), 1)
        # Label
        cv2.putText(
            frame, f"{label}: {int(value * 100)}%",
            (x - 5, top - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1,
        )