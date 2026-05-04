"""
Configuration Module
==================
Centralized configuration and constants for the gesture control system.
All settings can be modified in one place for easy tuning and customization.
"""

import platform
from screeninfo import get_monitors

# ============================================================================
# SYSTEM CONFIGURATION
# ============================================================================

# Get primary monitor resolution
monitor = get_monitors()[0]
SCREEN_WIDTH, SCREEN_HEIGHT = monitor.width, monitor.height

# Camera settings
CAMERA_ID = 0  # Default camera device
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# Operating System
OPERATING_SYSTEM = platform.system()  # 'Windows', 'Darwin' (macOS), 'Linux'

# ============================================================================
# PERFORMANCE & OPTIMIZATION SETTINGS
# ============================================================================

# Smoothing parameters for cursor control
SMOOTHING_FRAMES = 5  # Number of frames to average for cursor position
MAX_CURSOR_SPEED = 100  # Maximum pixels per frame (for velocity limiting)

# Frame rate target
TARGET_FPS = 30
MIN_FPS = 20

# ============================================================================
# HAND DETECTION SETTINGS
# ============================================================================

# MediaPipe confidence thresholds
HAND_DETECTION_CONFIDENCE = 0.7  # Detection confidence (0.0-1.0)
HAND_TRACKING_CONFIDENCE = 0.7   # Tracking confidence (0.0-1.0)
MAX_HANDS = 2  # Maximum number of hands to track simultaneously

# Hand loss detection
HAND_LOSS_THRESHOLD = 5  # Frames before considering hand as lost

# ============================================================================
# GESTURE RECOGNITION SETTINGS
# ============================================================================

# Distance thresholds (in pixels)
CLICK_THRESHOLD = 40  # Distance threshold for click gesture
PINCH_THRESHOLD = 40  # Distance threshold for pinch gestures
SCROLL_THRESHOLD = 100  # Y-axis movement threshold for scrolling

# Gesture timing
CLICK_COOLDOWN = 0.5  # Seconds between clicks
SCREENSHOT_COOLDOWN = 2.0  # Seconds between screenshots
VOLUME_COOLDOWN = 0.1  # Seconds between volume adjustments
BRIGHTNESS_COOLDOWN = 0.1  # Seconds between brightness adjustments
SCROLL_COOLDOWN = 0.05  # Seconds between scroll events
ZOOM_COOLDOWN = 0.3  # Seconds between zoom commands
MEDIA_COOLDOWN = 1.0  # Seconds between media control commands

# Gesture hold detection
GESTURE_HOLD_TIME = 0.5  # Time to hold gesture before activation
SCREENSHOT_HOLD_TIME = 1.0  # Time to hold for screenshot
MEDIA_HOLD_TIME = 0.8  # Time to hold for media control

# ============================================================================
# VOLUME & BRIGHTNESS CONTROL
# ============================================================================

# Volume settings
VOLUME_MIN, VOLUME_MAX = 0, 100
VOLUME_STEP = 5  # Increment/decrement step
VOLUME_RANGE_MIN_PX = 20  # Minimum pixel distance for volume
VOLUME_RANGE_MAX_PX = 200  # Maximum pixel distance for volume

# Brightness settings
BRIGHTNESS_MIN, BRIGHTNESS_MAX = 0, 100
BRIGHTNESS_STEP = 5  # Increment/decrement step
BRIGHTNESS_RANGE_MIN_PX = 20  # Minimum pixel distance for brightness
BRIGHTNESS_RANGE_MAX_PX = 200  # Maximum pixel distance for brightness

# ============================================================================
# DRAWING SETTINGS
# ============================================================================

DRAW_COLOR = (0, 255, 0)  # BGR format (Green)
DRAW_THICKNESS = 5  # Line thickness in pixels
DRAW_CANVAS_NAME = "Virtual Canvas"
DRAW_SMOOTHING = 3  # Smoothing factor for drawn lines

# ============================================================================
# SCROLLING SETTINGS
# ============================================================================

SCROLL_SENSITIVITY = 5  # Pixels per scroll wheel unit
SCROLL_DIRECTION_NATURAL = True  # True = natural scrolling (like macOS)
SCROLL_NOISE_THRESHOLD = 10  # Minimum movement to trigger scroll

# ============================================================================
# ZOOM SETTINGS
# ============================================================================

ZOOM_THRESHOLD_IN = 150  # Pixel distance for zoom in
ZOOM_THRESHOLD_OUT = 80  # Pixel distance for zoom out
ZOOM_COOLDOWN_MS = 300  # Milliseconds between zoom commands

