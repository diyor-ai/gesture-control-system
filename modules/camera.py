"""
camera.py – Frame grabbing with a bounded retry budget.

Kept free of OpenCV imports (it only calls `.read()` on the capture object)
so it can be unit-tested with a fake camera.
"""

import time
from typing import Callable


class CameraError(RuntimeError):
    """Raised when the camera stops delivering frames."""


def read_frame(
    cap,
    max_failures: int,
    retry_delay: float = 0.1,
    sleep: Callable[[float], None] = time.sleep,
):
    """
    Return the next frame from `cap`.

    A failed read is retried up to `max_failures` times in a row (waiting
    `retry_delay` seconds between attempts).  After that a CameraError with a
    clear message is raised instead of spinning forever.
    """
    for attempt in range(1, max_failures + 1):
        ok, frame = cap.read()
        if ok and frame is not None:
            return frame
        if attempt == 1:
            print("[WARN] Failed to read a camera frame – retrying...")
        sleep(retry_delay)

    raise CameraError(
        f"Camera returned no frames for {max_failures} consecutive attempts "
        f"(~{max_failures * retry_delay:.1f} s). It may have been unplugged or "
        "is in use by another application. Check CAMERA_INDEX in config.py."
    )
