"""
Shared test helpers: a synthetic hand-landmark factory and a fake clock.

No camera, OpenCV or MediaPipe is needed – the tests feed 21 hand-made
(x, y, z) landmark tuples straight into the gesture engine.
"""

from typing import Dict, List, Optional, Tuple

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


@pytest.fixture
def engine(clock):
    from modules.config import Config
    from modules.gesture_engine import GestureEngine

    return GestureEngine(Config(), clock=clock)
