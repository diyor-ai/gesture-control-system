"""Every gesture has its own reachable pose; cursor gestures belong to one hand."""

import pytest

from modules.config import Config
from modules.gesture_engine import GestureEngine
from tests.conftest import make_hand, play

# (fingers up, hand label, expected gesture)
CONTINUOUS = [
    ("I",   "Right", "MOVE_CURSOR"),
    ("IT",  "Right", "MOVE_CURSOR"),   # thumb out next to the index: still the cursor
    ("IM",  "Right", "SCROLL"),
    ("IMT", "Right", "SCROLL"),
    ("TP",  "Right", "VOLUME"),
    ("TR",  "Right", "BRIGHTNESS"),
    ("",    "Right", "DRAG_WINDOW"),
    ("T",   "Right", "DRAG_WINDOW"),
    ("TI",  "Left",  "ZOOM"),
    ("IM",  "Left",  "SCROLL"),
    ("TP",  "Left",  "VOLUME"),
    ("TR",  "Left",  "BRIGHTNESS"),
    ("",    "Left",  "DRAG_WINDOW"),
]


@pytest.fixture(autouse=True)
def _window_drag_available(monkeypatch):
    """Pose tests assume a platform that supports DRAG_WINDOW."""
    monkeypatch.setattr(Config, "WINDOW_DRAG_ENABLED", True)


@pytest.mark.parametrize("mirror", [False, True], ids=["right-shape", "left-shape"])
@pytest.mark.parametrize("up,label,expected", CONTINUOUS)
def test_continuous_gestures(engine, clock, up, label, expected, mirror):
    out = play(engine, clock, make_hand(up, mirror=mirror), 5, label=label)
    assert set(out) == {expected}


def test_draw_replaces_cursor_only_when_canvas_enabled(engine, clock):
    hand = make_hand("I")
    assert set(play(engine, clock, hand, 3)) == {"MOVE_CURSOR"}
    assert set(play(engine, clock, hand, 3, canvas=True)) == {"DRAW"}


# ── The ZOOM / MOVE_CURSOR / CLICK / DRAW conflict ────────────────────────────

def test_thumb_and_index_on_primary_hand_never_zooms(engine, clock):
    out = play(engine, clock, make_hand("TI"), 10, label="Right")
    assert "ZOOM" not in out and set(out) == {"MOVE_CURSOR"}


def test_zoom_pose_belongs_to_the_secondary_hand(engine, clock):
    assert set(play(engine, clock, make_hand("TI"), 5, label="Left")) == {"ZOOM"}


# ── Primary hand ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("hand", [
    make_hand("I"),
    make_hand("I", pinch="index"),
    make_hand("M", pinch="middle"),
])
def test_secondary_hand_cannot_move_click_or_draw(engine, clock, hand):
    out = play(engine, clock, hand, 5, label="Left", canvas=True)
    # (a closed L-shape pinch is just the zoom pose at minimum spread)
    cursor_family = {"MOVE_CURSOR", "DRAW", "CLICK", "DOUBLE_CLICK", "RIGHT_CLICK"}
    assert not cursor_family & set(out)


def test_two_hands_only_the_primary_drives_the_cursor(engine, clock):
    seen = []
    for _ in range(5):
        seen.append((
            engine.classify(make_hand("I"), "Right"),
            engine.classify(make_hand("I", mirror=True), "Left"),
        ))
        engine.end_frame()
        clock.advance(1 / 30)
    assert all(r == "MOVE_CURSOR" and l == "IDLE" for r, l in seen)


def test_primary_hand_is_configurable(clock):
    cfg = Config()
    cfg.PRIMARY_HAND = "Left"
    cfg.STABILITY_FRAMES = 1
    eng = GestureEngine(cfg, clock=clock)
    assert set(play(eng, clock, make_hand("I"), 3, label="Left")) == {"MOVE_CURSOR"}
    assert set(play(eng, clock, make_hand("I"), 3, label="Right")) == {"IDLE"}
    assert set(play(eng, clock, make_hand("TI"), 3, label="Right")) == {"ZOOM"}


