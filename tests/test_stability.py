"""Debouncing (N consecutive frames) and the hand-loss grace period."""

from modules.config import Config
from tests.conftest import make_hand, play

POINT = make_hand("I")
PEACE = make_hand("IM")
PINCH = make_hand("I", pinch="index")


def test_default_requires_several_consecutive_frames():
    assert Config().STABILITY_FRAMES >= 2


def test_pose_activates_only_after_n_consecutive_frames(stable_engine, clock):
    n = Config().STABILITY_FRAMES
    out = play(stable_engine, clock, POINT, n + 2)
    assert out[: n - 1] == ["IDLE"] * (n - 1)
    assert set(out[n - 1:]) == {"MOVE_CURSOR"}


def test_flickering_between_two_poses_never_activates_either(stable_engine, clock):
    out = []
    for _ in range(10):
        out += play(stable_engine, clock, POINT, 1)
        out += play(stable_engine, clock, PEACE, 1)
    assert set(out) == {"IDLE"}


def test_switching_pose_goes_idle_instead_of_repeating_the_old_gesture(stable_engine, clock):
    n = Config().STABILITY_FRAMES
    assert set(play(stable_engine, clock, PEACE, n + 3)[n - 1:]) == {"SCROLL"}
    out = play(stable_engine, clock, POINT, n + 3)
    assert out[: n - 1] == ["IDLE"] * (n - 1)       # no stale SCROLL while the change is pending
    assert out[-1] == "MOVE_CURSOR"


def test_one_frame_glitch_does_not_rearm_a_held_click(stable_engine, clock):
    out = play(stable_engine, clock, PINCH, 6)
    out += play(stable_engine, clock, POINT, 1)      # detector glitch
    out += play(stable_engine, clock, PINCH, 6)
    assert out.count("CLICK") == 1
    assert "DOUBLE_CLICK" not in out


def test_one_frame_glitch_does_not_interrupt_scrolling_state(stable_engine, clock):
    play(stable_engine, clock, PEACE, 6)
    glitch = play(stable_engine, clock, POINT, 1)
    assert glitch == ["IDLE"]                        # never a wrong gesture
    assert set(play(stable_engine, clock, PEACE, 3)) == {"SCROLL"}


def test_stability_of_one_frame_means_immediate(engine, clock):
    assert play(engine, clock, POINT, 1) == ["MOVE_CURSOR"]


# ── Hand-loss grace period ────────────────────────────────────────────────────

def _lose_hand(engine, clock, frames):
    for _ in range(frames):
        engine.end_frame()
        clock.advance(1 / 30)


def test_short_hand_loss_keeps_state_so_a_held_pinch_does_not_reclick(stable_engine, clock):
    grace = Config().HAND_LOSS_GRACE_FRAMES
    out = play(stable_engine, clock, PINCH, 6)
    _lose_hand(stable_engine, clock, grace)
    clock.advance(1.0)
    out += play(stable_engine, clock, PINCH, 6)
    assert out.count("CLICK") == 1


def test_long_hand_loss_resets_state(stable_engine, clock):
    grace = Config().HAND_LOSS_GRACE_FRAMES
    out = play(stable_engine, clock, PINCH, 6)
    _lose_hand(stable_engine, clock, grace + 1)
    clock.advance(1.0)
    out += play(stable_engine, clock, PINCH, 6)
    assert out.count("CLICK") == 2


def test_active_mode_returns_to_idle_without_hands(stable_engine, clock):
    play(stable_engine, clock, PEACE, 6)
    assert stable_engine.active_mode == "SCROLL"
    _lose_hand(stable_engine, clock, 1)
    assert stable_engine.active_mode == "IDLE"
