"""Backend selection / fallback for volume, brightness and screen size."""

import subprocess
from types import SimpleNamespace

import pytest

from modules import linux_backends as lb

XRANDR = (
    "Screen 0: minimum 16 x 16, current 2560 x 1440, maximum 32767 x 32767\n"
    "HDMI-1 connected 1920x1080+2560+0\n"
    "DP-3 connected primary 2560x1440+0+0\n"
)


class FakeSystem:
    """Pretend that only `tools` are installed; record every command run."""

    def __init__(self, monkeypatch, tools, failing=(), xrandr=XRANDR):
        self.calls = []
        self.failing = set(failing)
        self.xrandr = xrandr
        monkeypatch.setattr(lb.shutil, "which", lambda name: f"/usr/bin/{name}" if name in tools else None)
        monkeypatch.setattr(lb.subprocess, "run", self._run)

    def _run(self, cmd, **kwargs):
        self.calls.append(cmd)
        code = 1 if cmd[0] in self.failing else 0
        out = self.xrandr if cmd[:2] == ["xrandr", "--current"] else ""
        return SimpleNamespace(returncode=code, stdout=out, stderr="")


def test_volume_prefers_wpctl(monkeypatch):
    sys = FakeSystem(monkeypatch, {"wpctl", "pactl", "amixer"})
    assert lb.set_volume(0.5) is True
    assert sys.calls == [["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "0.50"]]


def test_volume_falls_back_to_pactl_when_wpctl_is_missing(monkeypatch):
    sys = FakeSystem(monkeypatch, {"pactl"})
    assert lb.set_volume(0.5) is True
    assert sys.calls == [["pactl", "set-sink-volume", "@DEFAULT_SINK@", "50%"]]


def test_volume_falls_back_when_wpctl_fails(monkeypatch):
    sys = FakeSystem(monkeypatch, {"wpctl", "pactl"}, failing={"wpctl"})
    assert lb.set_volume(0.25) is True
    assert [c[0] for c in sys.calls] == ["wpctl", "pactl"]


def test_volume_reports_failure_when_no_tool_exists(monkeypatch):
    FakeSystem(monkeypatch, set())
    assert lb.set_volume(0.5) is False


def test_volume_is_clamped(monkeypatch):
    sys = FakeSystem(monkeypatch, {"wpctl"})
    lb.set_volume(7.0)
    assert sys.calls[0][-1] == "1.00"


def test_brightness_prefers_brightnessctl(monkeypatch):
    sys = FakeSystem(monkeypatch, {"brightnessctl", "xrandr"})
    assert lb.set_brightness(0.6) is True
    assert sys.calls == [["brightnessctl", "--quiet", "set", "60%"]]


def test_brightness_falls_back_to_xrandr_on_the_detected_output(monkeypatch):
    sys = FakeSystem(monkeypatch, {"xrandr"})
    assert lb.set_brightness(0.6) is True
    assert sys.calls[-1] == ["xrandr", "--output", "DP-3", "--brightness", "0.60"]   # primary, not eDP-1


def test_brightness_never_goes_fully_dark(monkeypatch):
    sys = FakeSystem(monkeypatch, {"brightnessctl"})
    lb.set_brightness(0.0)
    assert sys.calls[0][-1] == "5%"


def test_brightness_fails_cleanly_without_tools(monkeypatch):
    FakeSystem(monkeypatch, set())
    assert lb.set_brightness(0.5) is False


def test_timeout_counts_as_failure(monkeypatch):
    monkeypatch.setattr(lb.shutil, "which", lambda name: "/usr/bin/x")

    def hang(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 2)

    monkeypatch.setattr(lb.subprocess, "run", hang)
    assert lb.set_volume(0.5) is False


@pytest.mark.parametrize("text,expected", [("1920x1080", (1920, 1080)), (" 2560 X 1440 ", (2560, 1440)),
                                           ("abc", None), ("", None)])
def test_parse_size(text, expected):
    assert lb.parse_size(text) == expected


def test_screen_size_env_override(monkeypatch):
    monkeypatch.setenv("GESTURE_SCREEN", "3840x2160")
    assert lb.screen_size() == (3840, 2160)


def test_screen_size_uses_the_primary_monitor(monkeypatch):
    import sys
    monkeypatch.delenv("GESTURE_SCREEN", raising=False)
    mons = [SimpleNamespace(width=1920, height=1080, is_primary=False),
            SimpleNamespace(width=2560, height=1440, is_primary=True)]
    monkeypatch.setitem(sys.modules, "screeninfo", SimpleNamespace(get_monitors=lambda: mons))
    assert lb.screen_size() == (2560, 1440)


def test_screen_size_falls_back_to_xrandr_then_default(monkeypatch):
    import sys
    monkeypatch.delenv("GESTURE_SCREEN", raising=False)
    monkeypatch.setitem(sys.modules, "screeninfo", None)          # import fails
    FakeSystem(monkeypatch, {"xrandr"})
    assert lb.screen_size() == (2560, 1440)
    FakeSystem(monkeypatch, set())
    assert lb.screen_size() == (1920, 1080)
