"""
media_control.py – Play/Pause and track navigation via gestures.

Uses PyAutoGUI to send media keys (works on Windows/macOS/Linux with
compatible media players: Spotify, VLC, YouTube, etc.).
"""

import time
import pyautogui
from modules.config import Config

pyautogui.PAUSE = 0


class MediaController:
    def __init__(self, cfg: Config) -> None:
        self._cfg  = cfg
        self._last = 0.0

    def toggle_play_pause(self) -> None:
        """Send the Play/Pause media key."""
        self._send("playpause")

    def next_track(self) -> None:
        """Send the Next Track media key."""
        self._send("nexttrack")

    def prev_track(self) -> None:
        """Send the Previous Track media key."""
        self._send("prevtrack")

    def _send(self, key: str) -> None:
        now = time.time()
        if now - self._last < self._cfg.MEDIA_COOLDOWN:
            return
        self._last = now
        try:
            pyautogui.press(key)
            print(f"[Media] {key}")
        except Exception as e:
            print(f"[Media] Key '{key}' failed: {e}")