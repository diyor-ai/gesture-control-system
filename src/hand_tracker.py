"""
Hand Detection Module
====================
Handles real-time hand detection, landmark tracking, and finger state analysis.
Uses MediaPipe Hands for robust multi-hand detection.
"""

import mediapipe as mp
import numpy as np
from config import (
    HAND_DETECTION_CONFIDENCE, HAND_TRACKING_CONFIDENCE, MAX_HANDS,
    FRAME_WIDTH, FRAME_HEIGHT
)
from src.utils.utils import calculate_distance, get_pixel_coordinates

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=MAX_HANDS,
    min_detection_confidence=HAND_DETECTION_CONFIDENCE,
    min_tracking_confidence=HAND_TRACKING_CONFIDENCE
)


class HandTracker:
    """
    High-level interface for hand detection and tracking.
    Provides hand landmarks, finger states, and gesture-relevant metrics.
    """

    def __init__(self):
        """Initialize the hand tracker."""
        self.hand_landmarks = None
        self.handedness = None  # Left or Right
        self.num_hands = 0
        self.detection_confidence = 0.0

    def process_frame(self, rgb_frame):
        """
        Process a frame and detect hands.

        Args:
            rgb_frame: RGB frame from camera (not BGR)

        Returns:
            bool: True if hands detected, False otherwise
        """
        results = hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            self.hand_landmarks = results.multi_hand_landmarks
            self.handedness = results.multi_handedness
            self.num_hands = len(results.multi_hand_landmarks)
            return True
        else:
            self.hand_landmarks = None
            self.handedness = None
            self.num_hands = 0
            return False

    def get_landmarks(self, hand_index=0):
        """
        Get hand landmarks for a specific hand.

        Args:
            hand_index (int): Index of hand (0 or 1)

        Returns:
            Hand landmarks or None if not available
        """
        if self.hand_landmarks and hand_index < len(self.hand_landmarks):
            return self.hand_landmarks[hand_index]
        return None

    def get_handedness(self, hand_index=0):
        """
        Get hand chirality (Left or Right).

        Args:
            hand_index (int): Index of hand (0 or 1)

        Returns:
            str: 'Left', 'Right', or None
        """
        if self.handedness and hand_index < len(self.handedness):
            return self.handedness[hand_index].classification[0].label
        return None

    def draw_landmarks(self, frame):
        """
        Draw hand landmarks and connections on frame.

        Args:
            frame: OpenCV frame to draw on

        Returns:
            frame: Modified frame with landmarks
        """
        if self.hand_landmarks:
            for hand_landmarks in self.hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=1),
                    mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                )
        return frame


def get_finger_states(hand_landmarks):
    """
    Determine which fingers are extended based on landmarks.
    Compares tip position with PIP joint position.

    Args:
        hand_landmarks: MediaPipe hand landmarks

    Returns:
        list: [thumb, index, middle, ring, pinky] - True if extended
    """
    landmarks = hand_landmarks.landmark

    # Determine hand chirality (left vs right)
    # Use wrist and thumb CMC positions
    wrist = landmarks[mp_hands.HandLandmark.WRIST]
    thumb_cmc = landmarks[mp_hands.HandLandmark.THUMB_CMC]
    is_right_hand = thumb_cmc.x < wrist.x

    fingers = []

    # Thumb (special handling for left/right)
    thumb_tip = landmarks[mp_hands.HandLandmark.THUMB_TIP]
    thumb_ip = landmarks[mp_hands.HandLandmark.THUMB_IP]

    if is_right_hand:
        fingers.append(thumb_tip.x < thumb_ip.x)
    else:
        fingers.append(thumb_tip.x > thumb_ip.x)

    # Other fingers (check if tip is above PIP joint)
    finger_tips = [
        mp_hands.HandLandmark.INDEX_FINGER_TIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
        mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.PINKY_TIP
    ]

    finger_pips = [
        mp_hands.HandLandmark.INDEX_FINGER_PIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_PIP,
        mp_hands.HandLandmark.RING_FINGER_PIP,
        mp_hands.HandLandmark.PINKY_PIP
    ]

    for tip, pip in zip(finger_tips, finger_pips):
        fingers.append(landmarks[tip].y < landmarks[pip].y)

    return fingers


