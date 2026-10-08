"""
input_backend.py – Where synthetic mouse / keyboard events go.

PyAutoGUIBackend : X11, Windows, macOS (and XWayland-only, unreliable on Wayland).
UInputBackend    : Linux kernel uinput through python-evdev.  Works on Wayland
                   and X11 alike because the compositor sees a real (virtual)
                   absolute pointing device.  Needs access to /dev/uinput –
                   see README "Wayland setup" (dedicated `uinput` group).

Every controller talks to the small interface below, so the rest of the
project does not care which backend is active:

    move_to(x, y)       absolute pointer position in screen pixels
    click() / right_click()
    scroll(clicks)      positive = up
    ctrl_scroll(clicks) scroll with Ctrl held (browser / editor zoom)
    press_media(name)   "playpause" | "nexttrack" | "prevtrack"
    screenshot(path)    save the whole screen, return True on success
    close()
"""

import os
import platform
from typing import Optional

# Linux input event codes (linux/input-event-codes.h).  Kept as plain numbers
# so this module imports without python-evdev; tests cross-check them.
EV_SYN, EV_KEY, EV_REL, EV_ABS = 0x00, 0x01, 0x02, 0x03
SYN_REPORT = 0
ABS_X, ABS_Y = 0x00, 0x01
REL_WHEEL, REL_WHEEL_HI_RES = 0x08, 0x0B
BTN_LEFT, BTN_RIGHT = 0x110, 0x111
KEY_LEFTCTRL = 29
KEY_NEXTSONG, KEY_PLAYPAUSE, KEY_PREVIOUSSONG = 163, 164, 165

_MEDIA_KEYS = {
    "playpause": KEY_PLAYPAUSE,
    "nexttrack": KEY_NEXTSONG,
    "prevtrack": KEY_PREVIOUSSONG,
}
_HI_RES_PER_NOTCH = 120


class InputBackendError(RuntimeError):
    """The requested input backend cannot be used (message says how to fix it)."""


# ── PyAutoGUI ─────────────────────────────────────────────────────────────────

class PyAutoGUIBackend:
    name = "pyautogui"

    def __init__(self) -> None:
        import pyautogui
        pyautogui.PAUSE    = 0
        pyautogui.FAILSAFE = False
        self._pag = pyautogui

    def move_to(self, x: int, y: int) -> None:
        self._pag.moveTo(int(x), int(y))

    def click(self) -> None:
        self._pag.click()

    def right_click(self) -> None:
        self._pag.rightClick()

    def scroll(self, clicks: int) -> None:
        self._pag.scroll(clicks)

    def ctrl_scroll(self, clicks: int) -> None:
        self._pag.keyDown("ctrl")
        try:
            self._pag.scroll(clicks)
        finally:
            self._pag.keyUp("ctrl")

    def press_media(self, name: str) -> None:
        self._pag.press(name)

    def screenshot(self, path: str) -> bool:
        try:
            self._pag.screenshot().save(path)
            return True
        except Exception as exc:
            print(f"[Screenshot] pyautogui failed: {exc}")
            return False

    def close(self) -> None:
        pass


# ── uinput ────────────────────────────────────────────────────────────────────

