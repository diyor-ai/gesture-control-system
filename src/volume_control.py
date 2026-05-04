"""
Volume Control Module
====================
Manages system volume control using finger pinch gesture distance.
Supports cross-platform volume adjustment (Windows, macOS, Linux).
"""

import subprocess
import cv2
import time
from hand_tracker import get_finger_distance
from config import (
    OPERATING_SYSTEM, VOLUME_MIN, VOLUME_MAX, VOLUME_RANGE_MIN_PX, VOLUME_RANGE_MAX_PX,
    FEATURE_VOLUME_CONTROL, FONT_FACE, FONT_SCALE, FONT_THICKNESS, TEXT_POSITION_FEEDBACK
)
from src.utils.utils import map_range


class VolumeController:
    """
    Controls system volume using finger pinch distance.
    Provides cross-platform support for Windows, macOS, and Linux.
    """

    def __init__(self):
        """Initialize volume controller."""
        self.enabled = FEATURE_VOLUME_CONTROL
        self.current_volume = 50  # Default to 50%
        self.last_update_time = 0
        self.update_cooldown = 0.1  # Minimum time between updates
        self.volume_history = []
        self.max_history = 5

    def update(self, hand_landmarks):
        """
        Update system volume based on finger distance.

        Args:
            hand_landmarks: MediaPipe hand landmarks

        Returns:
            int: Current volume level (0-100), or None if failed
        """
        if not self.enabled or hand_landmarks is None:
            return None

        # Check cooldown
        current_time = time.time()
        if current_time - self.last_update_time < self.update_cooldown:
            return self.current_volume

        # Get thumb-index distance
        distance = get_finger_distance(hand_landmarks, 'thumb', 'index')
        if distance is None:
            return None

        # Map distance to volume
        volume = int(map_range(distance, VOLUME_RANGE_MIN_PX, VOLUME_RANGE_MAX_PX,
                               VOLUME_MIN, VOLUME_MAX))

        # Smooth volume with moving average
        self.volume_history.append(volume)
        if len(self.volume_history) > self.max_history:
            self.volume_history.pop(0)

        smoothed_volume = int(sum(self.volume_history) / len(self.volume_history))

        # Set system volume
        try:
            self._set_system_volume(smoothed_volume)
            self.current_volume = smoothed_volume
            self.last_update_time = current_time
            return smoothed_volume
        except Exception as e:
            print(f"[WARNING] Volume update failed: {e}")
            return None

    def _set_system_volume(self, volume):
        """
        Set system volume (platform-specific).

        Args:
            volume (int): Volume level (0-100)
        """
        volume = max(VOLUME_MIN, min(VOLUME_MAX, volume))

        if OPERATING_SYSTEM == "Darwin":  # macOS
            subprocess.run(['osascript', '-e',
                            f'set volume output volume {volume}'],
                           capture_output=True)

        elif OPERATING_SYSTEM == "Windows":
            try:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume_control = cast(interface, POINTER(IAudioEndpointVolume))
                volume_control.SetMasterVolumeLevelScalar(volume / 100, None)
            except:
                pass  # Silent fail if pycaw not available

        else:  # Linux
            subprocess.run(['amixer', '-D', 'pulse', 'sset', 'Master', f'{volume}%'],
                           capture_output=True)

    def increase_volume(self, amount=5):
        """Increase volume by amount."""
        new_volume = min(VOLUME_MAX, self.current_volume + amount)
        self._set_system_volume(new_volume)
        self.current_volume = new_volume

    def decrease_volume(self, amount=5):
        """Decrease volume by amount."""
        new_volume = max(VOLUME_MIN, self.current_volume - amount)
        self._set_system_volume(new_volume)
        self.current_volume = new_volume

    def set_volume(self, volume):
        """Set volume to specific level."""
        volume = max(VOLUME_MIN, min(VOLUME_MAX, volume))
        self._set_system_volume(volume)
        self.current_volume = volume

    def draw_feedback(self, frame, distance=None):
        """
        Draw volume feedback on frame.

        Args:
            frame: OpenCV frame
            distance (float): Finger distance (optional, for visualization)

        Returns:
            frame: Modified frame with feedback
        """
        text = f"Volume: {self.current_volume}%"
        cv2.putText(frame, text, TEXT_POSITION_FEEDBACK,
                    FONT_FACE, FONT_SCALE, (255, 165, 0), FONT_THICKNESS)

        # Draw volume bar
        bar_width = int((self.current_volume / VOLUME_MAX) * 200)
        cv2.rectangle(frame, (10, 90), (210, 110), (100, 100, 100), 2)
        cv2.rectangle(frame, (10, 90), (10 + bar_width, 110), (255, 165, 0), -1)

        return frame

    def enable(self):
        """Enable volume control."""
        self.enabled = True

    def disable(self):
        """Disable volume control."""
        self.enabled = False

    def reset(self):
        """Reset volume controller."""
        self.volume_history.clear()
        self.last_update_time = 0

    def get_volume(self):
        """Get current volume level."""
        return self.current_volume


class AdvancedVolumeController(VolumeController):
    """
    Advanced volume controller with additional features.
    Includes mute/unmute and preset levels.
    """

    def __init__(self):
        """Initialize advanced volume controller."""
        super().__init__()
        self.muted = False
        self.volume_before_mute = 50
        self.presets = {
            'silent': 0,
            'quiet': 25,
            'normal': 50,
            'loud': 75,
            'max': 100
        }

    def toggle_mute(self):
        """Toggle mute state."""
        if self.muted:
            self.set_volume(self.volume_before_mute)
            self.muted = False
        else:
            self.volume_before_mute = self.current_volume
            self.set_volume(0)
            self.muted = True
        return self.muted

    def set_preset(self, preset_name):
        """
        Set volume to preset level.

        Args:
            preset_name (str): 'silent', 'quiet', 'normal', 'loud', 'max'

        Returns:
            bool: True if preset found and applied
        """
        if preset_name in self.presets:
            self.set_volume(self.presets[preset_name])
            return True
        return False


print("[VOLUME] Volume control module loaded successfully")