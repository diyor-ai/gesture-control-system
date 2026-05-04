"""
Click Handler Module
===================
Manages mouse click functionality triggered by specific hand gestures.
Includes debouncing, cooldown management, and click confirmation.
"""

import pyautogui
import cv2
import time
from hand_tracker import get_finger_distance
from config import CLICK_THRESHOLD, CLICK_COOLDOWN, FEATURE_CLICK
from config import FONT_FACE, FONT_SCALE, FONT_THICKNESS, TEXT_POSITION_FEEDBACK
from src.utils.utils import StateTracker


class ClickHandler:
    """
    Manages mouse click events with debouncing and cooldown.
    Prevents accidental clicks through timeout management.
    """

    def __init__(self, cooldown_time=CLICK_COOLDOWN):
        """
        Initialize click handler.

        Args:
            cooldown_time (float): Minimum time between clicks in seconds
        """
        self.cooldown_time = cooldown_time
        self.last_click_time = 0
        self.enabled = FEATURE_CLICK
        self.click_count = 0
        self.state_tracker = StateTracker()

    def process(self, hand_landmarks):
        """
        Process hand landmarks and execute click if gesture detected.

        Args:
            hand_landmarks: MediaPipe hand landmarks

        Returns:
            bool: True if click executed, False otherwise
        """
        if not self.enabled or hand_landmarks is None:
            return False

        # Get thumb-index distance
        distance = get_finger_distance(hand_landmarks, 'thumb', 'index')

        if distance is None or distance >= CLICK_THRESHOLD:
            return False

        # Check cooldown
        current_time = time.time()
        if current_time - self.last_click_time < self.cooldown_time:
            return False

        # Perform click
        try:
            pyautogui.click()
            self.last_click_time = current_time
            self.click_count += 1
            self.state_tracker.update_activation_time('click')
            return True
        except Exception as e:
            print(f"[ERROR] Click execution failed: {e}")
            return False

    def double_click(self):
        """
        Perform a double click.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            pyautogui.doubleClick()
            self.click_count += 2
            return True
        except Exception as e:
            print(f"[ERROR] Double click failed: {e}")
            return False

    def right_click(self):
        """
        Perform a right click.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            pyautogui.rightClick()
            self.click_count += 1
            return True
        except Exception as e:
            print(f"[ERROR] Right click failed: {e}")
            return False

    def draw_feedback(self, frame, clicked=False):
        """
        Draw click feedback on frame.

        Args:
            frame: OpenCV frame
            clicked (bool): Whether click just occurred

        Returns:
            frame: Modified frame
        """
        if clicked:
            color = (0, 0, 255)  # Red
            text = "CLICKED!"
        else:
            color = (255, 255, 0)  # Yellow
            text = f"Clicks: {self.click_count}"

        cv2.putText(frame, text, TEXT_POSITION_FEEDBACK,
                    FONT_FACE, FONT_SCALE, color, FONT_THICKNESS)
        return frame

    def enable(self):
        """Enable click handling."""
        self.enabled = True

    def disable(self):
        """Disable click handling."""
        self.enabled = False

    def reset(self):
        """Reset click handler."""
        self.last_click_time = 0
        self.click_count = 0
        self.state_tracker.reset()

    def get_statistics(self):
        """
        Get click handler statistics.

        Returns:
            dict: Statistics dictionary
        """
        return {
            'total_clicks': self.click_count,
            'last_click_time': self.last_click_time,
            'time_since_last_click': time.time() - self.last_click_time
        }

    def set_cooldown(self, cooldown_time):
        """
        Set new cooldown time.

        Args:
            cooldown_time (float): Cooldown in seconds
        """
        self.cooldown_time = cooldown_time


class AdvancedClickHandler:
    """
    Advanced click handler with multi-click and gesture-based selection.
    Supports single, double, and right-clicks with gesture recognition.
    """

    def __init__(self):
        """Initialize advanced click handler."""
        self.handlers = {
            'single': SingleClickHandler(),
            'double': DoubleClickHandler(),
            'right': RightClickHandler()
        }
        self.last_action = None

    def process_single_click(self, hand_landmarks):
        """Execute single click."""
        return self.handlers['single'].process(hand_landmarks)

    def process_double_click(self):
        """Execute double click."""
        return self.handlers['double'].perform()

    def process_right_click(self):
        """Execute right click."""
        return self.handlers['right'].perform()


class SingleClickHandler:
    """Handles single click gestures."""

    def __init__(self):
        self.last_click_time = 0
        self.cooldown = 0.5

    def process(self, hand_landmarks):
        """Process and execute single click."""
        distance = get_finger_distance(hand_landmarks, 'thumb', 'index')
        if distance and distance < CLICK_THRESHOLD:
            current_time = time.time()
            if current_time - self.last_click_time >= self.cooldown:
                pyautogui.click()
                self.last_click_time = current_time
                return True
        return False


class DoubleClickHandler:
    """Handles double click gestures."""

    def perform(self):
        """Execute double click."""
        try:
            pyautogui.doubleClick()
            return True
        except:
            return False


class RightClickHandler:
    """Handles right click gestures."""

    def perform(self):
        """Execute right click."""
        try:
            pyautogui.rightClick()
            return True
        except:
            return False


print("[CLICK] Click handler module loaded successfully")