# ============================================================================
# UI & VISUAL FEEDBACK
# ============================================================================

# Font settings
FONT_FACE = 2  # cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.7
FONT_THICKNESS = 2
FONT_COLOR_TEXT = (255, 255, 255)  # White
FONT_COLOR_MODE = (0, 255, 0)  # Green
FONT_COLOR_ERROR = (0, 0, 255)  # Red
FONT_COLOR_WARNING = (0, 255, 255)  # Yellow
FONT_COLOR_SUCCESS = (0, 255, 0)  # Green

# Display positions
TEXT_POSITION_MODE = (10, 30)  # Top-left
TEXT_POSITION_FEEDBACK = (10, 60)  # Below mode
TEXT_POSITION_FPS = (FRAME_WIDTH - 120, 30)  # Top-right
TEXT_POSITION_DEBUG = (10, FRAME_HEIGHT - 20)  # Bottom-left

# ============================================================================
# LOGGING & DEBUG
# ============================================================================

DEBUG_MODE = False  # Print debug information
SHOW_LANDMARKS = True  # Show hand landmarks on camera feed
SHOW_FPS = True  # Display FPS counter
LOG_FILE = "gesture_control.log"
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

# ============================================================================
# ERROR HANDLING
# ============================================================================

ENABLE_GESTURE_DEBOUNCING = True  # Prevent rapid repeated activations
MAX_RETRIES_ON_ERROR = 3  # Number of retries before giving up
ERROR_RECOVERY_TIMEOUT = 2.0  # Seconds to wait before retrying

# ============================================================================
# KEYBOARD SHORTCUTS
# ============================================================================

KEY_EXIT = ord('q')  # Press 'q' to quit
KEY_CLEAR_CANVAS = ord('c')  # Press 'c' to clear drawing canvas
KEY_PAUSE = ord('p')  # Press 'p' to pause/resume
KEY_TOGGLE_DEBUG = ord('d')  # Press 'd' to toggle debug mode
KEY_RESET = ord('r')  # Press 'r' to reset all states

# ============================================================================
# FEATURE FLAGS
# ============================================================================

# Enable/disable specific features
FEATURE_CURSOR_CONTROL = True
FEATURE_CLICK = True
FEATURE_VOLUME_CONTROL = True
FEATURE_BRIGHTNESS_CONTROL = True
FEATURE_SCROLLING = True
FEATURE_DRAWING = True
FEATURE_SCREENSHOT = True
FEATURE_ZOOM = True
FEATURE_MEDIA_CONTROL = True
FEATURE_MULTI_HAND = True
FEATURE_HAND_LOSS_RECOVERY = True

# ============================================================================
# PLATFORM-SPECIFIC SETTINGS
# ============================================================================

if OPERATING_SYSTEM == "Windows":
    AUDIO_DEVICE = "Master"  # Windows audio device
    BRIGHTNESS_MONITOR = 0  # Monitor index for brightness control
elif OPERATING_SYSTEM == "Darwin":  # macOS
    AUDIO_DEVICE = "output"
    BRIGHTNESS_MONITOR = 0
else:  # Linux
    AUDIO_DEVICE = "Master"  # ALSA audio device
    ALSA_CARD = "0"  # Sound card index
    BRIGHTNESS_DEVICE = "eDP-1"  # Output device for brightness
    XRANDR_TIMEOUT = 5  # Timeout for xrandr commands

# ============================================================================
# VALIDATION & CONSTRAINTS
# ============================================================================

# Ensure valid ranges
assert 0.0 <= HAND_DETECTION_CONFIDENCE <= 1.0, "Detection confidence must be 0-1"
assert 0.0 <= HAND_TRACKING_CONFIDENCE <= 1.0, "Tracking confidence must be 0-1"
assert 1 <= MAX_HANDS <= 2, "Max hands must be 1 or 2"
assert SMOOTHING_FRAMES >= 1, "Smoothing frames must be >= 1"
assert VOLUME_MIN <= VOLUME_MAX, "Volume min must be <= max"
assert BRIGHTNESS_MIN <= BRIGHTNESS_MAX, "Brightness min must be <= max"

print("[CONFIG] Configuration loaded successfully")
print(f"[CONFIG] Screen resolution: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
print(f"[CONFIG] Operating system: {OPERATING_SYSTEM}")
print(f"[CONFIG] Camera: {FRAME_WIDTH}x{FRAME_HEIGHT}")