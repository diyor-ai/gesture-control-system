"""
linux_backends.py – Wayland-friendly Linux helpers for volume, brightness
and screen size.  Every helper tries tools in order of preference and falls
through to the next one when a tool is missing or fails.

Volume      : wpctl (PipeWire)  →  pactl (PulseAudio / pipewire-pulse)  →  amixer
Brightness  : brightnessctl     →  xrandr (software gamma on the detected output)
Screen size : screeninfo (primary monitor)  →  xrandr  →  1920x1080
              (override with the GESTURE_SCREEN=WIDTHxHEIGHT environment variable)
"""

import os
import re
import shutil
import subprocess
from typing import List, Optional, Tuple

_TIMEOUT = 2  # seconds; a hung tool must never wedge the worker thread

# Below this the display would go black and the user could not see the HUD.
MIN_BRIGHTNESS = 0.05


def _run(cmd: List[str]) -> Optional[subprocess.CompletedProcess]:
    """Run `cmd`; return the result, or None if the tool is missing / timed out."""
    if shutil.which(cmd[0]) is None:
        return None
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _ok(cmd: List[str]) -> bool:
    result = _run(cmd)
    return result is not None and result.returncode == 0


# ── Volume ────────────────────────────────────────────────────────────────────

def set_volume(level: float) -> bool:
    """Set the default output volume to `level` (0.0–1.0). Returns True on success."""
    level = min(max(level, 0.0), 1.0)
    pct = int(round(level * 100))
    return (
        _ok(["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", f"{level:.2f}"])
        or _ok(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{pct}%"])
        or _ok(["amixer", "-D", "pulse", "sset", "Master", f"{pct}%"])
    )


# ── Brightness ────────────────────────────────────────────────────────────────

def _xrandr_output() -> Optional[str]:
    """Name of the primary (else first connected) output, e.g. 'eDP-1'."""
    result = _run(["xrandr", "--current"])
    if result is None or result.returncode != 0:
        return None
    connected = re.findall(r"^(\S+) connected( primary)?", result.stdout, re.MULTILINE)
    for name, primary in connected:
        if primary:
            return name
    return connected[0][0] if connected else None


def set_brightness(level: float) -> bool:
    """Set screen brightness to `level` (0.0–1.0, clamped to MIN_BRIGHTNESS)."""
    level = min(max(level, MIN_BRIGHTNESS), 1.0)
    if _ok(["brightnessctl", "--quiet", "set", f"{int(round(level * 100))}%"]):
        return True
    output = _xrandr_output()
    return output is not None and _ok(["xrandr", "--output", output, "--brightness", f"{level:.2f}"])


# ── Screen size ───────────────────────────────────────────────────────────────

def parse_size(text: str) -> Optional[Tuple[int, int]]:
    match = re.fullmatch(r"\s*(\d{3,5})\s*[xX]\s*(\d{3,5})\s*", text or "")
    return (int(match.group(1)), int(match.group(2))) if match else None


def screen_size() -> Tuple[int, int]:
    """
    Size of the primary monitor in pixels.  Works on X11 and, through
    XWayland, on Wayland sessions; GESTURE_SCREEN overrides detection (useful
    with fractional scaling, where XWayland may report a different size).
    """
    override = parse_size(os.environ.get("GESTURE_SCREEN", ""))
    if override:
        return override

    try:
        import screeninfo
        monitors = screeninfo.get_monitors()
        primary = next((m for m in monitors if getattr(m, "is_primary", False)), monitors[0])
        return primary.width, primary.height
    except Exception:
        pass

    result = _run(["xrandr", "--current"])
    if result is not None:
        match = re.search(r"current (\d+) x (\d+)", result.stdout)
        if match:
            return int(match.group(1)), int(match.group(2))

    return 1920, 1080
