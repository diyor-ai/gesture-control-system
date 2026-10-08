"""
config.py – Central configuration for the Gesture Control System.

All tunable parameters live here so every module stays in sync.
"""


def _get_screen_resolution() -> tuple[int, int]:
    """Return (width, height) of the primary monitor."""
    try:
        import screeninfo  # imported lazily so the config loads without a display stack
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
    CAMERA_MAX_READ_FAILURES = 30          # consecutive failed reads before giving up
    CAMERA_RETRY_DELAY       = 0.1         # seconds between retries

    # ── Screen ────────────────────────────────────────────────────────────────
    SCREEN_W, SCREEN_H = _get_screen_resolution()

    # ── MediaPipe hand detection ───────────────────────────────────────────────
    MAX_NUM_HANDS          = 2
    DETECTION_CONFIDENCE   = 0.75
    TRACKING_CONFIDENCE    = 0.75

    PRIMARY_HAND           = "Right"       # "Left" | "Right": drives cursor, clicks and drawing
                                           # (the other hand gets ZOOM instead)

    STABILITY_FRAMES       = 3             # consecutive frames a pose must be seen to activate

    # ── Cursor movement ───────────────────────────────────────────────────────
    # Fraction of frame used as the active control zone (avoids edge dead-zones)
    CONTROL_ZONE_MARGIN    = 0.15          # 15 % margin on each side
    SMOOTHING_FACTOR       = 0.30          # lower → smoother, higher → faster
    CURSOR_SPEED_MULTIPLIER = 1.5

    # ── Gesture thresholds ────────────────────────────────────────────────────
    CLICK_THRESHOLD        = 0.04          # normalised distance between tips
    DOUBLE_CLICK_INTERVAL  = 0.40          # max seconds between two pinch starts (<= OS double-click time)
    SCROLL_THRESHOLD       = 0.06          # minimum pinch distance for scroll gesture
    DRAW_MODE_DISTANCE     = 0.05          # index–middle gap to enter draw mode
    SCREENSHOT_HOLD_TIME   = 1.0           # seconds gesture must be held
    PLAY_PAUSE_HOLD_TIME   = 0.5           # seconds the 3-finger pose must be held
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
    HUD_FONT               = 0             # cv2.FONT_HERSHEY_SIMPLEX (numeric so config needs no OpenCV)
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