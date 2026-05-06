"""
hand_tracker.py – MediaPipe Hands wrapper.

Provides a clean interface for detecting hands and extracting
normalised landmarks from each frame.
"""

import cv2
import mediapipe as mp
import numpy as np
from modules.config import Config


class HandTracker:
    """
    Wraps MediaPipe Hands to detect, track and annotate hand landmarks.

    Parameters
    ----------
    cfg : Config
        Shared application configuration object.
    """

    # MediaPipe landmark indices (for readable code in other modules)
    WRIST          = 0
    THUMB_TIP      = 4
    INDEX_MCP      = 5
    INDEX_TIP      = 8
    MIDDLE_TIP     = 12
    RING_TIP       = 16
    PINKY_TIP      = 20
    INDEX_PIP      = 6
    MIDDLE_PIP     = 10
    RING_PIP       = 14
    PINKY_PIP      = 18
    THUMB_IP       = 3
    INDEX_DIP      = 7
    MIDDLE_DIP     = 11
    RING_DIP       = 15
    PINKY_DIP      = 19
    INDEX_MCP      = 5   # noqa: F811 (redefined intentionally for clarity)
    MIDDLE_MCP     = 9
    RING_MCP       = 13
    PINKY_MCP      = 17

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._mp_hands = mp.solutions.hands
        self._mp_draw  = mp.solutions.drawing_utils
        self._mp_styles = mp.solutions.drawing_styles

        self.hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=cfg.MAX_NUM_HANDS,
            min_detection_confidence=cfg.DETECTION_CONFIDENCE,
            min_tracking_confidence=cfg.TRACKING_CONFIDENCE,
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def process(self, frame: np.ndarray) -> tuple[np.ndarray, list[dict]]:
        """
        Run hand detection on a BGR frame.

        Returns
        -------
        frame      : annotated BGR frame
        hands_data : list of dicts, each containing
                     'landmarks' (list of (x, y, z) normalised floats)
                     'label'     ("Left" | "Right")
                     'bbox'      (x_min, y_min, x_max, y_max) in pixels
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)
        rgb.flags.writeable = True

        hands_data: list[dict] = []
        h, w = frame.shape[:2]

        if results.multi_hand_landmarks:
            for hand_lms, hand_info in zip(
                results.multi_hand_landmarks,
                results.multi_handedness,
            ):
                # Draw skeleton
                self._mp_draw.draw_landmarks(
                    frame,
                    hand_lms,
                    self._mp_hands.HAND_CONNECTIONS,
                    self._mp_styles.get_default_hand_landmarks_style(),
                    self._mp_styles.get_default_hand_connections_style(),
                )

                # Extract normalised coordinates (x, y, z)
                landmarks = [
                    (lm.x, lm.y, lm.z) for lm in hand_lms.landmark
                ]

                # Bounding box in pixel coords
                xs = [lm.x * w for lm in hand_lms.landmark]
                ys = [lm.y * h for lm in hand_lms.landmark]
                bbox = (
                    int(min(xs)) - 10,
                    int(min(ys)) - 10,
                    int(max(xs)) + 10,
                    int(max(ys)) + 10,
                )

                label = hand_info.classification[0].label  # "Left" | "Right"

                hands_data.append({
                    "landmarks": landmarks,
                    "label":     label,
                    "bbox":      bbox,
                })

        return frame, hands_data

    # ── Static helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def distance(lm_a: tuple, lm_b: tuple) -> float:
        """Euclidean distance between two normalised landmarks."""
        return float(np.linalg.norm(
            np.array(lm_a[:2]) - np.array(lm_b[:2])
        ))

    @staticmethod
    def fingers_up(landmarks: list[tuple]) -> list[bool]:
        """
        Return a boolean list [thumb, index, middle, ring, pinky]
        indicating which fingers are extended.
        """
        tips   = [4, 8, 12, 16, 20]
        pips   = [3, 6, 10, 14, 18]  # joint one below the tip
        up     = []

        # Thumb – compare x-axis (mirrored frame)
        up.append(landmarks[4][0] > landmarks[3][0])

        # Other fingers – compare y-axis (lower y = higher on screen = extended)
        for tip, pip in zip(tips[1:], pips[1:]):
            up.append(landmarks[tip][1] < landmarks[pip][1])

        return up