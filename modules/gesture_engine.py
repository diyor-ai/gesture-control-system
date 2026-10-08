"""
gesture_engine.py – Core gesture classification module.

Maps raw MediaPipe landmarks to named gestures consumed by other modules.
Each hand has its own state, and every gesture has its own pose, so no two
gestures can shadow each other.

Poses (T I M R P = thumb, index, middle, ring, pinky; "-" = ignored)
--------------------------------------------------------------------
Primary hand only (cursor family, Config.PRIMARY_HAND, default "Right")
  MOVE_CURSOR       – index up, M R P down, thumb free (also the L shape)
  CLICK             – same pose, thumb tip pinched onto the index tip
  DOUBLE_CLICK      – a second CLICK pinch within DOUBLE_CLICK_INTERVAL
  RIGHT_CLICK       – only middle up, thumb tip pinched onto the middle tip
  DRAW              – like MOVE_CURSOR, but while the canvas is enabled

Secondary hand only
  ZOOM              – L shape: thumb + index up, M R P down

Either hand
  SCROLL            – T - | I M up, R P down              (peace sign)
  VOLUME            – T up, P up, I M R down              (hang loose)
  BRIGHTNESS        – T up, R up, I M P down
  DRAG_WINDOW       – I M R P down (fist, thumb ignored)
  MEDIA_PLAY_PAUSE  – I M R up, P down, held PLAY_PAUSE_HOLD_TIME
  MEDIA_NEXT / PREV – I P up, M R down, then swipe right / left
  SCREENSHOT        – all five fingers up, held SCREENSHOT_HOLD_TIME

Event gestures (clicks, play/pause, screenshot, swipes) are returned exactly
once; everything else is level-triggered and returned every frame.
"""

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
from modules.config import Config
from modules.hand_tracker import HandTracker

# Poses whose gesture is reported on every frame while the pose is held.
_CONTINUOUS = frozenset(
    {"MOVE_CURSOR", "DRAW", "SCROLL", "VOLUME", "BRIGHTNESS", "DRAG_WINDOW", "ZOOM"}
)


@dataclass
class _HandState:
    """Everything the engine remembers about one hand between frames."""
    last_click_time: float = float("-inf")
    last_media_time: float = float("-inf")
    wrist_history: List[float] = field(default_factory=list)
    prev_pose: str = "IDLE"
    pose_since: float = 0.0
    entered: bool = False      # pose changed on this very frame
    fired: bool = False        # one-shot already emitted for the current pose


