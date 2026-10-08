import pytest

from modules.camera import CameraError, read_frame


class FakeCap:
    def __init__(self, results):
        self._results = list(results)
        self.reads = 0

    def read(self):
        self.reads += 1
        return self._results.pop(0) if self._results else (False, None)


def test_returns_frame_immediately():
    cap = FakeCap([(True, "frame")])
    assert read_frame(cap, max_failures=5, sleep=lambda s: None) == "frame"
    assert cap.reads == 1


def test_recovers_after_transient_failures():
    cap = FakeCap([(False, None), (False, None), (True, "frame")])
    assert read_frame(cap, max_failures=5, sleep=lambda s: None) == "frame"
    assert cap.reads == 3


def test_gives_up_after_the_retry_limit_with_a_clear_error():
    cap = FakeCap([])
    sleeps = []
    with pytest.raises(CameraError, match="no frames for 4 consecutive"):
        read_frame(cap, max_failures=4, retry_delay=0.2, sleep=sleeps.append)
    assert cap.reads == 4
    assert sleeps == [0.2] * 4


def test_a_none_frame_counts_as_a_failure():
    cap = FakeCap([(True, None), (True, "frame")])
    assert read_frame(cap, max_failures=3, sleep=lambda s: None) == "frame"
