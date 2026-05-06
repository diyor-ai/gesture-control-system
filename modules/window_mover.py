"""
window_mover.py – Drag the active window using a closed-fist gesture.

Gesture : Closed fist (all fingers curled).
Moves   : The foreground window by tracking fist displacement.
"""

import platform
import pyautogui
import numpy as np
from modules.config import Config

pyautogui.PAUSE = 0


class WindowMover:
    def __init__(self, cfg: Config) -> None:
        self._cfg      = cfg
        self._sw       = cfg.SCREEN_W
        self._sh       = cfg.SCREEN_H
        self._prev_pos = None   # (screen_x, screen_y) of fist centre last frame

    def drag(self, landmarks: list[tuple]) -> None:
        """Move the active window based on fist centre displacement."""
        # Use wrist as the anchor point for the fist
        wx = landmarks[0][0] * self._sw
        wy = landmarks[0][1] * self._sh

        if self._prev_pos is not None:
            dx = int(wx - self._prev_pos[0])
            dy = int(wy - self._prev_pos[1])
            if abs(dx) > 1 or abs(dy) > 1:
                self._move_active_window(dx, dy)

        self._prev_pos = (wx, wy)

    def on_hand_lost(self) -> None:
        self._prev_pos = None

    # ── Platform-specific window move ─────────────────────────────────────────

    def _move_active_window(self, dx: int, dy: int) -> None:
        system = platform.system()
        if system == "Windows":
            self._move_windows(dx, dy)
        elif system == "Darwin":
            self._move_macos(dx, dy)
        # Linux: would use wmctrl; skipped for brevity

    def _move_windows(self, dx: int, dy: int) -> None:
        try:
            import win32gui, win32con  # type: ignore
            hwnd = win32gui.GetForegroundWindow()
            rect = win32gui.GetWindowRect(hwnd)
            x, y = rect[0] + dx, rect[1] + dy
            w, h = rect[2] - rect[0], rect[3] - rect[1]
            win32gui.MoveWindow(hwnd, x, y, w, h, True)
        except ImportError:
            pass

    def _move_macos(self, dx: int, dy: int) -> None:
        try:
            import subprocess
            # Uses AppleScript – moves frontmost window
            script = f"""
            tell application "System Events"
                set pos to position of front window of (first process whose frontmost is true)
                set front window of (first process whose frontmost is true) position to {{(item 1 of pos) + {dx}, (item 2 of pos) + {dy}}}
            end tell
            """
            subprocess.run(["osascript", "-e", script], capture_output=True)
        except Exception:
            pass