"""uinput backend: events, absolute mapping and backend selection (no real device)."""

import pytest

from modules import input_backend as ib
from modules.config import Config


class FakeDevice:
    def __init__(self):
        self.events = []        # (type, code, value) in write order, "SYN" markers for syn()
        self.closed = False

    def write(self, etype, code, value):
        self.events.append((etype, code, value))

    def syn(self):
        self.events.append("SYN")

    def close(self):
        self.closed = True


@pytest.fixture
def dev():
    return FakeDevice()


@pytest.fixture
def backend(dev):
    return ib.UInputBackend(1920, 1080, device=dev)


def test_constants_match_the_kernel_headers():
    ecodes = pytest.importorskip("evdev.ecodes")
    assert (ib.EV_KEY, ib.EV_REL, ib.EV_ABS) == (ecodes.EV_KEY, ecodes.EV_REL, ecodes.EV_ABS)
    assert (ib.ABS_X, ib.ABS_Y) == (ecodes.ABS_X, ecodes.ABS_Y)
    assert (ib.REL_WHEEL, ib.REL_WHEEL_HI_RES) == (ecodes.REL_WHEEL, ecodes.REL_WHEEL_HI_RES)
    assert (ib.BTN_LEFT, ib.BTN_RIGHT) == (ecodes.BTN_LEFT, ecodes.BTN_RIGHT)
    assert ib.KEY_LEFTCTRL == ecodes.KEY_LEFTCTRL
    assert (ib.KEY_PLAYPAUSE, ib.KEY_NEXTSONG, ib.KEY_PREVIOUSSONG) == (
        ecodes.KEY_PLAYPAUSE, ecodes.KEY_NEXTSONG, ecodes.KEY_PREVIOUSSONG)


def test_move_is_absolute_and_in_screen_pixels(backend, dev):
    backend.move_to(960, 540)
    assert dev.events == [(ib.EV_ABS, ib.ABS_X, 960), (ib.EV_ABS, ib.ABS_Y, 540), "SYN"]


def test_move_is_clamped_to_the_detected_screen(backend, dev):
    backend.move_to(-50, 99999)
    assert dev.events[:2] == [(ib.EV_ABS, ib.ABS_X, 0), (ib.EV_ABS, ib.ABS_Y, 1079)]


def test_click_presses_and_releases_the_left_button(backend, dev):
    backend.click()
    assert dev.events == [(ib.EV_KEY, ib.BTN_LEFT, 1), "SYN", (ib.EV_KEY, ib.BTN_LEFT, 0), "SYN"]


def test_right_click_uses_the_right_button(backend, dev):
    backend.right_click()
    assert (ib.EV_KEY, ib.BTN_RIGHT, 1) in dev.events and (ib.EV_KEY, ib.BTN_RIGHT, 0) in dev.events


def test_scroll_sends_hi_res_and_legacy_wheel_events(backend, dev):
    backend.scroll(-3)
    assert (ib.EV_REL, ib.REL_WHEEL_HI_RES, -360) in dev.events
    assert (ib.EV_REL, ib.REL_WHEEL, -3) in dev.events


def test_zero_scroll_sends_nothing(backend, dev):
    backend.scroll(0)
    assert dev.events == []


def test_ctrl_scroll_holds_ctrl_around_the_wheel_and_always_releases_it(backend, dev):
    backend.ctrl_scroll(2)
    kinds = [e for e in dev.events if e != "SYN"]
    assert kinds[0] == (ib.EV_KEY, ib.KEY_LEFTCTRL, 1)
    assert kinds[-1] == (ib.EV_KEY, ib.KEY_LEFTCTRL, 0)
    assert (ib.EV_REL, ib.REL_WHEEL, 2) in kinds


@pytest.mark.parametrize("name,code", [("playpause", 164), ("nexttrack", 163), ("prevtrack", 165)])
def test_media_keys(backend, dev, name, code):
    backend.press_media(name)
    assert dev.events[0] == (ib.EV_KEY, code, 1)


def test_close_closes_the_device(backend, dev):
    backend.close()
    assert dev.closed


# ── backend selection ─────────────────────────────────────────────────────────

