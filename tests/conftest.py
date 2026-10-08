"""
Shared test helpers: a synthetic hand-landmark factory and a fake clock.

No camera, OpenCV or MediaPipe is needed – the tests feed 21 hand-made
(x, y, z) landmark tuples straight into the gesture engine.
"""

import sys
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple
from unittest.mock import MagicMock

import pytest

Landmarks = List[Tuple[float, float, float]]

# Base geometry of a right hand seen in the mirrored (selfie) frame, palm
# towards the camera, fingers pointing up.  Coordinates are normalised 0–1.
_WRIST = (0.50, 0.85)
_MCP = {"I": (0.45, 0.62), "M": (0.50, 0.60), "R": (0.55, 0.62), "P": (0.60, 0.66)}
_FINGER_BASE_IDX = {"I": 5, "M": 9, "R": 13, "P": 17}


def make_hand(
    up: str = "",
    pinch: Optional[str] = None,
    wrist_x: float = 0.50,
    mirror: bool = False,
) -> Landmarks:
    """
    Build 21 synthetic landmarks.

    up      : letters of the extended fingers, any of "TIMRP"
              (T = thumb, I = index, M = middle, R = ring, P = pinky)
    pinch   : "index" or "middle" – put the thumb tip on that fingertip
    wrist_x : horizontal position of the hand (to simulate swipes)
    mirror  : mirror the hand horizontally (gives a left-hand shape)
    """
    pts: Dict[int, Tuple[float, float]] = {0: _WRIST}

    # Thumb: 1 CMC, 2 MCP, 3 IP, 4 tip
    pts[1] = (0.46, 0.80)
    pts[2] = (0.42, 0.74)
    if "T" in up:
        pts[3], pts[4] = (0.36, 0.69), (0.30, 0.64)      # sticking out
    else:
        pts[3], pts[4] = (0.46, 0.70), (0.51, 0.68)      # folded over the palm

    # Fingers: base+0 MCP, +1 PIP, +2 DIP, +3 tip
    for f, (x, y) in _MCP.items():
        base = _FINGER_BASE_IDX[f]
        pts[base] = (x, y)
        if f in up:
            pts[base + 1] = (x, y - 0.07)
            pts[base + 2] = (x, y - 0.11)
            pts[base + 3] = (x, y - 0.15)
        else:
            pts[base + 1] = (x, y - 0.05)
            pts[base + 2] = (x, y - 0.02)
            pts[base + 3] = (x, y + 0.01)

    if pinch is not None:
        tip = pts[8] if pinch == "index" else pts[12]
        pts[4] = (tip[0] + 0.01, tip[1])
        pts[3] = (tip[0] - 0.02, tip[1] + 0.12)

    shift = wrist_x - 0.50
    out: Landmarks = []
    for i in range(21):
        x, y = pts[i]
        x += shift
        if mirror:
            x = 1.0 - x
        out.append((x, y, 0.0))
    return out


class FakeClock:
    """Deterministic replacement for time.monotonic()."""

    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def play(engine, clock, hand, frames, label="Right", canvas=False, dt=1 / 30):
    """Feed the same landmarks for `frames` frames; return the gesture of each."""
    out = []
    for _ in range(frames):
        out.append(engine.classify(hand, label, canvas_enabled=canvas))
        if hasattr(engine, "end_frame"):
            engine.end_frame()
        clock.advance(dt)
    return out


def _make_engine(clock, **overrides):
    from modules.config import Config
    from modules.gesture_engine import GestureEngine

    cfg = Config()
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return GestureEngine(cfg, clock=clock)


@pytest.fixture
def engine(clock):
    """Engine with the stability layer off (1 frame) so pose tests are immediate."""
    return _make_engine(clock, STABILITY_FRAMES=1)


@pytest.fixture
def stable_engine(clock):
    """Engine with the default configuration (stability layer on)."""
    return _make_engine(clock)


@pytest.fixture(params=[1, 3], ids=["stability-1", "stability-3"])
def engine_any(request, clock):
    """Engine run both without and with the stability layer."""
    return _make_engine(clock, STABILITY_FRAMES=request.param)


_GUI_MODULES = (
    "main",
    "modules.ui_overlay", "modules.volume_control", "modules.brightness_control",
    "modules.scroll_control", "modules.zoom_control", "modules.cursor_controller",
    "modules.window_mover", "modules.media_control", "modules.screenshot",
    "modules.drawing_canvas",
)


@pytest.fixture
def gui_stubs(monkeypatch):
    """
    Replace OpenCV and PyAutoGUI by mocks and import the controller modules
    fresh against them, so no test needs a camera, display or input device.
    """
    stubs = SimpleNamespace(cv2=MagicMock(), pyautogui=MagicMock())
    monkeypatch.setitem(sys.modules, "cv2", stubs.cv2)
    monkeypatch.setitem(sys.modules, "pyautogui", stubs.pyautogui)
    for name in _GUI_MODULES:
        sys.modules.pop(name, None)
    yield stubs
    for name in _GUI_MODULES:
        sys.modules.pop(name, None)
