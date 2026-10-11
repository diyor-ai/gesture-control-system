"""
scroll_control.py – Joystick-style scrolling with a two-finger gesture.

Gesture  : Index + middle fingers extended (peace sign ✌).
Direction: The wrist height when the gesture starts is the anchor.  Holding
           the hand below it scrolls down, above it scrolls up; the further
           from the anchor (outside a dead zone), the faster.  Moving back
           towards the anchor only slows or stops the scrolling.
           The anchor survives short pose dropouts (SCROLL_ANCHOR_GRACE), so a
           hand that wanders to the edge of tracking does not get a new anchor
           out there.
"""

import time
from typing import Callable
import numpy as np
import cv2
from modules.config import Config
from modules.hand_tracker import HandTracker
from modules.input_backend import PyAutoGUIBackend

_UNITS_PER_NOTCH = 120          # REL_WHEEL_HI_RES units in one wheel notch
_LOG_INTERVAL = 0.2             # --debug: at most ~5 [scroll] lines per second


class ScrollController:
    def __init__(
        self,
        cfg: Config,
        backend=None,
        clock: Callable[[], float] = time.monotonic,
        debug: bool = False,
    ) -> None:
        self._cfg      = cfg
        self._input    = backend or PyAutoGUIBackend()
        self._clock    = clock
        self._debug    = debug
        self._anchor   = None       # wrist Y (normalised) when the gesture started
        self._last_t   = None
        self._absent_since = None   # when the SCROLL pose was last lost (None = present)
        self._residual = 0.0        # hi-res units not yet sent (sub-unit remainder)
        self._last_log = float("-inf")
        self._sent_since_log = 0
        self._resets_since_log = 0

    def reset(self) -> None:
        """Forget the anchor immediately."""
        if self._anchor is not None and self._debug:
            print("[scroll] anchor reset")
        if self._anchor is not None:
            self._resets_since_log += 1
        self._anchor   = None
        self._last_t   = None
        self._absent_since = None
        self._residual = 0.0

    def pose_absent(self) -> None:
        """
        Call every frame the SCROLL pose is not active.  The anchor is kept
        through short dropouts and forgotten once the pose has been absent for
        SCROLL_ANCHOR_GRACE.  Nothing is sent while the pose is absent.
        """
        if self._anchor is None:
            return
        now = self._clock()
        if self._absent_since is None:
            self._absent_since = now
        elif now - self._absent_since >= self._cfg.SCROLL_ANCHOR_GRACE:
            self.reset()

    # ── Maths (pure, unit-tested) ─────────────────────────────────────────────

    def speed(self, offset: float) -> float:
        """Scroll speed in notches/second for a signed offset in palm lengths (positive = down)."""
        span = max(self._cfg.SCROLL_FULL_SPEED_OFFSET - self._cfg.SCROLL_DEADZONE, 1e-6)
        beyond = abs(offset) - self._cfg.SCROLL_DEADZONE
        if beyond <= 0:
            return 0.0
        fraction = min(beyond / span, 1.0)              # clamped at the full-speed point
        return self._cfg.SCROLL_MAX_SPEED * fraction ** self._cfg.SCROLL_EXPONENT

    # ── Per-frame update ──────────────────────────────────────────────────────

    def scroll(self, landmarks: list, frame: np.ndarray) -> None:
        now = self._clock()
        wrist_y = landmarks[0][1]                       # normalised 0–1
        scale = HandTracker.hand_scale(landmarks)

        if self._anchor is None:
            self._anchor, self._last_t = wrist_y, now
            if self._debug:
                print(f"[scroll] anchor set (y={wrist_y:.3f})")
            self._draw(frame, scale, 0.0)
            return

        if self._absent_since is not None:              # pose is back inside the grace period
            self._absent_since = None
            self._last_t = now                          # no catch-up for the time it was missing
            self._residual = 0.0

        dt = min(max(now - self._last_t, 0.0), self._cfg.SCROLL_MAX_DT)   # real time, not frames
        self._last_t = now

        # Palm lengths, so the same gesture works near and far. Positive = below the anchor.
        offset = (wrist_y - self._anchor) / scale
        speed = self.speed(offset)
        direction = -1 if offset > 0 else 1             # wheel: negative = down
        if self._cfg.SCROLL_NATURAL:
            direction = -direction

        self._residual += direction * speed * _UNITS_PER_NOTCH * dt
        units = int(self._residual)                     # truncates toward zero; remainder is kept
        self._residual -= units
        if units:
            self._input.scroll_hi_res(units)
            self._sent_since_log += units

        self._log(now, offset, speed)
        self._draw(frame, scale, offset, scrolling=speed > 0, down=offset > 0)

    # ── Feedback ──────────────────────────────────────────────────────────────

    def _log(self, now: float, offset: float, speed: float) -> None:
        if not self._debug or now - self._last_log < _LOG_INTERVAL:
            return
        self._last_log = now
        print(f"[scroll] offset={offset:+.2f} palm  speed={speed:5.1f} notch/s  "
              f"units_since_last_line={self._sent_since_log:+d}  anchor_resets={self._resets_since_log}")
        self._sent_since_log = 0
        self._resets_since_log = 0

    def _draw(self, frame: np.ndarray, scale: float, offset: float,
              scrolling: bool = False, down: bool = False) -> None:
        """Anchor line, dead-zone band and (only while scrolling) a direction arrow."""
        h, w = frame.shape[:2]
        y = int(self._anchor * h)
        band = int(self._cfg.SCROLL_DEADZONE * scale * h)

        shade = frame.copy()
        cv2.rectangle(shade, (0, y - band), (w, y + band), (255, 200, 0), -1)
        cv2.addWeighted(shade, 0.25, frame, 0.75, 0, frame)
        cv2.line(frame, (0, y), (w, y), (255, 200, 0), 1)

        if scrolling:
            cx, tip = w - 60, y + (90 if down else -90)
            pts = np.array([[cx - 25, y + (40 if down else -40)],
                            [cx + 25, y + (40 if down else -40)],
                            [cx, tip]], dtype=np.int32)
            cv2.fillPoly(frame, [pts], (0, 255, 180))
