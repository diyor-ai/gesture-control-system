"""
Cursor Control Module
====================
Handles real-time cursor movement with advanced smoothing and stabilization.
Provides jitter reduction for responsive yet stable cursor control.
"""

import pyautogui
import cv2
from hand_tracker import get_screen_coordinates
from config import FEATURE_CURSOR_CONTROL, FONT_FACE, FONT_SCALE, FONT_THICKNESS, FONT_COLOR_MODE, TEXT_POSITION_MODE
from src.utils.utils import PositionSmoother


class CursorController:
    """
    Controls mouse cursor with smooth, jitter-free movement.
    Uses MediaPipe landmarks for position tracking.
    """

    def __init__(self):
        """Initialize cursor controller."""
        self.smoother = PositionSmoother()
        self.enabled = FEATURE_CURSOR_CONTROL
        self.current_position = None
        self.previous_position = None
        self.movement_count = 0

    def update(self, hand_landmarks):
        """
        Update cursor position based on hand landmarks.

        Args:
            hand_landmarks: MediaPipe hand landmarks

        Returns:
            tuple: (screen_x, screen_y) of cursor, or None if failed
        """
        if not self.enabled or hand_landmarks is None:
            return None

        try:
            # Get index fingertip position in screen coordinates
            index_landmark = hand_landmarks.landmark[8]  # Index finger tip
            screen_x = int(index_landmark.x * 1920)  # Assume 1920 width
            screen_y = int(index_landmark.y * 1080)  # Assume 1080 height

            # Add to smoother
            self.smoother.add_position(screen_x, screen_y)

            # Get smoothed position
            smooth_x, smooth_y = self.smoother.get_smooth_position()

            if smooth_x is not None and smooth_y is not None:
                # Move cursor
                pyautogui.moveTo(smooth_x, smooth_y)

                self.previous_position = self.current_position
                self.current_position = (smooth_x, smooth_y)
                self.movement_count += 1

                return smooth_x, smooth_y

        except Exception as e:
            print(f"[ERROR] Cursor update failed: {e}")

        return None

    def draw_feedback(self, frame):
        """
        Draw cursor feedback on frame.

        Args:
            frame: OpenCV frame to draw on

        Returns:
            frame: Modified frame with feedback
        """
        if self.current_position:
            cv2.circle(frame, self.current_position, 5, (0, 255, 0), -1)

        cv2.putText(frame, "Mode: CURSOR", TEXT_POSITION_MODE,
                    FONT_FACE, FONT_SCALE, FONT_COLOR_MODE, FONT_THICKNESS)
        return frame

    def enable(self):
        """Enable cursor control."""
        self.enabled = True

    def disable(self):
        """Disable cursor control."""
        self.enabled = False

    def reset(self):
        """Reset cursor controller."""
        self.smoother.clear()
        self.current_position = None
        self.previous_position = None
        self.movement_count = 0

    def get_statistics(self):
        """
        Get cursor control statistics.

        Returns:
            dict: Statistics dictionary
        """
        return {
            'movement_count': self.movement_count,
            'current_position': self.current_position,
            'smoothing_active': len(self.smoother.buffer) > 0
        }


class AdvancedCursorController:
    """
    Advanced cursor controller with velocity limiting and acceleration control.
    Provides more natural cursor movement with adjustable responsiveness.
    """

    def __init__(self, max_speed=100, acceleration=0.8):
        """
        Initialize advanced cursor controller.

        Args:
            max_speed (int): Maximum cursor speed in pixels/frame
            acceleration (float): Acceleration factor (0-1)
        """
        self.smoother = PositionSmoother()
        self.max_speed = max_speed
        self.acceleration = acceleration
        self.velocity = (0, 0)
        self.enabled = FEATURE_CURSOR_CONTROL

    def update(self, hand_landmarks):
        """
        Update cursor with velocity control.

        Args:
            hand_landmarks: MediaPipe hand landmarks

        Returns:
            tuple: (screen_x, screen_y) or None
        """
        if not self.enabled or hand_landmarks is None:
            return None

        try:
            # Get target position
            index_landmark = hand_landmarks.landmark[8]
            target_x = int(index_landmark.x * 1920)
            target_y = int(index_landmark.y * 1080)

            # Apply smoothing
            self.smoother.add_position(target_x, target_y)
            smooth_x, smooth_y = self.smoother.get_smooth_position()

            if smooth_x is None:
                return None

            # Get current cursor position
            curr_x, curr_y = pyautogui.position()

            # Calculate velocity
            vel_x = (smooth_x - curr_x) * self.acceleration
            vel_y = (smooth_y - curr_y) * self.acceleration

            # Limit velocity
            speed_squared = vel_x ** 2 + vel_y ** 2
            max_speed_squared = self.max_speed ** 2

            if speed_squared > max_speed_squared:
                scale = (max_speed_squared / speed_squared) ** 0.5
                vel_x *= scale
                vel_y *= scale

            # Update velocity
            self.velocity = (vel_x, vel_y)

            # Calculate new position
            new_x = int(curr_x + vel_x)
            new_y = int(curr_y + vel_y)

            # Move cursor
            pyautogui.moveTo(new_x, new_y)

            return new_x, new_y

        except Exception as e:
            print(f"[ERROR] Advanced cursor update failed: {e}")

        return None

    def reset(self):
        """Reset controller state."""
        self.smoother.clear()
        self.velocity = (0, 0)


print("[CURSOR] Cursor control module loaded successfully")