class GestureEngine:
    """
    Stateful gesture classifier.  Keeps one `_HandState` per hand label so
    timing-based gestures (double click, holds, swipes) never mix two hands.
    """

    _SWIPE_HISTORY = 6
    _SWIPE_DELTA   = 0.06

    def __init__(self, cfg: Config, clock: Callable[[], float] = time.monotonic) -> None:
        if cfg.PRIMARY_HAND not in ("Left", "Right"):
            raise ValueError(
                f"Config.PRIMARY_HAND must be 'Left' or 'Right', got {cfg.PRIMARY_HAND!r}"
            )
        self._cfg   = cfg
        self._clock = clock
        self._states: Dict[str, _HandState] = {}
        self._seen: set = set()

        self.primary_hand = cfg.PRIMARY_HAND
        self.active_mode  = "IDLE"
        # Per-hand diagnostics for the --debug overlay
        self.debug: Dict[str, dict] = {}

    # ── Public API ─────────────────────────────────────────────────────────────

    def classify(self, landmarks: List[tuple], hand_label: str, canvas_enabled: bool = False) -> str:
        """
        Classify the current hand pose and return a gesture string.

        Parameters
        ----------
        landmarks       : 21 normalised (x, y, z) tuples from MediaPipe
        hand_label      : "Left" or "Right"
        canvas_enabled  : Whether drawing canvas is enabled (from main.py)

        Returns
        -------
        gesture string, e.g. "CLICK", "SCROLL", "IDLE"
        """
        now   = self._clock()
        state = self._states.setdefault(hand_label, _HandState(pose_since=now))
        first = not self._seen
        self._seen.add(hand_label)

        fingers = HandTracker.fingers_up(landmarks)
        is_primary = hand_label == self.primary_hand
        pose = self._pose(landmarks, fingers, is_primary, canvas_enabled)

        state.entered = pose != state.prev_pose
        if state.entered:
            state.prev_pose  = pose
            state.pose_since = now
            state.fired      = False
            state.wrist_history.clear()

        gesture, mode = self._resolve(state, pose, landmarks, now)

        if first or mode != "IDLE":
            self.active_mode = mode
        self.debug[hand_label] = {
            "fingers": fingers, "pose": pose, "gesture": gesture, "primary": is_primary,
        }
        return gesture

    def end_frame(self) -> None:
        """Call once per camera frame, after every visible hand was classified."""
        if not self._seen:
            self.active_mode = "IDLE"
        self.debug = {k: v for k, v in self.debug.items() if k in self._seen}
        self._seen = set()

    # ── Pose classification (stateless) ───────────────────────────────────────

    def _pose(
        self,
        landmarks: List[tuple],
        fingers: List[bool],
        is_primary: bool,
        canvas_enabled: bool,
    ) -> str:
        """Map finger states to exactly one pose name for this frame."""
        thumb, index, middle, ring, pinky = fingers
        dist = HandTracker.distance
        others_down = not (middle or ring or pinky)

        if thumb and index and middle and ring and pinky:
            return "SCREENSHOT"
        if not (index or middle or ring or pinky):
            return "DRAG_WINDOW"
        if thumb and pinky and not (index or middle or ring):
            return "VOLUME"
        if thumb and ring and not (index or middle or pinky):
            return "BRIGHTNESS"
        if index and middle and ring and not pinky:
            return "MEDIA_PLAY_PAUSE"
        if index and pinky and not (middle or ring):
            return "MEDIA_SWIPE"
        if index and middle and not (ring or pinky):
            return "SCROLL"

        if index and others_down:
            if is_primary:
                if dist(landmarks[4], landmarks[8]) < self._cfg.CLICK_THRESHOLD:
                    return "CLICK"
                return "DRAW" if canvas_enabled else "MOVE_CURSOR"
            return "ZOOM" if thumb else "IDLE"

        if middle and not (index or ring or pinky) and is_primary:
            if dist(landmarks[4], landmarks[12]) < self._cfg.CLICK_THRESHOLD:
                return "RIGHT_CLICK"

        return "IDLE"

    # ── Pose → gesture (stateful) ─────────────────────────────────────────────

    def _resolve(
        self, state: _HandState, pose: str, landmarks: List[tuple], now: float
    ) -> Tuple[str, str]:
        """Turn a pose into the gesture to dispatch; returns (gesture, hud_mode)."""
        if pose in _CONTINUOUS:
            return pose, pose

        if pose == "CLICK":
            if state.entered:
                gesture = self._click(state, now)
                return gesture, gesture
            return "IDLE", "IDLE"

        if pose == "RIGHT_CLICK":
            return ("RIGHT_CLICK", pose) if state.entered else ("IDLE", "IDLE")

        if pose in ("SCREENSHOT", "MEDIA_PLAY_PAUSE"):
            hold = (self._cfg.SCREENSHOT_HOLD_TIME if pose == "SCREENSHOT"
                    else self._cfg.PLAY_PAUSE_HOLD_TIME)
            if state.fired:
                return "IDLE", "IDLE"
            if now - state.pose_since >= hold:
                state.fired = True
                return pose, pose
            return "IDLE", f"{pose}_HOLD" if pose == "SCREENSHOT" else "PLAY_PAUSE_HOLD"

        if pose == "MEDIA_SWIPE":
            swipe = self._swipe(state, landmarks[0][0], now)
            return (swipe, swipe) if swipe else ("IDLE", "IDLE")

        return "IDLE", "IDLE"

    def _click(self, state: _HandState, now: float) -> str:
        """A new pinch: DOUBLE_CLICK if the previous pinch was recent enough."""
        if now - state.last_click_time < self._cfg.DOUBLE_CLICK_INTERVAL:
            state.last_click_time = float("-inf")   # a third pinch starts afresh
            return "DOUBLE_CLICK"
        state.last_click_time = now
        return "CLICK"

    def _swipe(self, state: _HandState, wrist_x: float, now: float) -> Optional[str]:
        """
        Buffer recent wrist X positions and detect left/right swipes.
        The frame is already mirrored, so +x is the user's right.
        """
        if now - state.last_media_time < self._cfg.MEDIA_COOLDOWN:
            return None

        hist = state.wrist_history
        hist.append(wrist_x)
        if len(hist) > self._SWIPE_HISTORY:
            hist.pop(0)
        if len(hist) < self._SWIPE_HISTORY:
            return None

        delta = hist[-1] - hist[0]
        if abs(delta) >= self._SWIPE_DELTA:
            hist.clear()
            state.last_media_time = now
            return "MEDIA_NEXT" if delta > 0 else "MEDIA_PREV"
        return None
