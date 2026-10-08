"""
Manual check of the uinput backend.  RUN THIS YOURSELF – it moves your
real mouse pointer.  It sends pointer movement only: no clicks, no scrolling,
no key presses.

    python tools/uinput_selftest.py

It asks for confirmation first, draws a small square around the screen centre
and leaves the pointer at the centre.  Press Ctrl+C at any time to stop.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.config import Config                      # noqa: E402
from modules.input_backend import InputBackendError, UInputBackend   # noqa: E402


def main() -> int:
    cfg = Config()
    print(f"Detected screen size: {cfg.SCREEN_W}x{cfg.SCREEN_H}")
    print("This will MOVE YOUR MOUSE POINTER around the screen centre (no clicks).")
    if input("Type 'yes' to continue: ").strip().lower() != "yes":
        print("Aborted.")
        return 1

    try:
        backend = UInputBackend(cfg.SCREEN_W, cfg.SCREEN_H)
    except InputBackendError as exc:
        print(f"[FAIL] {exc}")
        return 2

    cx, cy, r = cfg.SCREEN_W // 2, cfg.SCREEN_H // 2, 150
    time.sleep(0.5)                       # let the compositor pick up the new device
    path = [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r), (cx - r, cy - r), (cx, cy)]
    for x, y in path:
        for step in range(1, 21):
            prev = path[path.index((x, y)) - 1] if path.index((x, y)) else (cx, cy)
            backend.move_to(prev[0] + (x - prev[0]) * step // 20, prev[1] + (y - prev[1]) * step // 20)
            time.sleep(0.01)
    backend.close()
    print("Done. If the pointer drew a square and ended in the middle, absolute positioning works.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
