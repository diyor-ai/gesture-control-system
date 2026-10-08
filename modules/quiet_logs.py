"""
quiet_logs.py – Silence third-party start-up noise, keep our own [INFO] lines.

Sources: OpenCV's bundled Qt (font directory warnings), MediaPipe's protobuf
deprecation warning, and the C++ side of MediaPipe / TFLite / absl, which
writes straight to file descriptor 2.

apply() must run before OpenCV, MediaPipe or TensorFlow Lite are imported.
"""

import contextlib
import os
import re
import threading
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


# Known-harmless lines the C++ libraries print straight to file descriptor 2.
# Anything that does not match (camera / model errors, tracebacks) passes through.
_NOISE = re.compile(
    r"^(WARNING: All log messages before absl::InitializeLog\(\)"
    r"|INFO: Created TensorFlow Lite XNNPACK delegate"
    r"|[IW]0000 .*(gl_context(_egl)?\.cc|inference_feedback_manager\.cc)"
    r"|QFontDatabase: )"
)


def is_noise(line: str) -> bool:
    return bool(_NOISE.match(line))


@contextlib.contextmanager
def filter_stderr():
    """
    Route file descriptor 2 through a filter that drops the known noisy lines
    and forwards everything else to the real stderr unchanged.
    """
    try:
        saved = os.dup(2)
        read_fd, write_fd = os.pipe()
    except OSError:                       # no usable fds (odd embedding): do nothing
        yield
        return

    def pump() -> None:
        with os.fdopen(read_fd, "rb", closefd=True) as src:
            for raw in src:
                if not is_noise(raw.decode("utf-8", "replace")):
                    os.write(saved, raw)

    thread = threading.Thread(target=pump, daemon=True)
    thread.start()
    os.dup2(write_fd, 2)
    try:
        yield
    finally:
        os.dup2(saved, 2)                 # restore first so a traceback is never filtered
        os.close(write_fd)                # EOF for the pump
        thread.join(timeout=2)
        os.close(saved)
