"""
config.py – Central configuration for the Gesture Control System.

All tunable parameters live here so every module stays in sync.
"""

import screeninfo
import cv2


def _get_screen_resolution() -> tuple[int, int]:
    """Return (width, height) of the primary monitor."""
    try:
        monitor = screeninfo.get_monitors()[0]
        return monitor.width, monitor.height
    except Exception:
        return 1920, 1080  # safe fallback


class Config:
    # ── Camera ────────────────────────────────────────────────────────────────
    CAMERA_INDEX  = 0
    FRAME_WIDTH   = 1280
    FRAME_HEIGHT  = 720
    TARGET_FPS    = 30

    # ── Screen ────────────────────────────────────────────────────────────────
    SCREEN_W, SCREEN_H = _get_screen_resolution()

    # ── MediaPipe hand detection ───────────────────────────────────────────────
    MAX_NUM_HANDS          = 2
    DETECTION_CONFIDENCE   = 0.75
    TRACKING_CONFIDENCE    = 0.75

    # ── Cursor movement ───────────────────────────────────────────────────────
    # Fraction of frame used as the active control zone (avoids edge dead-zones)
    CONTROL_ZONE_MARGIN    = 0.15          # 15 % margin on each side
    SMOOTHING_FACTOR       = 0.30          # lower → smoother, higher → faster
    CURSOR_SPEED_MULTIPLIER = 1.5

    # ── Gesture thresholds ────────────────────────────────────────────────────
    CLICK_THRESHOLD        = 0.04          # normalised distance between tips
    DOUBLE_CLICK_INTERVAL  = 0.35          # seconds between two clicks to register as double
    SCROLL_THRESHOLD       = 0.06          # minimum pinch distance for scroll gesture
    DRAW_MODE_DISTANCE     = 0.05          # index–middle gap to enter draw mode
    ZOOM_THRESHOLD         = 0.08          # pinch distance to begin zoom
    SCREENSHOT_HOLD_TIME   = 1.0           # seconds gesture must be held
    DRAG_THRESHOLD         = 0.05

    # ── Volume / Brightness ───────────────────────────────────────────────────
    VOLUME_MIN_DIST        = 0.02
    VOLUME_MAX_DIST        = 0.35
    BRIGHTNESS_MIN_DIST    = 0.02
    BRIGHTNESS_MAX_DIST    = 0.35

    # ── Drawing canvas ────────────────────────────────────────────────────────
    DRAW_COLOR             = (0, 255, 180)  # neon-green
    DRAW_THICKNESS         = 4
    DRAW_ERASER_RADIUS     = 30

    # ── UI overlay ────────────────────────────────────────────────────────────
    HUD_FONT               = cv2.FONT_HERSHEY_SIMPLEX  # type: ignore[attr-defined]  # noqa: F821
    HUD_SCALE              = 0.65
    HUD_THICKNESS          = 2
    HUD_COLOR_PRIMARY      = (255, 255, 255)
    HUD_COLOR_ACCENT       = (0, 255, 200)
    HUD_COLOR_WARNING      = (0, 100, 255)

    # ── Screenshot ────────────────────────────────────────────────────────────
    SCREENSHOT_SAVE_DIR    = "screenshots"

    # ── Media keys ────────────────────────────────────────────────────────────
    MEDIA_COOLDOWN         = 1.0           # seconds between media key presses

    # ── Hand-loss recovery ────────────────────────────────────────────────────
    HAND_LOSS_GRACE_FRAMES = 5             # frames to wait before resetting state