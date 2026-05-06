from __future__ import annotations
from __future__ import annotations
"""
gesture_engine.py – Core gesture classification module.

Maps raw MediaPipe landmarks to named gestures consumed by other modules.
Each gesture maps to exactly one action string returned by classify().

Supported gestures
------------------
MOVE_CURSOR     – Index finger up, others down
CLICK           – Index + Thumb pinch
DOUBLE_CLICK    – Two rapid pinches
RIGHT_CLICK     – Middle + Thumb pinch
SCROLL          – Two-finger (index + middle) up together, wrist leads direction
VOLUME          – Thumb + Pinky spread (like a phone hand 🤙)
DRAW            – Index up, middle curled, index–middle gap < threshold (draw mode)
SCREENSHOT      – All five fingers spread wide, held for 1 s
DRAG_WINDOW     – Closed fist (all fingers curled)
ZOOM            – Index + Thumb spread (pinch gesture)
MEDIA_PLAY_PAUSE– Flat palm facing camera
MEDIA_NEXT      – Swipe right (index extended, wrist moving right)
MEDIA_PREV      – Swipe left  (index extended, wrist moving left)
BRIGHTNESS      – Ring + Thumb spread
"""
import time
import numpy as np
from modules.config import Config
from modules.hand_tracker import HandTracker


class GestureEngine:
    """
    Stateful gesture classifier.  Maintains per-session history for
    gestures that require timing (double-click, screenshot hold, swipe).
    """

    def __init__(self, cfg: Config) -> None:
        self._cfg         = cfg
        self.active_mode  = "IDLE"

        # ── Timing / state ─────────────────────────────────────────────────
        self._last_click_time   = 0.0
        self._last_gesture      = ""
        self._screenshot_start  = 0.0
        self._screenshot_fired  = False

        # Wrist position history for swipe detection
        self._wrist_history: list[float] = []
        self._SWIPE_HISTORY = 6
        self._SWIPE_DELTA   = 0.06

        # Media action cooldown
        self._last_media_action_time = 0.0

    # ── Public API ─────────────────────────────────────────────────────────────

    def classify(self, landmarks: list[tuple], hand_label: str) -> str:
        """
        Classify the current hand pose and return a gesture string.

        Parameters
        ----------
        landmarks  : 21 normalised (x, y, z) tuples from MediaPipe
        hand_label : "Left" or "Right"

        Returns
        -------
        gesture string, e.g. "CLICK", "SCROLL", "IDLE"
        """
        fingers = HandTracker.fingers_up(landmarks)
        dist    = HandTracker.distance

        thumb, index, middle, ring, pinky = fingers
        n_up = sum(fingers)

        thumb_tip  = landmarks[4]
        index_tip  = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip   = landmarks[16]
        pinky_tip  = landmarks[20]
        wrist      = landmarks[0]

        # ── Gesture rules (checked in priority order) ──────────────────────

        # 1. Screenshot – all 5 fingers extended, held ≥ SCREENSHOT_HOLD_TIME
        if n_up == 5:
            gesture = self._handle_screenshot()
            if gesture:
                self.active_mode = gesture
                return gesture
            self.active_mode = "SCREENSHOT_HOLD"
            return "IDLE"

        self._screenshot_start = 0.0
        self._screenshot_fired = False

        # 2. Fist → drag window
        if n_up == 0:
            self.active_mode = "DRAG_WINDOW"
            return "DRAG_WINDOW"

        # 3. Flat palm (4 fingers + thumb) → Media Play/Pause
        if n_up == 5:
            self.active_mode = "MEDIA_PLAY_PAUSE"
            return "MEDIA_PLAY_PAUSE"

        # 4. Volume: thumb + pinky up, others down (🤙 shape)
        if thumb and not index and not middle and not ring and pinky:
            self.active_mode = "VOLUME"
            return "VOLUME"

        # 5. Brightness: thumb + ring up, others down
        if thumb and not index and not middle and ring and not pinky:
            self.active_mode = "BRIGHTNESS"
            return "BRIGHTNESS"

        # 6. Zoom: thumb + index only (classic pinch spread)
        if thumb and index and not middle and not ring and not pinky:
            d = dist(thumb_tip, index_tip)
            if d > self._cfg.ZOOM_THRESHOLD:
                self.active_mode = "ZOOM"
                return "ZOOM"

        # 7. Click: index up, middle curled, thumb approaching index tip
        if index and not middle and not ring and not pinky:
            d_click = dist(thumb_tip, index_tip)
            if d_click < self._cfg.CLICK_THRESHOLD:
                gesture = self._handle_click()
                self.active_mode = gesture
                return gesture

        # 8. Right-click: middle up, thumb approaching middle tip
        if not index and middle and not ring and not pinky:
            d_right = dist(thumb_tip, middle_tip)
            if d_right < self._cfg.CLICK_THRESHOLD:
                self.active_mode = "RIGHT_CLICK"
                return "RIGHT_CLICK"

        # 9. Scroll: index + middle both extended (peace sign)
        if index and middle and not ring and not pinky:
            # Track wrist Y for scroll direction
            self.active_mode = "SCROLL"
            return "SCROLL"

        # 10. Draw: index only, middle curled, gap small (no click)
        if index and not middle and not ring and not pinky:
            d_im = dist(index_tip, middle_tip)
            if d_im < self._cfg.DRAW_MODE_DISTANCE:
                self.active_mode = "DRAW"
                return "DRAW"

        # 11. Media swipe detection (index + pinky = "horns")
        if index and not middle and not ring and pinky:
            swipe = self._detect_swipe(wrist)
            if swipe:
                self.active_mode = swipe
                return swipe

        # 12. Default – cursor movement (index extended)
        if index and not middle and not ring and not pinky:
            self.active_mode = "MOVE_CURSOR"
            return "MOVE_CURSOR"

        self.active_mode = "IDLE"
        return "IDLE"

    # ── Private helpers ────────────────────────────────────────────────────────

    def _handle_click(self) -> str:
        """Distinguish single vs double click based on timing."""
        now = time.time()
        if now - self._last_click_time < self._cfg.DOUBLE_CLICK_INTERVAL:
            self._last_click_time = 0.0  # reset so triple doesn't trigger again
            return "DOUBLE_CLICK"
        self._last_click_time = now
        return "CLICK"

    def _handle_screenshot(self) -> str | None:
        """Return 'SCREENSHOT' once the gesture has been held long enough."""
        now = time.time()
        if self._screenshot_start == 0.0:
            self._screenshot_start = now
            return None
        held = now - self._screenshot_start
        if held >= self._cfg.SCREENSHOT_HOLD_TIME and not self._screenshot_fired:
            self._screenshot_fired = True
            return "SCREENSHOT"
        return None

    def _detect_swipe(self, wrist: tuple) -> str | None:
        """
        Buffer recent wrist X positions and detect left/right swipes.
        Returns 'MEDIA_NEXT', 'MEDIA_PREV', or None.
        """
        now = time.time()
        if now - self._last_media_action_time < self._cfg.MEDIA_COOLDOWN:
            return None

        self._wrist_history.append(wrist[0])
        if len(self._wrist_history) > self._SWIPE_HISTORY:
            self._wrist_history.pop(0)

        if len(self._wrist_history) < self._SWIPE_HISTORY:
            return None

        delta = self._wrist_history[-1] - self._wrist_history[0]
        if abs(delta) >= self._SWIPE_DELTA:
            self._wrist_history.clear()
            self._last_media_action_time = now
            # Flipped because frame is mirrored
            return "MEDIA_PREV" if delta > 0 else "MEDIA_NEXT"

        return None