def test_auto_uses_pyautogui_outside_wayland(monkeypatch, gui_stubs):
    monkeypatch.delenv("GESTURE_INPUT", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    assert ib.create_backend(Config()).name == "pyautogui"


def test_auto_uses_uinput_on_wayland(monkeypatch):
    monkeypatch.delenv("GESTURE_INPUT", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setattr(ib, "platform", type("P", (), {"system": staticmethod(lambda: "Linux")}))
    monkeypatch.setattr(ib, "_open_uinput_device", lambda w, h: FakeDevice())
    assert ib.create_backend(Config()).name == "uinput"


def test_auto_falls_back_with_a_warning_when_uinput_is_not_permitted(monkeypatch, gui_stubs, capsys):
    monkeypatch.delenv("GESTURE_INPUT", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setattr(ib, "platform", type("P", (), {"system": staticmethod(lambda: "Linux")}))

    def denied(w, h):
        raise ib.InputBackendError("No permission to open /dev/uinput")

    monkeypatch.setattr(ib, "_open_uinput_device", denied)
    assert ib.create_backend(Config()).name == "pyautogui"
    assert "NOT move" in capsys.readouterr().out


def test_explicit_uinput_fails_loudly(monkeypatch):
    def denied(w, h):
        raise ib.InputBackendError("No permission to open /dev/uinput")

    monkeypatch.setattr(ib, "_open_uinput_device", denied)
    with pytest.raises(ib.InputBackendError, match="permission"):
        ib.create_backend(Config(), choice="uinput")


def test_unknown_backend_is_rejected():
    with pytest.raises(ib.InputBackendError):
        ib.create_backend(Config(), choice="xdotool")


def test_missing_uinput_device_gives_an_actionable_message(monkeypatch):
    evdev = pytest.importorskip("evdev")

    def no_device(*a, **k):
        raise FileNotFoundError()

    monkeypatch.setattr(evdev, "UInput", no_device)
    with pytest.raises(ib.InputBackendError, match="modprobe uinput"):
        ib._open_uinput_device(1920, 1080)


def test_permission_error_points_to_the_setup(monkeypatch):
    evdev = pytest.importorskip("evdev")

    def denied(*a, **k):
        raise PermissionError()

    monkeypatch.setattr(evdev, "UInput", denied)
    with pytest.raises(ib.InputBackendError, match="uinput. group"):
        ib._open_uinput_device(1920, 1080)


def test_press_keys_holds_the_combo_and_releases_in_reverse(backend, dev):
    backend.press_keys(("shift", "print"))
    keys = [e for e in dev.events if e != "SYN"]
    assert keys == [(ib.EV_KEY, ib.KEY_LEFTSHIFT, 1), (ib.EV_KEY, ib.KEY_SYSRQ, 1),
                    (ib.EV_KEY, ib.KEY_SYSRQ, 0), (ib.EV_KEY, ib.KEY_LEFTSHIFT, 0)]


def test_unknown_screenshot_key_is_rejected_up_front(dev):
    with pytest.raises(ib.InputBackendError):
        ib.UInputBackend(1920, 1080, device=dev, screenshot_keys=("shift", "prtsc"))


def test_gnome_wayland_screenshot_types_the_shortcut_instead_of_a_tool(monkeypatch, dev, tmp_path):
    monkeypatch.setattr(ib, "is_gnome_wayland", lambda: True)
    called = []
    monkeypatch.setattr("modules.linux_backends.take_screenshot", lambda p: called.append(p) or True)
    b = ib.UInputBackend(1920, 1080, device=dev, screenshot_keys=("shift", "print"))
    assert b.screenshot(str(tmp_path / "x.png")) is True
    assert (ib.EV_KEY, ib.KEY_SYSRQ, 1) in dev.events
    assert called == [] and b.screenshot_location.endswith("Pictures/Screenshots")


def test_other_desktops_fall_back_to_the_screenshot_tools(monkeypatch, dev, tmp_path):
    monkeypatch.setattr(ib, "is_gnome_wayland", lambda: False)
    monkeypatch.setattr("modules.linux_backends.take_screenshot", lambda p: True)
    b = ib.UInputBackend(1920, 1080, device=dev, screenshot_keys=("shift", "print"))
    assert b.screenshot(str(tmp_path / "x.png")) is True
    assert dev.events == [] and b.screenshot_location is None


def test_empty_screenshot_keys_disable_the_shortcut(monkeypatch, dev, tmp_path):
    monkeypatch.setattr(ib, "is_gnome_wayland", lambda: True)
    monkeypatch.setattr("modules.linux_backends.take_screenshot", lambda p: False)
    b = ib.UInputBackend(1920, 1080, device=dev)
    assert b.screenshot(str(tmp_path / "x.png")) is False and dev.events == []
