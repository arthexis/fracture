#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from obs_plugins.obs_controller import OBSController


def latest_image(mse_dir: Path) -> Path | None:
    valid_exts = {".png", ".jpg", ".jpeg", ".webp"}
    try:
        return max(
            (p for p in mse_dir.iterdir() if p.suffix.lower() in valid_exts),
            key=lambda p: p.stat().st_mtime,
            default=None,
        )
    except FileNotFoundError:
        return None


def make_server(controller: OBSController, mse_dir: Path):
    from fastmcp import FastMCP
    server = FastMCP("obs-overlay-controller")


    snapshots: dict[str, dict] = {}

    @server.tool
    def snapshot_layout(name: str = "default") -> str:
        snapshots[name] = controller.snapshot_state()
        return f"snapshot saved: {name}"

    @server.tool
    def restore_snapshot(name: str = "default") -> str:
        if name not in snapshots:
            return f"snapshot not found: {name}"
        controller.restore_state(snapshots[name])
        return f"snapshot restored: {name}"

    @server.tool
    def set_share_source(source_name: str) -> str:
        controller.set_share_source(source_name)
        return f"share source set to {source_name}"

    @server.tool
    def lock_layout() -> str:
        controller.lock_layout()
        return "layout locked"

    @server.tool
    def unlock_layout() -> str:
        controller.unlock_layout()
        return "layout unlocked"

    @server.tool
    def preview_preset(name: str) -> str:
        if name.lower() not in {"prep", "live", "discussion", "brb"}:
            return f"unknown preset: {name}"
        return f"preview only: would apply preset {name}"

    @server.tool
    def set_notes(text: str) -> str:
        controller.set_notes(text)
        return "notes updated"

    @server.tool
    def set_chat_url(url: str) -> str:
        controller.set_chat_url(url)
        return "chat url updated"

    @server.tool
    def set_speaker_art(path: str) -> str:
        controller.set_speaker_art(path)
        return "speaker art updated"


    @server.tool
    def ensure_camera_source(device_id: str = "") -> str:
        controller.ensure_camera_source(device_id)
        return "camera source ensured"

    @server.tool
    def set_camera_crop(left: int, top: int, right: int, bottom: int) -> str:
        controller.set_camera_crop(left, top, right, bottom)
        return "camera crop updated"

    @server.tool
    def set_camera_filter_preset(preset: str) -> str:
        controller.set_camera_filter_preset(preset)
        return f"camera filter preset set to {preset}"

    @server.tool
    def set_speaker_mode(mode: str) -> str:
        controller.set_speaker_mode(mode)
        return f"speaker mode set to {mode}"

    @server.tool
    def apply_preset(name: str) -> str:
        controller.apply_preset(name)
        return f"applied preset: {name}"

    @server.tool
    def refresh_from_mse2_latest() -> str:
        image = latest_image(mse_dir)
        if image is None:
            return f"no images found in {mse_dir}"
        controller.set_speaker_art(str(image))
        return f"speaker art set to {image}"

    @server.tool
    def ensure_layout(chat_url: str, notes: str, card_frame: str, speaker_art: str) -> str:
        controller.ensure_layout(chat_url, notes, card_frame, speaker_art)
        return "layout ensured"

    @server.tool
    def health() -> str:
        return json.dumps({"status": "ok", "mse_dir": str(mse_dir)})

    return server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=4455)
    parser.add_argument("--password", default="")
    parser.add_argument("--mse-output-dir", default="./mse2_output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    from obsws_python import ReqClient
    ws = ReqClient(host=args.host, port=args.port, password=args.password, timeout=8)
    controller = OBSController(ws)
    server = make_server(controller, Path(args.mse_output_dir))
    server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