def get_finger_position(hand_landmarks, finger_type):
    """
    Get pixel position of a specific finger tip.

    Args:
        hand_landmarks: MediaPipe hand landmarks
        finger_type (str): 'thumb', 'index', 'middle', 'ring', or 'pinky'

    Returns:
        tuple: (x, y) pixel coordinates or None
    """
    finger_tips = {
        'thumb': mp_hands.HandLandmark.THUMB_TIP,
        'index': mp_hands.HandLandmark.INDEX_FINGER_TIP,
        'middle': mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
        'ring': mp_hands.HandLandmark.RING_FINGER_TIP,
        'pinky': mp_hands.HandLandmark.PINKY_TIP,
        'wrist': mp_hands.HandLandmark.WRIST,
        'palm': mp_hands.HandLandmark.MIDDLE_FINGER_MCP
    }

    if finger_type not in finger_tips:
        return None

    landmark = hand_landmarks.landmark[finger_tips[finger_type]]
    return get_pixel_coordinates(landmark)


def get_finger_distance(hand_landmarks, finger1, finger2):
    """
    Get distance between two fingers.

    Args:
        hand_landmarks: MediaPipe hand landmarks
        finger1 (str): First finger ('thumb', 'index', etc.)
        finger2 (str): Second finger

    Returns:
        float: Distance in pixels or None
    """
    pos1 = get_finger_position(hand_landmarks, finger1)
    pos2 = get_finger_position(hand_landmarks, finger2)

    if pos1 and pos2:
        return calculate_distance(pos1, pos2)
    return None


def get_hand_center(hand_landmarks):
    """
    Get the center point of the hand (average of all landmarks).

    Args:
        hand_landmarks: MediaPipe hand landmarks

    Returns:
        tuple: (x, y) center position in pixels
    """
    landmarks = hand_landmarks.landmark
    x_coords = [lm.x for lm in landmarks]
    y_coords = [lm.y for lm in landmarks]

    center_x = int(np.mean(x_coords) * FRAME_WIDTH)
    center_y = int(np.mean(y_coords) * FRAME_HEIGHT)

    return center_x, center_y


def get_hand_bounding_box(hand_landmarks):
    """
    Get bounding box of hand in pixel coordinates.

    Args:
        hand_landmarks: MediaPipe hand landmarks

    Returns:
        tuple: (x_min, y_min, x_max, y_max) in pixels
    """
    landmarks = hand_landmarks.landmark
    x_coords = [lm.x * FRAME_WIDTH for lm in landmarks]
    y_coords = [lm.y * FRAME_HEIGHT for lm in landmarks]

    x_min, x_max = int(min(x_coords)), int(max(x_coords))
    y_min, y_max = int(min(y_coords)), int(max(y_coords))

    return x_min, y_min, x_max, y_max


def get_hand_size(hand_landmarks):
    """
    Get approximate size of hand based on bounding box.

    Args:
        hand_landmarks: MediaPipe hand landmarks

    Returns:
        float: Size in pixels (width * height)
    """
    x_min, y_min, x_max, y_max = get_hand_bounding_box(hand_landmarks)
    width = x_max - x_min
    height = y_max - y_min
    return width * height


def is_hand_open(hand_landmarks):
    """
    Check if hand is open (most fingers extended).

    Args:
        hand_landmarks: MediaPipe hand landmarks

    Returns:
        bool: True if hand is mostly open
    """
    fingers = get_finger_states(hand_landmarks)
    extended_count = sum(fingers)
    return extended_count >= 4  # At least 4 fingers extended


def is_fist(hand_landmarks):
    """
    Check if hand is in fist position (all fingers closed).

    Args:
        hand_landmarks: MediaPipe hand landmarks

    Returns:
        bool: True if hand is in fist
    """
    fingers = get_finger_states(hand_landmarks)
    extended_count = sum(fingers)
    return extended_count == 0  # No fingers extended


def get_hand_velocity(prev_position, curr_position, time_delta=1.0):
    """
    Calculate hand velocity based on position change over time.

    Args:
        prev_position (tuple): Previous position (x, y)
        curr_position (tuple): Current position (x, y)
        time_delta (float): Time elapsed in seconds

    Returns:
        float: Velocity in pixels per second
    """
    if prev_position is None:
        return 0.0

    distance = calculate_distance(prev_position, curr_position)
    velocity = distance / time_delta if time_delta > 0 else 0.0
    return velocity


print("[HAND_TRACKER] Hand detection module loaded successfully")