def test_invalid_primary_hand_is_rejected(clock):
    cfg = Config()
    cfg.PRIMARY_HAND = "Middle"
    with pytest.raises(ValueError):
        GestureEngine(cfg, clock=clock)


def test_hands_keep_separate_click_state(engine, clock):
    play(engine, clock, make_hand("I", pinch="index"), 3, label="Right")
    # the other hand holding a pose must not release or re-arm the right pinch
    out = play(engine, clock, make_hand("IM", mirror=True), 3, label="Left")
    assert set(out) == {"SCROLL"}
    assert set(play(engine, clock, make_hand("I", pinch="index"), 3, label="Right")) == {"IDLE"}


# ── Hold-to-fire gestures ─────────────────────────────────────────────────────

def test_play_pause_is_reachable_and_fires_once_after_the_hold(engine, clock):
    hand = make_hand("IMR")
    assert set(play(engine, clock, hand, 10)) == {"IDLE"}          # 0.33 s < 0.5 s
    out = play(engine, clock, hand, 30)
    assert out.count("MEDIA_PLAY_PAUSE") == 1
    assert "SCREENSHOT" not in out


def test_play_pause_fires_again_after_release(engine, clock):
    hand = make_hand("IMR")
    out = play(engine, clock, hand, 25)
    out += play(engine, clock, make_hand("I"), 3)
    out += play(engine, clock, hand, 25)
    assert out.count("MEDIA_PLAY_PAUSE") == 2


def test_open_palm_takes_a_screenshot_once_after_one_second(engine, clock):
    palm = make_hand("TIMRP")
    early = play(engine, clock, palm, 20)                          # 0.67 s
    assert set(early) == {"IDLE"} and engine.active_mode == "SCREENSHOT_HOLD"
    late = play(engine, clock, palm, 40)
    assert late.count("SCREENSHOT") == 1
    assert "MEDIA_PLAY_PAUSE" not in early + late


def test_screenshot_can_be_taken_again_after_releasing(engine, clock):
    palm = make_hand("TIMRP")
    out = play(engine, clock, palm, 40)
    out += play(engine, clock, make_hand(""), 3)
    out += play(engine, clock, palm, 40)
    assert out.count("SCREENSHOT") == 2


# ── Swipes ────────────────────────────────────────────────────────────────────

def _swipe(engine, clock, xs):
    out = []
    for x in xs:
        out.append(engine.classify(make_hand("IP", wrist_x=x), "Right"))
        engine.end_frame()
        clock.advance(1 / 30)
    return out


def test_swipe_right_is_next_track(engine, clock):
    assert _swipe(engine, clock, [0.30, 0.34, 0.38, 0.42, 0.46, 0.50, 0.54]).count("MEDIA_NEXT") == 1


def test_swipe_left_is_previous_track(engine, clock):
    assert _swipe(engine, clock, [0.70, 0.66, 0.62, 0.58, 0.54, 0.50, 0.46]).count("MEDIA_PREV") == 1


def test_horns_without_movement_do_nothing(engine, clock):
    assert set(_swipe(engine, clock, [0.5] * 20)) == {"IDLE"}


# ── Misc ──────────────────────────────────────────────────────────────────────

def test_unrecognised_pose_is_idle(engine, clock):
    assert set(play(engine, clock, make_hand("M"), 5)) == {"IDLE"}      # lone middle finger
    assert set(play(engine, clock, make_hand("IMRP"), 5)) == {"IDLE"}   # open palm, thumb folded


def test_fist_does_nothing_where_window_drag_is_not_implemented(clock):
    cfg = Config()
    cfg.WINDOW_DRAG_ENABLED = False
    cfg.STABILITY_FRAMES = 1
    eng = GestureEngine(cfg, clock=clock)
    assert set(play(eng, clock, make_hand(""), 5)) == {"IDLE"}
