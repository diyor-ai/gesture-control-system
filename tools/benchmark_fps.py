"""
Measure real camera + MediaPipe throughput (no window, no input injection).

    python tools/benchmark_fps.py            # compares old and new defaults
    python tools/benchmark_fps.py 640 480 0  # width height model_complexity

Keep a hand in front of the camera for a realistic number.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2                                     # noqa: E402
from modules.config import Config              # noqa: E402
from modules.hand_tracker import HandTracker   # noqa: E402

FRAMES, WARMUP = 150, 15


def run(width: int, height: int, complexity: int) -> None:
    cfg = Config()
    cfg.FRAME_WIDTH, cfg.FRAME_HEIGHT, cfg.MODEL_COMPLEXITY = width, height, complexity
    cap = cv2.VideoCapture(cfg.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    tracker = HandTracker(cfg)

    for _ in range(WARMUP):
        ok, frame = cap.read()
    got = frame.shape[1], frame.shape[0]

    t0 = time.perf_counter()
    for _ in range(FRAMES):
        cap.read()
    capture_fps = FRAMES / (time.perf_counter() - t0)

    hands, t0 = 0, time.perf_counter()
    for _ in range(FRAMES):
        ok, frame = cap.read()
        _, found = tracker.process(cv2.flip(frame, 1))
        hands += bool(found)
    fps = FRAMES / (time.perf_counter() - t0)
    cap.release()

    print(f"requested {width}x{height} complexity {complexity} | camera gives {got[0]}x{got[1]} | "
          f"capture only {capture_fps:5.1f} FPS | capture+tracking {fps:5.1f} FPS | "
          f"hand in {hands}/{FRAMES} frames")


if __name__ == "__main__":
    if len(sys.argv) == 4:
        run(*map(int, sys.argv[1:]))
    else:
        run(1280, 720, 1)     # previous defaults
        run(640, 480, 0)      # current defaults
