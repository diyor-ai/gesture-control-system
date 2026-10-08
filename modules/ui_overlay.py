"""
ui_overlay.py – Heads-Up Display (HUD) and gesture label renderer.

Draws on the camera frame:
* Top-left  : FPS counter and active mode
* Top-right : Keyboard shortcut legend
* Per-hand  : Current gesture label with coloured badge
"""

import cv2
import numpy as np
from modules.config import Config


# Colour map for gesture categories
_GESTURE_COLORS: dict[str, tuple[int, int, int]] = {
    "MOVE_CURSOR":       (255, 255, 255),
    "CLICK":             (0,   255, 100),
    "DOUBLE_CLICK":      (0,   200, 255),
    "RIGHT_CLICK":       (255, 150,   0),
    "SCROLL":            (100, 200, 255),
    "VOLUME":            (255,  80, 200),
    "DRAW":              (0,   255, 180),
    "SCREENSHOT":        (255, 255,   0),
    "DRAG_WINDOW":       (200, 100, 255),
    "ZOOM":              (0,   180, 255),
    "MEDIA_PLAY_PAUSE":  (255, 200,  50),
    "MEDIA_NEXT":        (255, 200,  50),
    "MEDIA_PREV":        (255, 200,  50),
    "BRIGHTNESS":        (255, 220,   0),
    "IDLE":              (130, 130, 130),
    "SCREENSHOT_HOLD":   (255, 255,   0),
}

_LEGEND = [
    "'q'  – Quit",
    "'d'  – Toggle Draw",
    "'r'  – Clear Canvas",
]


class UIOverlay:
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg

    def draw_hud(self, frame: np.ndarray, fps: float, active_mode: str) -> None:
        """Render FPS, active mode, and shortcut legend onto the frame."""
        h, w = frame.shape[:2]
        font       = cv2.FONT_HERSHEY_SIMPLEX
        scale      = 0.60
        thickness  = 1
        pad        = 12

        # ── Semi-transparent top bar ──────────────────────────────────────────
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 45), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        # FPS
        fps_color = (0, 255, 100) if fps >= 25 else (0, 100, 255)
        cv2.putText(frame, f"FPS: {fps:.1f}", (pad, 30),
                    font, scale, fps_color, thickness)

        # Active mode
        mode_color = _GESTURE_COLORS.get(active_mode, (200, 200, 200))
        mode_str   = f"Mode: {active_mode}"
        cv2.putText(frame, mode_str, (w // 2 - 120, 30),
                    font, scale, mode_color, thickness)

        # Legend (bottom-left)
        for i, line in enumerate(_LEGEND):
            y = h - pad - (len(_LEGEND) - i - 1) * 22
            cv2.putText(frame, line, (pad, y),
                        font, 0.50, (180, 180, 180), 1)

    def draw_gesture_label(
        self,
        frame: np.ndarray,
        gesture: str,
        hand_label: str,
    ) -> None:
        """Draw the current gesture name near the hand."""
        if gesture in ("IDLE", ""):
            return

        h, w = frame.shape[:2]
        color  = _GESTURE_COLORS.get(gesture, (255, 255, 255))
        label  = f"[{hand_label}] {gesture}"

        # Position: top or bottom depending on hand label
        x = 20 if hand_label == "Right" else w - 280
        y = 90

        # Badge background
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        cv2.rectangle(frame, (x - 6, y - th - 6), (x + tw + 6, y + 4),
                      (20, 20, 20), -1)
        cv2.rectangle(frame, (x - 6, y - th - 6), (x + tw + 6, y + 4),
                      color, 1)

        cv2.putText(frame, label, (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

    def draw_debug(
        self,
        frame: np.ndarray,
        debug: dict,
        fps: float,
        avg_fps: float,
    ) -> None:
        """
        --debug overlay: per-hand finger states, raw / stable pose and the
        gesture being dispatched, plus instantaneous and average FPS.
        """
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX

        frame_ms = 1000.0 / max(fps, 1e-6)
        cv2.putText(frame, f"[debug] fps {fps:5.1f}  avg {avg_fps:5.1f}  frame {frame_ms:5.1f} ms",
                    (12, h - 90), font, 0.50, (0, 255, 255), 1)

        for hand_label, info in debug.items():
            x = 20 if hand_label == "Right" else w - 360
            y = 130
            role = "primary" if info["primary"] else "secondary"
            cv2.putText(frame, f"{hand_label} hand ({role})", (x, y),
                        font, 0.55, (0, 255, 255), 1)

            # One letter per finger: bright when extended, dim when curled
            for i, (name, up) in enumerate(zip("TIMRP", info["fingers"])):
                colour = (0, 255, 100) if up else (110, 110, 110)
                cv2.putText(frame, f"{name}:{int(up)}", (x + i * 52, y + 26),
                            font, 0.55, colour, 2)

            cv2.putText(frame, f"raw:    {info['raw']}", (x, y + 52), font, 0.50, (220, 220, 220), 1)
            cv2.putText(frame, f"stable: {info['stable']}", (x, y + 74), font, 0.50, (220, 220, 220), 1)
            cv2.putText(frame, f"pinch idx {info['pinch_index']:.2f}  mid {info['pinch_middle']:.2f}"
                        f"  (click < {self._cfg.CLICK_THRESHOLD:.2f})", (x, y + 118), font, 0.45, (180, 180, 180), 1)
            cv2.putText(frame, f"gesture: {info['gesture']}", (x, y + 96), font, 0.50,
                        _GESTURE_COLORS.get(info["gesture"], (255, 255, 255)), 1)
