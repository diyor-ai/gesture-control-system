"""Joystick-style scrolling: anchor + dead zone + speed by offset, in real time."""

import numpy as np
import pytest

from modules.config import Config
from tests.conftest import FakeClock, make_hand

PALM = 0.25                       # wrist -> middle MCP in make_hand, unscaled


class WheelBackend:
    """Records hi-res units; `total` is the net wheel travel in notches (+ = up)."""

    name = "wheel"

    def __init__(self):
        self.units = []

    def scroll_hi_res(self, units):
        self.units.append(units)

    @property
    def total(self):
        return sum(self.units) / 120


def _shift(landmarks, dy):
    return [(x, y + dy, z) for x, y, z in landmarks]


@pytest.fixture
def rig(gui_stubs):
    from modules.scroll_control import ScrollController

    clock, backend = FakeClock(), WheelBackend()
    cfg = Config()
    ctrl = ScrollController(cfg, backend, clock=clock)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    hand = make_hand("IM")

    def run(offset_palms, seconds, fps=30, h=hand):
        """Hold the hand `offset_palms` below the anchor for `seconds`."""
        moved = _shift(h, offset_palms * PALM)
        for _ in range(int(round(seconds * fps))):
            clock.advance(1 / fps)
            ctrl.scroll(moved, frame)

    ctrl.scroll(hand, frame)               # gesture starts: anchor stored
    return ctrl, backend, clock, run, cfg, frame, hand


def test_nothing_happens_inside_the_dead_zone(rig):
    ctrl, backend, clock, run, cfg, *_ = rig
    run(cfg.SCROLL_DEADZONE * 0.9, 2.0)
    run(-cfg.SCROLL_DEADZONE * 0.9, 2.0)
    assert backend.units == []


def test_hand_below_the_anchor_scrolls_down_and_above_scrolls_up(rig):
    ctrl, backend, clock, run, *_ = rig
    run(0.6, 1.0)
    assert backend.total < 0                         # wheel negative = down
    ctrl.reset(); backend.units.clear()
    ctrl.scroll(make_hand("IM"), np.zeros((480, 640, 3), dtype=np.uint8))
    run(-0.6, 1.0)
    assert backend.total > 0


def test_natural_flag_inverts_the_direction(rig):
    ctrl, backend, clock, run, cfg, *_ = rig
    cfg.SCROLL_NATURAL = True
    run(0.6, 1.0)
    assert backend.total > 0


@pytest.mark.parametrize("fps", [15, 30, 60])
def test_constant_offset_gives_the_same_speed_at_any_fps(rig, fps):
    ctrl, backend, clock, run, cfg, *_ = rig
    run(0.6, 2.0, fps=fps)
    expected = ctrl.speed(0.6) * 2.0                 # notches in 2 s
    assert -backend.total == pytest.approx(expected, rel=0.05)


def test_speed_grows_with_offset_and_is_capped(gui_stubs):
    from modules.scroll_control import ScrollController

    cfg = Config()
    ctrl = ScrollController(cfg, WheelBackend(), clock=FakeClock())
    s = [ctrl.speed(o) for o in (0.1, 0.3, 0.5, 0.8)]
    assert s[0] == 0 and s[1] < s[2] < s[3]
    assert ctrl.speed(10.0) == cfg.SCROLL_MAX_SPEED
    assert ctrl.speed(-0.5) == ctrl.speed(0.5)


def test_slow_movement_accumulates_instead_of_being_lost(rig):
    ctrl, backend, clock, run, cfg, *_ = rig
    # Just beyond the dead zone: well under one unit per frame, but never zero over time.
    run(cfg.SCROLL_DEADZONE + 0.02, 3.0, fps=60)
    assert backend.units, "slow scrolling must still produce wheel units"
    assert -backend.total == pytest.approx(ctrl.speed(cfg.SCROLL_DEADZONE + 0.02) * 3.0, rel=0.05)
    assert all(isinstance(u, int) and u != 0 for u in backend.units)


def test_returning_toward_the_anchor_does_not_scroll_the_other_way(rig):
    ctrl, backend, clock, run, cfg, *_ = rig
    run(0.8, 1.0)
    run(0.5, 0.5)
    run(0.2, 0.5)
    run(0.0, 1.0)
    assert backend.units and all(u < 0 for u in backend.units)      # never positive


def test_reset_clears_the_anchor(rig):
    ctrl, backend, clock, run, cfg, frame, hand = rig
    ctrl.reset()
    backend.units.clear()
    far = _shift(hand, 0.5)                          # new gesture starts here: this is the anchor
    clock.advance(0.1)
    ctrl.scroll(far, frame)
    run(0.0, 1.0, h=far)                             # holding still at the new anchor
    assert backend.units == []


