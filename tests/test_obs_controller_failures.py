import pytest

from obs_plugins.obs_controller import OBSController
from tests.test_obs_controller import FakeWS


def _controller_with_layout() -> tuple[OBSController, FakeWS]:
    ws = FakeWS()
    c = OBSController(ws)
    c.ensure_layout("https://chat", "hello", "/tmp/a.png", "/tmp/b.png")
    ws.create_input("LiveLayout_Main", "SpeakerCard_Camera", "dshow_input", {}, True)
    ws.create_scene_item("LiveLayout_Main", "SpeakerCard_Camera")
    return c, ws


def test_set_speaker_mode_rejects_invalid_value():
    c, _ = _controller_with_layout()
    with pytest.raises(ValueError):
        c.set_speaker_mode("bad")


def test_apply_preset_rejects_invalid_value():
    c, _ = _controller_with_layout()
    with pytest.raises(ValueError):
        c.apply_preset("unknown")


def test_set_camera_filter_rejects_invalid_value():
    c, _ = _controller_with_layout()
    with pytest.raises(ValueError):
        c.set_camera_filter_preset("vhs")


def test_locked_layout_blocks_mutation_calls():
    c, _ = _controller_with_layout()
    c.lock_layout()
    with pytest.raises(RuntimeError):
        c.set_share_source("Other")
    with pytest.raises(RuntimeError):
        c.restore_state({"share": "Other"})


def test_ensure_layout_reconcile_reports_updates_on_second_run():
    c, _ = _controller_with_layout()
    report = c.ensure_layout("https://chat2", "hello2", "/tmp/c.png", "/tmp/d.png")
    assert report["updated"]


def test_lock_blocks_all_mutating_layout_updates():
    c, _ = _controller_with_layout()
    c.lock_layout()
    import pytest
    with pytest.raises(RuntimeError):
        c.apply_preset("live")
    with pytest.raises(RuntimeError):
        c.set_notes("x")
    with pytest.raises(RuntimeError):
        c.set_speaker_mode("generated")
