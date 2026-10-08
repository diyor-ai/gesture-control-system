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
- [Wayland setup](#-wayland-setup-linux)
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

This project delivers a **real-time, gesture-driven computer interaction system** that uses a standard webcam to replace traditional mouse and keyboard input. It tracks hand landmarks in real time (≈ 30 FPS, limited by the webcam – see [Performance](#-performance)) using Google's MediaPipe framework and dispatches recognised gestures to dedicated modules for cursor control, volume, scrolling, drawing, screenshots, window management, zoom, media playback, and screen brightness.

| Metric | Value |
|--------|-------|
| Measured FPS | ≈ 30 (camera-limited), see Performance |
| Detected hands | Up to 2 simultaneous |
| Total gestures | 14 distinct actions |
| Lines of code | ~2 000 (+ ~1 100 lines of tests) |
| Supported OS | Windows · macOS · Linux |

---

## ✅ Feature Matrix

| # | Feature | Gesture | Status |
|---|---------|---------|--------|
| 1 | **Cursor Movement** | Index finger extended | ✅ Core |
| 2 | **Single Click** | Index + Thumb pinch | ✅ Core |
| 3 | **Double Click** | Two separate pinches within 0.40 s | ✅ Core |
| 4 | **Right Click** | Middle + Thumb pinch | ✅ Core |
| 5 | **Volume Control** | Thumb + Pinky spread 🤙 | ✅ Mandatory |
| 6 | **Screen Scrolling** | Peace sign ✌ + wrist movement | ✅ Mandatory |
| 7 | **Finger Drawing** | Index only, canvas mode | ✅ Mandatory |
| 8 | **Screenshot** | All 5 fingers up (hold 1 s) | ✅ Mandatory |
| 9 | **Window Movement** | Closed fist drag | ⚠️ Windows/macOS only – not available on Linux |
| 10 | **Zoom In/Out** | Secondary hand L-shape, thumb–index spread | ✅ Mandatory |
| 11 | **Media Play/Pause** | Index + middle + ring up (hold 0.5 s) | ✅ Mandatory |
| 12 | **Media Next/Prev** | Index + Pinky 🤘, swipe right / left | ✅ Mandatory |
| 13 | **Brightness Control** | Thumb + Ring spread | ✅ Advanced |
| 14 | **Hand-Loss Recovery** | Automatic freeze on hand loss | ✅ Advanced |
| 15 | **Multi-Hand Support** | Up to 2 hands; primary hand = cursor, other = zoom | ✅ Advanced |
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

Every gesture has its own pose. `T I M R P` = thumb, index, middle, ring, pinky; "any" = not checked.
A pose must be seen for 3 consecutive frames (`STABILITY_FRAMES`) before it activates.

**Primary hand** (`PRIMARY_HAND`, default **Right**) – the only hand that drives the cursor

| Gesture | Pose | Behaviour |
|---------|------|-----------|
| Move cursor | ☝️ Index up, M R P down, thumb any (L-shape is fine) | Fingertip → screen, smoothed |
| Click | Same pose, thumb tip pinched onto index tip | **One** click when the pinch starts; release before the next |
| Double click | Two separate pinches within 0.40 s (`DOUBLE_CLICK_INTERVAL`) | Second pinch completes the double click |
| Right click | Only middle up, thumb tip pinched onto middle tip | One click per pinch |
| Draw | ☝️ Index pose while the canvas is on (`d`) | Replaces MOVE_CURSOR while drawing |

**Secondary hand** (the other one)

| Gesture | Pose | Behaviour |
|---------|------|-----------|
| Zoom | 👆 L-shape: thumb + index up, M R P down | Thumb–index spread → Ctrl + scroll |

**Either hand**

| Gesture | Pose | Behaviour |
|---------|------|-----------|
| Scroll | ✌️ Index + middle up, R P down | Wrist Y movement drives direction |
| Volume | 🤙 Thumb + pinky up, I M R down | Thumb–pinky distance = volume % |
| Brightness | Thumb + ring up, I M P down | Thumb–ring distance = brightness % |
| Play/Pause | 🤟 Index + middle + ring up, pinky down | Hold 0.5 s → fires once |
| Next track | 🤘 Index + pinky up, M R down, swipe **right** | One event per swipe (1 s cooldown) |
| Previous track | 🤘 Same pose, swipe **left** | One event per swipe |
| Screenshot | 🖐 All five fingers up | Hold 1 s → fires once, release to re-arm |

> **Drag window (✊ fist) is Windows/macOS only.** It is not implemented on Linux, so there the fist
> does nothing and is not listed above (`Config.WINDOW_DRAG_ENABLED`). Moving foreign windows is not possible
> from a normal Wayland client; it would need a compositor-specific extension.

Pinch, volume, brightness and zoom distances are measured in **palm lengths** (wrist → middle-finger base),
so they work at any distance from the camera. Run with `--debug` to see the live values.

Event gestures (clicks, play/pause, swipes, screenshot) fire once; the rest repeat every frame while held.
If the hand disappears for up to 5 frames (`HAND_LOSS_GRACE_FRAMES`) nothing is reset; longer and all gesture state is cleared.

---

## 💻 Installation

### Prerequisites

- Python 3.9 – 3.12 (MediaPipe 0.10.14 has no wheels for 3.13+); 3.11 recommended
- Conda (recommended)
- Webcam

### Step 1 – Create the Conda environment

```bash
conda create -n gesture311 python=3.11 -y
conda activate gesture311
```

### Step 2 – Install dependencies

```bash
pip install -r requirements.txt
python -c "import mediapipe; print(mediapipe.__version__)"   # expect 0.10.14
```

### Step 3 – Platform-specific extras

**Windows (volume + window movement):**
```bash
pip install pycaw pywin32
```

**Linux (Fedora):**
```bash
sudo dnf install wireplumber brightnessctl     # wpctl (volume) and brightness
```
Volume: `wpctl` → `pactl` → `amixer`. Brightness: `brightnessctl` → `xrandr` (software gamma, X11 only).
Screen size is auto-detected; override with `GESTURE_SCREEN=2560x1440 python main.py`.

> **Wayland (GNOME on Fedora 44 has no Xorg session):** PyAutoGUI cannot move the pointer there, so the app
> injects input through the kernel's uinput instead – see [Wayland setup](#-wayland-setup-linux) below.

**Windows (brightness):**
```bash
pip install screen-brightness-control
```

---

## 🐧 Wayland setup (Linux)

On Wayland the app creates a virtual *absolute* pointing device through `/dev/uinput` (python-evdev) and maps
the hand position to the detected screen size. That needs read/write access to `/dev/uinput`.
**Do not add yourself to the `input` group** – that would let every program you run read your keyboard.
Use a dedicated `uinput` group that only owns `/dev/uinput`. Run these once yourself:

```bash
sudo groupadd --system uinput
sudo usermod -aG uinput "$USER"
sudo cp linux/99-gesture-uinput.rules /etc/udev/rules.d/
sudo cp linux/uinput.conf /etc/modules-load.d/gesture-uinput.conf
sudo udevadm control --reload-rules
sudo udevadm trigger --name-match=uinput
sudo modprobe uinput
sudo dnf install gnome-screenshot brightnessctl     # screenshots + brightness
```

Then **log out and back in** (group membership is read at login) and check:

```bash
id -nG | tr ' ' '\n' | grep -x uinput      # prints "uinput"
ls -l /dev/uinput                            # crw-rw---- root uinput
python tools/uinput_selftest.py              # asks first, then moves the pointer in a square (no clicks)
```

Trade-off: any process running as a member of `uinput` can inject mouse/keyboard events (it can *not* read
them). Remove the setup with `sudo gpasswd -d "$USER" uinput` and `sudo rm /etc/udev/rules.d/99-gesture-uinput.rules`.

Backend choice: `INPUT_BACKEND` in `config.py` or `GESTURE_INPUT=uinput|pyautogui|auto`. `auto` uses uinput on
Wayland and falls back to PyAutoGUI (with a warning) if `/dev/uinput` is not accessible.

---

## 🚀 Usage

```bash
conda activate gesture311
python main.py
```

| Key | Action |
|-----|--------|
| `q` | Quit the application |
| `d` | Toggle drawing canvas on/off |
| `r` | Clear the drawing canvas |

```bash
python main.py --debug     # overlay: finger states, raw/stable pose, gesture, FPS
```

### Tests

```bash
pip install -r requirements-dev.txt
pytest                     # no camera needed – uses synthetic landmarks
```

The HUD in the top bar shows the current FPS and active gesture mode in real time.

---

## 📁 Project Structure

```
gesture_control/
├── main.py                  # Entry point – camera loop & module orchestration
├── requirements.txt         # Python dependencies
├── requirements-dev.txt     # + pytest
├── tests/                   # Unit tests (synthetic landmarks, fake input device)
├── tools/                   # benchmark_fps.py, uinput_selftest.py (manual)
├── linux/                   # udev rule + modules-load file for the uinput group
├── screenshots/             # Auto-created; screenshot captures saved here
└── modules/
    ├── __init__.py
    ├── config.py            # All tuneable parameters in one place
    ├── hand_tracker.py      # MediaPipe Hands wrapper
    ├── gesture_engine.py    # Per-hand, debounced gesture classifier
    ├── camera.py            # Frame reading with a bounded retry budget
    ├── system_worker.py     # Step filter + background worker for volume/brightness
    ├── cursor_controller.py # Smooth cursor + click actions
    ├── volume_control.py    # System volume via thumb–pinky distance
    ├── scroll_control.py    # Page scrolling via wrist velocity
    ├── drawing_canvas.py    # Virtual finger-drawing overlay
    ├── screenshot.py        # Full-screen capture with debounce
    ├── window_mover.py      # Active window drag (Windows & macOS only)
    ├── input_backend.py     # uinput (Wayland) / PyAutoGUI input injection
    ├── linux_backends.py    # wpctl/pactl volume, brightnessctl/xrandr brightness, screen size
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
DOUBLE_CLICK_INTERVAL  = 0.40   # max seconds between two pinch starts → double click
PRIMARY_HAND           = "Right" # hand that moves the cursor / clicks / draws
STABILITY_FRAMES       = 3      # frames a pose must persist before it activates
HAND_LOSS_GRACE_FRAMES = 5      # dropout frames tolerated before state is reset
SCREENSHOT_HOLD_TIME   = 1.0    # seconds to hold 5-finger gesture
CONTROL_ZONE_MARGIN    = 0.15   # dead-zone fraction at frame edges
```

Adjust these to match your environment (lighting, hand size, camera distance).

---

## 📊 Performance

Measured with `tools/benchmark_fps.py` (real webcam + MediaPipe, no window, no input injection),
Fedora 44, CPU only, a hand in view. The webcam delivers 640×480 at 30 FPS and ignores a 1280×720 request,
so 30 FPS is the ceiling.

| Setting | Camera → tracking FPS (hand in view) |
|---------|--------------------------------------|
| Before: 1280×720 requested, `model_complexity=1` | 16.5 – 21.6 |
| Now: 640×480, `model_complexity=0` (`MODEL_COMPLEXITY`) | 29.9 (camera-limited) |
| Camera alone | 30.1 |

Numbers vary by about ±3 FPS between runs. The full application (window, HUD, input injection) has not been
benchmarked yet. Gesture accuracy has not been measured, so no accuracy figures are claimed.

---

## 🔧 Troubleshooting

**Camera not detected**  
→ Change `CAMERA_INDEX` in `config.py` (try `1`, `2`, etc.)

**Low FPS**  
→ Already 640×480 / `MODEL_COMPLEXITY = 0` by default; run `python tools/benchmark_fps.py` to see where time goes

**Volume not changing (Linux)**  
→ Ensure `pulseaudio` or `pipewire-pulse` is running; amixer uses PULSE

**Cursor / screenshot do nothing on Fedora (Wayland)**  
→ PyAutoGUI cannot drive native Wayland (measured on Fedora 44 / GNOME 50: `moveTo()` does nothing, `screenshot()` raises). Do the [Wayland setup](#-wayland-setup-linux); the app prints `Input backend: uinput` at start-up when it works.

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