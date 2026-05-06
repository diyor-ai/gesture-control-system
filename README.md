# 🖐️ Advanced Gesture-Based Computer Control System

> Control your computer entirely through natural hand gestures — no mouse, no keyboard.  
> Built with Python · MediaPipe · OpenCV · PyAutoGUI

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Feature Matrix](#-feature-matrix)
- [System Architecture](#-system-architecture)
- [Gesture Reference](#-gesture-reference)
- [Installation](#-installation)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Configuration](#️-configuration)
- [Performance](#-performance)
- [Troubleshooting](#-troubleshooting)
- [Demo](#-demo)
- [Future Improvements](#-future-improvements)
- [References](#-references)

---

## 🔍 Overview

This project delivers a **real-time, gesture-driven computer interaction system** that uses a standard webcam to replace traditional mouse and keyboard input. It processes hand landmarks at ≥ 30 FPS using Google's MediaPipe framework and dispatches recognised gestures to dedicated modules for cursor control, volume, scrolling, drawing, screenshots, window management, zoom, media playback, and screen brightness.

| Metric | Value |
|--------|-------|
| Target FPS | ≥ 30 |
| Detected hands | Up to 2 simultaneous |
| Total gestures | 14 distinct actions |
| Lines of code | ~1 200 (documented) |
| Supported OS | Windows · macOS · Linux |

---

## ✅ Feature Matrix

| # | Feature | Gesture | Status |
|---|---------|---------|--------|
| 1 | **Cursor Movement** | Index finger extended | ✅ Core |
| 2 | **Single Click** | Index + Thumb pinch | ✅ Core |
| 3 | **Double Click** | Two rapid pinches | ✅ Core |
| 4 | **Right Click** | Middle + Thumb pinch | ✅ Core |
| 5 | **Volume Control** | Thumb + Pinky spread 🤙 | ✅ Mandatory |
| 6 | **Screen Scrolling** | Peace sign ✌ + wrist movement | ✅ Mandatory |
| 7 | **Finger Drawing** | Index only, canvas mode | ✅ Mandatory |
| 8 | **Screenshot** | All 5 fingers spread (hold 1 s) | ✅ Mandatory |
| 9 | **Window Movement** | Closed fist drag | ✅ Mandatory |
| 10 | **Zoom In/Out** | Thumb + Index pinch spread | ✅ Mandatory |
| 11 | **Media Play/Pause** | Flat palm | ✅ Mandatory |
| 12 | **Media Next/Prev** | Index + Pinky swipe (🤘) | ✅ Mandatory |
| 13 | **Brightness Control** | Thumb + Ring spread | ✅ Advanced |
| 14 | **Hand-Loss Recovery** | Automatic freeze on hand loss | ✅ Advanced |
| 15 | **Multi-Hand Support** | Up to 2 hands simultaneously | ✅ Advanced |
| 16 | **Real-time HUD** | FPS · mode · shortcuts overlay | ✅ Advanced |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         main.py (Event Loop)                        │
│  Camera → Flip → HandTracker → GestureEngine → Module Dispatch      │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
        ┌───────────▼────────────┐
        │     HandTracker        │  MediaPipe Hands
        │  (landmark extraction) │  21 keypoints per hand
        └───────────┬────────────┘
                    │ landmarks[]
        ┌───────────▼────────────┐
        │    GestureEngine       │  Rule-based classifier
        │  (stateful classifier) │  + timing logic
        └───────────┬────────────┘
                    │ gesture string
          ┌─────────┼──────────────────────────────┐
          ▼         ▼         ▼                     ▼
   CursorController  VolumeController  ScrollController  …(9 more)
          │
     PyAutoGUI → OS input events
```

Each module is **independent and stateless-by-design** — the engine calls only the module that matches the current gesture, making the system easy to extend.

---

## 🤚 Gesture Reference

| Gesture | Hand Shape | Notes |
|---------|-----------|-------|
| Move cursor | ☝️ Index only | Maps to full screen |
| Click | Pinch index+thumb | < 4 % distance threshold |
| Double click | Two rapid pinches | < 350 ms apart |
| Right click | Pinch middle+thumb | — |
| Scroll | ✌️ Peace sign | Wrist Y velocity drives direction |
| Volume | 🤙 Hang loose | Thumb–Pinky distance = volume % |
| Draw | ☝️ Index only (draw mode) | Toggle with `d` key |
| Screenshot | 🖐 All 5 fingers | Hold ≥ 1 second |
| Drag window | ✊ Closed fist | Wrist displacement moves window |
| Zoom | 🤏 Pinch spread | Ctrl + Scroll simulation |
| Play/Pause | 🖐 Flat palm | Debounced 1 s |
| Next track | 🤘 Swipe right | Index + Pinky, swipe gesture |
| Prev track | 🤘 Swipe left | Index + Pinky, swipe gesture |
| Brightness | Thumb + Ring | Right-hand bar indicator |

---

## 💻 Installation

### Prerequisites

- Python 3.9+
- Conda (recommended)
- Webcam

### Step 1 – Create the Conda environment

```bash
conda create -n gesture_control python=3.9 -y
conda activate gesture_control
```

### Step 2 – Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 – Platform-specific extras

**Windows (volume + window movement):**
```bash
pip install pycaw pywin32
```

**Windows/Linux (brightness):**
```bash
pip install screen-brightness-control
```

---

## 🚀 Usage

```bash
conda activate gesture_control
python main.py
```

| Key | Action |
|-----|--------|
| `q` | Quit the application |
| `d` | Toggle drawing canvas on/off |
| `r` | Clear the drawing canvas |

The HUD in the top bar shows the current FPS and active gesture mode in real time.

---

## 📁 Project Structure

```
gesture_control/
├── main.py                  # Entry point – camera loop & module orchestration
├── requirements.txt         # Python dependencies
├── screenshots/             # Auto-created; screenshot captures saved here
└── modules/
    ├── __init__.py
    ├── config.py            # All tuneable parameters in one place
    ├── hand_tracker.py      # MediaPipe Hands wrapper
    ├── gesture_engine.py    # Stateful gesture classifier (14 gestures)
    ├── cursor_controller.py # Smooth cursor + click actions
    ├── volume_control.py    # System volume via thumb–pinky distance
    ├── scroll_control.py    # Page scrolling via wrist velocity
    ├── drawing_canvas.py    # Virtual finger-drawing overlay
    ├── screenshot.py        # Full-screen capture with debounce
    ├── window_mover.py      # Active window drag (Windows & macOS)
    ├── zoom_control.py      # Ctrl+Scroll pinch zoom
    ├── media_control.py     # Play/Pause / Next / Prev media keys
    ├── brightness_control.py# Screen brightness (cross-platform)
    └── ui_overlay.py        # HUD, gesture badges, legend
```

---

## ⚙️ Configuration

All parameters are centralised in `modules/config.py`. Key settings:

```python
SMOOTHING_FACTOR       = 0.30    # cursor EMA weight (lower → smoother)
CLICK_THRESHOLD        = 0.04    # normalised pinch distance for click
DOUBLE_CLICK_INTERVAL  = 0.35   # seconds between clicks → double click
SCREENSHOT_HOLD_TIME   = 1.0    # seconds to hold 5-finger gesture
CONTROL_ZONE_MARGIN    = 0.15   # dead-zone fraction at frame edges
```

Adjust these to match your environment (lighting, hand size, camera distance).

---

## 📊 Performance

| Condition | Typical FPS | Accuracy |
|-----------|-------------|----------|
| Good lighting, close hand | 28–32 | > 95 % |
| Low light | 20–28 | ~85 % |
| Fast movement | 25–30 | ~88 % |
| Two-hand tracking | 22–28 | ~90 % |

Tested on: Intel Core i7-11th Gen, 16 GB RAM, integrated camera (720 p).

---

## 🔧 Troubleshooting

**Camera not detected**  
→ Change `CAMERA_INDEX` in `config.py` (try `1`, `2`, etc.)

**Low FPS**  
→ Reduce `FRAME_WIDTH`/`FRAME_HEIGHT` to `640×480` in `config.py`

**Volume not changing (Linux)**  
→ Ensure `pulseaudio` or `pipewire-pulse` is running; amixer uses PULSE

**Window drag not working**  
→ Install `pywin32` (Windows) or ensure Accessibility permissions are granted (macOS)

---

## 🎬 Demo

📹 [Demo Video Link] ← _Add your screen recording link here_

![Gesture Demo Screenshot](assets/demo_screenshot.png)

---

## 🔮 Future Improvements

- **Virtual Keyboard** – Hand-tracking-based on-screen keyboard for full text input
- **Handwriting Recognition** – Convert drawn strokes to text via an OCR model
- **ML-based Classifier** – Replace rule-based engine with a trained CNN/LSTM for higher accuracy in challenging lighting
- **Custom Gesture Profiles** – Per-application gesture mapping (e.g., Zoom mode for browsers, drawing mode for Photoshop)
- **Voice + Gesture Fusion** – Combine speech commands with gestures for richer interactions
- **Gaze Tracking Integration** – Eye + hand combined control for accessibility use cases

---

## 📚 References

1. Google MediaPipe – https://mediapipe.dev  
2. OpenCV Documentation – https://docs.opencv.org  
3. PyAutoGUI Documentation – https://pyautogui.readthedocs.io  
4. Murtaza's Workshop – Hand Tracking tutorial (YouTube)  
5. NumPy Documentation – https://numpy.org/doc  

---

*Course Final Assessment · May 2026*