"""
config.py – Central configuration for the Gesture Control System.

All tunable parameters live here so every module stays in sync.
"""


import platform


def _get_screen_resolution() -> tuple[int, int]:
    """Return (width, height) of the primary monitor (Wayland-safe)."""
    from modules.linux_backends import screen_size
    return screen_size()


class Config:
    # ── Platform features ─────────────────────────────────────────────────────
    # Moving another application's window is only implemented for Windows
    # (win32gui) and macOS (AppleScript). On Linux the fist gesture is disabled
    # instead of pretending to work.
    WINDOW_DRAG_ENABLED = platform.system() in ("Windows", "Darwin")

    # ── Input injection ───────────────────────────────────────────────────────
    INPUT_BACKEND = "auto"                 # "auto" | "uinput" | "pyautogui" (or $GESTURE_INPUT)

    # ── Camera ────────────────────────────────────────────────────────────────
    CAMERA_INDEX  = 0
    FRAME_WIDTH   = 640
    FRAME_HEIGHT  = 480
    TARGET_FPS    = 30
    CAMERA_MAX_READ_FAILURES = 30          # consecutive failed reads before giving up
    CAMERA_RETRY_DELAY       = 0.1         # seconds between retries

    # ── Screen ────────────────────────────────────────────────────────────────
    SCREEN_W, SCREEN_H = _get_screen_resolution()

    # ── MediaPipe hand detection ───────────────────────────────────────────────
    MODEL_COMPLEXITY       = 0             # 0 = fast landmark model, 1 = more accurate / slower
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
    # Distances below are in palm lengths (wrist -> middle MCP), so they hold at any camera distance
    CLICK_THRESHOLD        = 0.20          # max thumb-to-fingertip distance for a pinch
    DOUBLE_CLICK_INTERVAL  = 0.85          # max seconds between two pinch starts (a human double-pinch is slower
                                           # than the OS double-click time; see CursorController.double_click)
    CLICK_LOCK_TIME        = 0.85          # cursor frozen this long after a click so both pinches hit one pixel
                                           # (keep >= DOUBLE_CLICK_INTERVAL)
    FAST_DOUBLE_CLICK_GAP  = 0.05          # seconds between the two clicks sent for a DOUBLE_CLICK
    # Scroll is joystick-style: hold the hand above/below where the gesture started.
    SCROLL_DEADZONE        = 0.15          # palm lengths around the anchor where nothing scrolls
    SCROLL_FULL_SPEED_OFFSET = 0.8         # palm lengths: at and beyond this offset speed is SCROLL_MAX_SPEED
    SCROLL_MAX_SPEED       = 15.0          # notches/s at full speed
    SCROLL_EXPONENT        = 1.5           # >1: gentle near the dead zone (reading speed), steeper further out
    SCROLL_ANCHOR_GRACE    = 0.6           # seconds the SCROLL pose may drop out before the anchor is forgotten
    SCROLL_NATURAL         = False         # False: hand below anchor = scroll down; True: inverted
    SCROLL_MAX_DT          = 0.1           # seconds; longer frame gaps are clamped (no jump after a stall)
    DRAW_MODE_DISTANCE     = 0.05          # index–middle gap to enter draw mode
    SCREENSHOT_HOLD_TIME   = 1.0           # seconds gesture must be held
    PLAY_PAUSE_HOLD_TIME   = 0.5           # seconds the 3-finger pose must be held

    # ── Volume / Brightness ───────────────────────────────────────────────────
    VOLUME_MIN_DIST        = 0.10          # thumb-pinky spread (palm lengths) = 0 %
    VOLUME_MAX_DIST        = 1.60          # ... = 100 %
    BRIGHTNESS_MIN_DIST    = 0.10          # thumb-ring spread (palm lengths) = min
    BRIGHTNESS_MAX_DIST    = 1.30          # ... = max
    VOLUME_STEP            = 0.03          # min change (0–1) before the mixer is touched
    BRIGHTNESS_STEP        = 0.03          # min change (0–1) before the display is touched

    # ── Drawing canvas ────────────────────────────────────────────────────────
    DRAW_COLOR             = (0, 255, 180)  # neon-green
    DRAW_THICKNESS         = 4
    DRAW_ERASER_RADIUS     = 30

    # ── Window ────────────────────────────────────────────────────────────────
    WINDOW_SCALE           = 1.5           # initial window size = frame size x this (640x480 -> 960x720)

    # ── UI overlay ────────────────────────────────────────────────────────────
    HUD_FONT               = 0             # cv2.FONT_HERSHEY_SIMPLEX (numeric so config needs no OpenCV)
    HUD_SCALE              = 0.65
    HUD_THICKNESS          = 2
    HUD_COLOR_PRIMARY      = (255, 255, 255)
    HUD_COLOR_ACCENT       = (0, 255, 200)
    HUD_COLOR_WARNING      = (0, 100, 255)

    # ── Screenshot ────────────────────────────────────────────────────────────
    SCREENSHOT_SAVE_DIR    = "screenshots"
    SCREENSHOT_COOLDOWN    = 5.0           # seconds before another screenshot is allowed
    # GNOME on Wayland refuses programmatic screenshots, so the uinput backend
    # types GNOME's own shortcut instead (gsettings get org.gnome.shell.keybindings
    # screenshot).  Names: ctrl, shift, alt, super, print.  Empty tuple = disabled.
    # GNOME saves these to ~/Pictures/Screenshots, not to SCREENSHOT_SAVE_DIR.
    SCREENSHOT_KEYS        = ("shift", "print")

    # ── Media keys ────────────────────────────────────────────────────────────
    MEDIA_COOLDOWN         = 1.0           # seconds between media key presses

    # ── Privacy mode (demos) ──────────────────────────────────────────────────
    PRIVACY_START          = False         # start with the camera image blurred (toggle with 'p')
    PRIVACY_BLUR_DOWNSCALE = 16            # image is shrunk this many times before blurring (bigger = blurrier)

    # ── Hand-loss recovery ────────────────────────────────────────────────────
    HAND_LOSS_GRACE_FRAMES = 5             # frames to wait before resetting state