"""Ctrl+C shutdown in main(), and the stderr noise filter."""

import os
from unittest.mock import MagicMock

import pytest

from modules import quiet_logs


def test_ctrl_c_releases_everything_and_exits_cleanly(gui_stubs, monkeypatch, capsys):
    import main
    cv2 = gui_stubs.cv2
    cap = MagicMock()
    cap.isOpened.return_value = True
    cv2.VideoCapture.return_value = cap
    cv2.waitKey.side_effect = KeyboardInterrupt        # user presses Ctrl+C
    backend = MagicMock()
    tracker = MagicMock()
    tracker.process.return_value = (MagicMock(), [])
    volume, brightness = MagicMock(), MagicMock()
    monkeypatch.setattr(main, "create_backend", lambda cfg: backend)
    monkeypatch.setattr(main, "read_frame", lambda *a: MagicMock())
    monkeypatch.setattr(main, "HandTracker", lambda cfg: tracker)
    monkeypatch.setattr(main, "VolumeController", lambda cfg: volume)
    monkeypatch.setattr(main, "BrightnessController", lambda cfg: brightness)
    for name in ("CursorController", "ScrollController", "ScreenshotModule", "ZoomController",
                 "MediaController", "UIOverlay", "DrawingCanvas"):
        monkeypatch.setattr(main, name, lambda *a, **k: MagicMock())

    main.main()                                         # must not raise

    cap.release.assert_called_once()
    cv2.destroyAllWindows.assert_called()
    backend.close.assert_called_once()
    volume.close.assert_called_once()
    brightness.close.assert_called_once()
    assert "shut down cleanly" in capsys.readouterr().out


@pytest.mark.parametrize("line", [
    "WARNING: All log messages before absl::InitializeLog() is called are written to STDERR",
    "INFO: Created TensorFlow Lite XNNPACK delegate for CPU.",
    "W0000 00:00:1.0 1 inference_feedback_manager.cc:114] Feedback manager requires a model",
    "I0000 00:00:1.0 1 gl_context_egl.cc:85] Successfully initialized EGL.",
    "QFontDatabase: Cannot find font directory /x/fonts.",
])
def test_known_noise_is_dropped(line):
    assert quiet_logs.is_noise(line)


@pytest.mark.parametrize("line", [
    "E0000 00:00:1.0 1 calculator_graph.cc:1] Failed to open model",
    "Traceback (most recent call last):",
    "[ WARN:0@1.0] global cap_v4l.cpp:999 open VIDEOIO(V4L2:/dev/video0): can't open camera",
])
def test_real_errors_pass_through(line):
    assert not quiet_logs.is_noise(line)


def test_filter_stderr_forwards_real_lines_and_restores_fd2(capfdbinary):
    with quiet_logs.filter_stderr():
        os.write(2, b"INFO: Created TensorFlow Lite XNNPACK delegate for CPU.\n")
        os.write(2, b"E0000 real model error\n")
    os.write(2, b"after\n")
    err = capfdbinary.readouterr().err
    assert err == b"E0000 real model error\nafter\n"
