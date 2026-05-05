#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from obs_plugins.obs_controller import OBSController


def latest_image(mse_dir: Path) -> Path | None:
    images = sorted(
        [p for p in mse_dir.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return images[0] if images else None


def make_server(controller: OBSController, mse_dir: Path):
    from fastmcp import FastMCP
    server = FastMCP("obs-overlay-controller")

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
    def set_speaker_mode(mode: str) -> str:
        controller.set_speaker_mode(mode)
        return f"speaker mode set to {mode}"

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