class UInputBackend:
    """Virtual absolute pointer + wheel + a few keys, created through uinput."""

    name = "uinput"

    def __init__(self, screen_w: int, screen_h: int, device=None) -> None:
        """`device` (anything with write(type, code, value) and syn()) is for tests."""
        self._w = max(int(screen_w), 2)
        self._h = max(int(screen_h), 2)
        self._dev = device if device is not None else _open_uinput_device(self._w, self._h)

    def move_to(self, x: int, y: int) -> None:
        x = min(max(int(x), 0), self._w - 1)
        y = min(max(int(y), 0), self._h - 1)
        self._dev.write(EV_ABS, ABS_X, x)
        self._dev.write(EV_ABS, ABS_Y, y)
        self._dev.syn()

    def _button(self, code: int) -> None:
        self._dev.write(EV_KEY, code, 1)
        self._dev.syn()
        self._dev.write(EV_KEY, code, 0)
        self._dev.syn()

    def click(self) -> None:
        self._button(BTN_LEFT)

    def right_click(self) -> None:
        self._button(BTN_RIGHT)

    def scroll(self, clicks: int) -> None:
        if clicks == 0:
            return
        self._dev.write(EV_REL, REL_WHEEL_HI_RES, int(clicks) * _HI_RES_PER_NOTCH)
        self._dev.write(EV_REL, REL_WHEEL, int(clicks))
        self._dev.syn()

    def ctrl_scroll(self, clicks: int) -> None:
        self._dev.write(EV_KEY, KEY_LEFTCTRL, 1)
        self._dev.syn()
        try:
            self.scroll(clicks)
        finally:
            self._dev.write(EV_KEY, KEY_LEFTCTRL, 0)
            self._dev.syn()

    def press_media(self, name: str) -> None:
        code = _MEDIA_KEYS[name]
        self._button(code)

    def screenshot(self, path: str) -> bool:
        from modules import linux_backends
        return linux_backends.take_screenshot(path)

    def close(self) -> None:
        close = getattr(self._dev, "close", None)
        if close:
            close()


def _open_uinput_device(width: int, height: int):
    """Create the virtual device; raise InputBackendError with a fix on failure."""
    try:
        from evdev import AbsInfo, UInput
    except ImportError as exc:
        raise InputBackendError(
            "python-evdev is not installed. Run: pip install evdev"
        ) from exc

    capabilities = {
        EV_KEY: [BTN_LEFT, BTN_RIGHT, KEY_LEFTCTRL, *_MEDIA_KEYS.values()],
        EV_REL: [REL_WHEEL, REL_WHEEL_HI_RES],
        EV_ABS: [
            (ABS_X, AbsInfo(value=0, min=0, max=width - 1, fuzz=0, flat=0, resolution=0)),
            (ABS_Y, AbsInfo(value=0, min=0, max=height - 1, fuzz=0, flat=0, resolution=0)),
        ],
    }
    try:
        return UInput(capabilities, name="gesture-control virtual pointer")
    except PermissionError as exc:
        raise InputBackendError(
            "No permission to open /dev/uinput. Do the one-time 'Wayland setup' "
            "from the README (dedicated 'uinput' group + udev rule), then log out and in."
        ) from exc
    except FileNotFoundError as exc:
        raise InputBackendError(
            "/dev/uinput does not exist. Load the kernel module: sudo modprobe uinput"
        ) from exc


# ── Selection ─────────────────────────────────────────────────────────────────

def is_wayland() -> bool:
    return platform.system() == "Linux" and os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


def create_backend(cfg, choice: Optional[str] = None):
    """
    Pick the input backend.  `choice` / $GESTURE_INPUT / cfg.INPUT_BACKEND is
    "auto" (uinput on Wayland, otherwise PyAutoGUI), "uinput" or "pyautogui".
    "uinput" fails loudly; "auto" falls back to PyAutoGUI with a warning.
    """
    choice = (choice or os.environ.get("GESTURE_INPUT") or cfg.INPUT_BACKEND).lower()
    if choice not in ("auto", "uinput", "pyautogui"):
        raise InputBackendError(f"Unknown input backend {choice!r} (use auto, uinput or pyautogui)")

    if choice == "pyautogui" or (choice == "auto" and not is_wayland()):
        return PyAutoGUIBackend()

    try:
        return UInputBackend(cfg.SCREEN_W, cfg.SCREEN_H)
    except InputBackendError as exc:
        if choice == "uinput":
            raise
        print(f"[WARN] uinput unavailable: {exc}")
        print("[WARN] Falling back to PyAutoGUI – on Wayland the pointer will NOT move.")
        return PyAutoGUIBackend()