def test_a_stalled_frame_does_not_cause_a_jump(rig):
    ctrl, backend, clock, run, cfg, frame, hand = rig
    moved = _shift(hand, 0.6 * PALM)
    clock.advance(5.0)                               # camera stalled for 5 s
    ctrl.scroll(moved, frame)
    assert -backend.total <= cfg.SCROLL_MAX_SPEED * cfg.SCROLL_MAX_DT + 0.01


def test_debug_log_is_throttled_and_off_by_default(gui_stubs, capsys):
    from modules.scroll_control import ScrollController

    def drive(debug):
        clock = FakeClock()
        ctrl = ScrollController(Config(), WheelBackend(), clock=clock, debug=debug)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        hand = make_hand("IM")
        ctrl.scroll(hand, frame)
        moved = _shift(hand, 0.5 * PALM)
        for _ in range(60):                          # 2 s at 30 FPS
            clock.advance(1 / 30)
            ctrl.scroll(moved, frame)
        return capsys.readouterr().out.strip().splitlines()

    assert drive(False) == []
    lines = drive(True)
    lines = [l for l in lines if "offset=" in l]
    assert 8 <= len(lines) <= 11                     # ~5 per second
    assert all(l.startswith("[scroll]") and "offset=" in l and "speed=" in l and "units_since_last_line=" in l and "anchor_resets=" in l for l in lines)


def _absent(ctrl, clock, seconds, fps=30):
    for _ in range(int(round(seconds * fps))):
        clock.advance(1 / fps)
        ctrl.pose_absent()


def test_short_pose_dropout_keeps_the_anchor_so_coming_back_does_not_reverse(rig):
    ctrl, backend, clock, run, cfg, frame, hand = rig
    run(1.0, 1.0)                                    # far below the anchor, scrolling down
    backend.units.clear()
    _absent(ctrl, clock, cfg.SCROLL_ANCHOR_GRACE * 0.5)      # pose lost for a few frames
    assert backend.units == []                       # nothing is sent while absent
    run(0.0, 1.0)                                    # hand returns to the neutral position
    assert all(u < 0 for u in backend.units)         # never scrolls up on the way back
    assert not any(u > 0 for u in backend.units)


def test_resuming_after_a_dropout_has_no_catch_up_burst(rig):
    ctrl, backend, clock, run, cfg, frame, hand = rig
    _absent(ctrl, clock, cfg.SCROLL_ANCHOR_GRACE * 0.8)
    ctrl.scroll(_shift(hand, 1.0 * PALM), frame)
    assert backend.units == []                       # first frame back only re-syncs the clock


def test_pose_absent_longer_than_the_grace_resets_the_anchor(rig):
    ctrl, backend, clock, run, cfg, frame, hand = rig
    _absent(ctrl, clock, cfg.SCROLL_ANCHOR_GRACE + 0.2)
    backend.units.clear()
    far = _shift(hand, 1.0 * PALM)
    clock.advance(0.1)
    ctrl.scroll(far, frame)                          # new anchor right here
    run(0.0, 1.0, h=far)
    assert backend.units == []


def test_speed_is_capped_at_every_offset_beyond_the_full_speed_point(gui_stubs):
    from modules.scroll_control import ScrollController

    cfg = Config()
    ctrl = ScrollController(cfg, WheelBackend(), clock=FakeClock())
    for offset in (cfg.SCROLL_FULL_SPEED_OFFSET, 1.0, 1.5, 3.0, 10.0, -2.0):
        assert ctrl.speed(offset) == pytest.approx(cfg.SCROLL_MAX_SPEED)
    assert ctrl.speed(cfg.SCROLL_FULL_SPEED_OFFSET - 0.1) < cfg.SCROLL_MAX_SPEED
    assert ctrl.speed(cfg.SCROLL_DEADZONE) == 0


def test_reading_speed_scroll_is_gentle_near_the_dead_zone(gui_stubs):
    from modules.scroll_control import ScrollController

    cfg = Config()
    ctrl = ScrollController(cfg, WheelBackend(), clock=FakeClock())
    assert 0 < ctrl.speed(cfg.SCROLL_DEADZONE + 0.1) < 3        # a few notches per second at most


def test_debug_log_reports_anchor_set_reset_and_resets_between_lines(gui_stubs, capsys):
    from modules.scroll_control import ScrollController

    clock = FakeClock()
    ctrl = ScrollController(Config(), WheelBackend(), clock=clock, debug=True)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    hand = make_hand("IM")
    ctrl.scroll(hand, frame)
    for _ in range(10):
        clock.advance(1 / 30)
        ctrl.scroll(_shift(hand, 0.7 * PALM), frame)
    _absent(ctrl, clock, Config().SCROLL_ANCHOR_GRACE + 0.1)
    ctrl.scroll(hand, frame)
    clock.advance(0.3)
    ctrl.scroll(hand, frame)
    out = capsys.readouterr().out
    assert "[scroll] anchor set" in out and "[scroll] anchor reset" in out
    assert "anchor_resets=1" in out
