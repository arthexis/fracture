from pathlib import Path

from scripts.overlay_mcp_server import latest_image


def test_latest_image_picks_newest(tmp_path: Path):
    older = tmp_path / "a.png"
    newer = tmp_path / "b.png"
    older.write_bytes(b"a")
    newer.write_bytes(b"b")
    import os, time
    time.sleep(0.01)
    os.utime(newer, None)
    assert latest_image(tmp_path).name == "b.png"


def test_latest_image_returns_none_when_empty(tmp_path: Path):
    assert latest_image(tmp_path) is None
