#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from obs_plugins.obs_controller import OBSController


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Configure OBS layout for card+chat+share overlay.")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=4455)
    parser.add_argument("--password", default="")
    parser.add_argument("--chat-url", required=True)
    parser.add_argument("--notes", default="References / editorial notes")
    parser.add_argument("--card-frame", required=True)
    parser.add_argument("--speaker-art", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    from obsws_python import ReqClient

    ws = ReqClient(host=args.host, port=args.port, password=args.password, timeout=8)
    controller = OBSController(ws)
    capabilities = controller.probe_capabilities()
    report = controller.ensure_layout(
        chat_url=args.chat_url,
        notes_text=args.notes,
        card_frame_path=str(Path(args.card_frame).resolve()),
        speaker_art_path=str(Path(args.speaker_art).resolve()),
    )
    print("OBS layout configured successfully.")
    print(json.dumps({"capabilities": capabilities, "reconcile": report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
