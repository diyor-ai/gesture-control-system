"""
Advanced Gesture-Based Computer Control System
================================================
Author  : Mukhammaddiyor Abdulazimov
Date    : May 2026
Course  : Final Assessment Project

Entry point – initialises all modules and runs the main event loop.
"""

import argparse
import cv2
import time
import sys
from typing import List, Optional
from modules.camera import CameraError, read_frame
from modules.hand_tracker import HandTracker
from modules.cursor_controller import CursorController
from modules.gesture_engine import GestureEngine, HandLossGrace
from modules.volume_control import VolumeController
from modules.scroll_control import ScrollController
from modules.drawing_canvas import DrawingCanvas
from modules.screenshot import ScreenshotModule
from modules.window_mover import WindowMover
from modules.zoom_control import ZoomController
from modules.media_control import MediaController
from modules.brightness_control import BrightnessController
from modules.ui_overlay import UIOverlay
from modules.config import Config
from modules.input_backend import InputBackendError, create_backend


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Advanced Gesture Control System")
    parser.add_argument(
        "--debug", action="store_true",
        help="show finger states, raw/stable pose, detected gesture and FPS on screen",
    )
    return parser.parse_args(argv)


def main(debug: bool = False) -> None:
    """
    Main application loop.
    Captures webcam frames, processes hand landmarks,
    dispatches recognised gestures to the appropriate modules.
    """
    cfg = Config()

    # ── Initialise camera ─────────────────────────────────────────────────────
    cap = cv2.VideoCapture(cfg.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  cfg.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          cfg.TARGET_FPS)

    if not cap.isOpened():
        print("[ERROR] Cannot open camera. Check CAMERA_INDEX in config.py.")
        sys.exit(1)

    # ── Input injection (uinput on Wayland, PyAutoGUI elsewhere) ─────────────
    try:
        backend = create_backend(cfg)
    except InputBackendError as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)
    print(f"[INFO] Input backend: {backend.name}")

    # ── Initialise modules ────────────────────────────────────────────────────
    tracker    = HandTracker(cfg)
    cursor     = CursorController(cfg, backend)
    engine     = GestureEngine(cfg)
    volume     = VolumeController(cfg)
    scroller   = ScrollController(cfg, backend)
    canvas     = DrawingCanvas(cfg)
    screenshot = ScreenshotModule(cfg, backend)
    win_mover  = WindowMover(cfg)
    zoomer     = ZoomController(cfg, backend)
    media      = MediaController(cfg, backend)
    brightness = BrightnessController(cfg)
    overlay    = UIOverlay(cfg)

    hand_loss = HandLossGrace(cfg.HAND_LOSS_GRACE_FRAMES)

    # ── FPS tracking ─────────────────────────────────────────────────────────
    prev_time = time.time()
    fps_values: list[float] = []

    print("[INFO] Gesture Control System started. Press 'q' to quit.")
    print("[INFO] Press 'd' to toggle drawing canvas.")
    print("[INFO] Press 'r' to clear the drawing canvas.")

    while True:
        try:
            frame = read_frame(cap, cfg.CAMERA_MAX_READ_FAILURES, cfg.CAMERA_RETRY_DELAY)
        except CameraError as exc:
            print(f"[ERROR] {exc}")
            cap.release()
            cv2.destroyAllWindows()
            sys.exit(1)

        # Mirror so the display feels natural
        frame = cv2.flip(frame, 1)

        # ── Hand detection & landmark extraction ──────────────────────────────
        frame, hands_data = tracker.process(frame)

        # ── FPS calculation ───────────────────────────────────────────────────
        now = time.time()
        fps = 1.0 / max(now - prev_time, 1e-6)
        prev_time = now
        fps_values.append(fps)
        if len(fps_values) > 30:
            fps_values.pop(0)
        avg_fps = sum(fps_values) / len(fps_values)

        active: set = set()                              # gestures seen this frame

        if hands_data:
            for hand_info in hands_data:
                landmarks = hand_info["landmarks"]
                hand_label = hand_info["label"]          # "Left" | "Right"

                # ── Classify current gesture ──────────────────────────────────
                gesture = engine.classify(landmarks, hand_label, canvas_enabled=canvas._enabled)
                active.add(gesture)

                # ── Module dispatch ───────────────────────────────────────────
                if gesture == "MOVE_CURSOR":
                    cursor.move(landmarks)

                elif gesture == "CLICK":
                    cursor.click(landmarks)

                elif gesture == "DOUBLE_CLICK":
                    cursor.double_click(landmarks)

                elif gesture == "RIGHT_CLICK":
                    cursor.right_click(landmarks)

                elif gesture == "SCROLL":
                    scroller.scroll(landmarks, frame)

                elif gesture == "VOLUME":
                    volume.adjust(landmarks, frame)

                elif gesture == "DRAW":
                    canvas.draw(landmarks, frame)

                elif gesture == "SCREENSHOT":
                    screenshot.capture(frame)

                elif gesture == "DRAG_WINDOW":
                    win_mover.drag(landmarks)

                elif gesture == "ZOOM":
                    zoomer.pinch_zoom(landmarks, frame)

                elif gesture == "MEDIA_PLAY_PAUSE":
                    media.toggle_play_pause()

                elif gesture == "MEDIA_NEXT":
                    media.next_track()

                elif gesture == "MEDIA_PREV":
                    media.prev_track()

                elif gesture == "BRIGHTNESS":
                    brightness.adjust(landmarks, frame)

                # ── Draw gesture label on frame ───────────────────────────────
                overlay.draw_gesture_label(frame, gesture, hand_label)

            # A gesture that is no longer active must not leave stale state
            # behind (previous wrist position, pinch distance, pen position...)
            if "SCROLL" not in active:
                scroller.reset()
            if "ZOOM" not in active:
                zoomer.reset()
            if "DRAG_WINDOW" not in active:
                win_mover.on_hand_lost()
            if "DRAW" not in active:
                canvas.on_hand_lost()

        engine.end_frame()

        # Hand-loss recovery: ignore dropouts shorter than the grace period,
        # then reset every stateful module once.
        if hand_loss.update(bool(hands_data)):
            cursor.on_hand_lost()
            scroller.reset()
            zoomer.reset()
            win_mover.on_hand_lost()
            canvas.on_hand_lost()

        # ── Draw persistent canvas layer ──────────────────────────────────────
        frame = canvas.render(frame)

        # ── HUD overlay (FPS, active mode, instructions) ──────────────────────
        overlay.draw_hud(frame, avg_fps, engine.active_mode)
        if debug:
            overlay.draw_debug(frame, engine.debug, fps, avg_fps)

        cv2.imshow("Gesture Control System", frame)

        # ── Keyboard shortcuts ────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("d"):
            canvas.toggle()
        elif key == ord("r"):
            canvas.clear()

    # ── Clean up ──────────────────────────────────────────────────────────────
    cap.release()
    cv2.destroyAllWindows()
    volume.close()
    brightness.close()
    backend.close()
    print("[INFO] Gesture Control System shut down cleanly.")


if __name__ == "__main__":
    main(debug=parse_args().debug)