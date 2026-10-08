"""
system_worker.py – Keep slow OS calls (amixer, xrandr, ...) off the main loop.

StepGate        – only lets a value through when it moved by a meaningful step.
LatestValueWorker – runs a setter on a background thread; if values arrive
                  faster than the setter finishes, only the newest one is
                  applied, so the camera loop never waits on a subprocess.
"""

import threading
from typing import Callable, Optional


class StepGate:
    """Accept a 0–1 value only if it differs from the last accepted one by `step`."""

    def __init__(self, step: float) -> None:
        self._step = step
        self._last: Optional[float] = None

    def accept(self, value: float) -> bool:
        last = self._last
        reached_end = value in (0.0, 1.0) and value != last   # always reach min / max
        if last is None or reached_end or abs(value - last) >= self._step:
            self._last = value
            return True
        return False


class LatestValueWorker:
    """Apply submitted values on a daemon thread, coalescing to the latest."""

    def __init__(self, apply: Callable[[float], None], name: str = "system-worker") -> None:
        self._apply   = apply
        self._cond    = threading.Condition()
        self._pending: Optional[float] = None
        self._has_pending = False
        self._closed  = False
        self._thread  = threading.Thread(target=self._run, name=name, daemon=True)
        self._thread.start()

    def submit(self, value: float) -> None:
        """Queue `value`; returns immediately and never blocks."""
        with self._cond:
            self._pending     = value
            self._has_pending = True
            self._cond.notify()

    def close(self, timeout: float = 1.0) -> None:
        with self._cond:
            self._closed = True
            self._cond.notify()
        self._thread.join(timeout)

    def _run(self) -> None:
        while True:
            with self._cond:
                while not self._has_pending and not self._closed:
                    self._cond.wait()
                if self._closed:
                    return
                value, self._has_pending = self._pending, False
            try:
                self._apply(value)
            except Exception as exc:               # keep the worker alive
                print(f"[{self._thread.name}] {exc}")
