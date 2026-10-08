"""
quiet_logs.py – Silence third-party start-up noise, keep our own [INFO] lines.

Sources: OpenCV's bundled Qt (font directory warnings), MediaPipe's protobuf
deprecation warning, and the C++ side of MediaPipe / TFLite / absl, which
writes straight to file descriptor 2.

apply() must run before OpenCV, MediaPipe or TensorFlow Lite are imported.
"""

import contextlib
import os
import warnings

_FONT_DIRS = ("/usr/share/fonts", "/usr/local/share/fonts")


def apply() -> None:
    """Set the environment variables and warning filters (idempotent)."""
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")     # TensorFlow / TFLite
    os.environ.setdefault("GLOG_minloglevel", "3")          # glog / absl in MediaPipe
    os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false;*.info=false;*.warning=false")
    if "QT_QPA_FONTDIR" not in os.environ:                  # point Qt at real fonts
        for path in _FONT_DIRS:
            if os.path.isdir(path):
                os.environ["QT_QPA_FONTDIR"] = path
                break
    warnings.filterwarnings("ignore", module=r"google\.protobuf.*")


@contextlib.contextmanager
def quiet_stderr():
    """Send file descriptor 2 to /dev/null (C++ libraries bypass sys.stderr)."""
    try:
        saved = os.dup(2)
        devnull = os.open(os.devnull, os.O_WRONLY)
    except OSError:                       # no usable fds (odd embedding): do nothing
        yield
        return
    try:
        os.dup2(devnull, 2)
        yield
    finally:
        os.dup2(saved, 2)
        os.close(saved)
        os.close(devnull)
