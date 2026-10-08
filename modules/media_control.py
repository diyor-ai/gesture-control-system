"""
media_control.py – Play/Pause and track navigation via gestures.

Sends media keys through the active input backend (works on Windows/macOS/Linux with
compatible media players: Spotify, VLC, YouTube, etc.).
"""

import time
from modules.config import Config
from modules.input_backend import PyAutoGUIBackend


class MediaController:
    def __init__(self, cfg: Config, backend=None) -> None:
        self._cfg  = cfg
        self._input = backend or PyAutoGUIBackend()
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
            self._input.press_media(key)
            print(f"[Media] {key}")
        except Exception as e:
            print(f"[Media] Key '{key}' failed: {e}")