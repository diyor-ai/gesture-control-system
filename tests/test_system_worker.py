"""Volume / brightness: step filtering and a non-blocking main loop."""

import threading
import time

import numpy as np

from modules.config import Config
from modules.system_worker import LatestValueWorker, StepGate


def test_step_gate_ignores_small_changes_and_passes_big_ones():
    gate = StepGate(0.05)
    assert gate.accept(0.50) is True            # first value always goes through
    assert gate.accept(0.52) is False
    assert gate.accept(0.54) is False
    assert gate.accept(0.56) is True            # 0.06 from the last accepted value
    assert gate.accept(0.50) is True


def test_step_gate_always_reaches_the_ends():
    gate = StepGate(0.10)
    gate.accept(0.95)
    assert gate.accept(1.0) is True             # only 0.05 away, but it is the maximum
    assert gate.accept(1.0) is False
    gate.accept(0.04)
    assert gate.accept(0.0) is True


def test_worker_runs_the_setter_off_the_calling_thread_and_never_blocks():
    started, release = threading.Event(), threading.Event()
    applied = []

    def slow(value):
        started.set()
        release.wait(2)
        applied.append((value, threading.current_thread().name))

    worker = LatestValueWorker(slow, name="test-worker")
    t0 = time.perf_counter()
    for v in (0.1, 0.2, 0.3, 0.4, 0.5):
        worker.submit(v)
    assert time.perf_counter() - t0 < 0.1       # submit() returns at once
    assert started.wait(2)
    release.set()
    worker.close(timeout=2)
    # the first value may already have been taken; the newest one must win
    assert applied[-1][0] == 0.5
    assert all(name == "test-worker" for _, name in applied)
    assert len(applied) <= 2                    # intermediate values were coalesced


def test_worker_survives_a_failing_setter():
    calls = []

    def flaky(value):
        calls.append(value)
        if value == 1:
            raise RuntimeError("boom")

    worker = LatestValueWorker(flaky)
    worker.submit(1)
    time.sleep(0.1)
    worker.submit(2)
    time.sleep(0.1)
    worker.close()
    assert calls == [1, 2]


def _volume_controller(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    from modules.volume_control import VolumeController

    return VolumeController(Config())


def _landmarks(distance):
    lm = [(0.0, 0.0, 0.0)] * 21
    lm[20] = (distance, 0.0, 0.0)
    return lm


def test_volume_controller_ignores_jitter(monkeypatch, gui_stubs):
    ctrl = _volume_controller(monkeypatch)
    calls = []
    ctrl._worker.close()
    ctrl._worker = LatestValueWorker(calls.append)
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    for i in range(200):
        ctrl.adjust(_landmarks(0.20 + (0.001 if i % 2 else -0.001)), frame)
    time.sleep(0.1)
    ctrl.close()
    assert len(calls) == 1


def test_volume_controller_does_not_block_on_a_slow_mixer(monkeypatch, gui_stubs):
    ctrl = _volume_controller(monkeypatch)
    applied = []

    def slow_mixer(value):
        time.sleep(0.3)
        applied.append(value)

    ctrl._worker.close()
    ctrl._worker = LatestValueWorker(slow_mixer)
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    t0 = time.perf_counter()
    for i in range(60):                          # a sweep from 0.02 to 0.35
        ctrl.adjust(_landmarks(0.02 + i * 0.0055), frame)
    assert time.perf_counter() - t0 < 0.2        # 60 frames, mixer takes 0.3 s per call
    time.sleep(0.8)
    ctrl.close()
    assert applied[-1] > 0.9                     # ended on the newest value
    assert len(applied) < 10                     # far fewer than 60 mixer calls
