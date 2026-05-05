#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from obs_plugins.obs_controller import OBSController
from scripts.overlay_mcp_server import latest_image


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Watch MSE2 output dir and update OBS speaker art automatically.")
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=4455)
    p.add_argument("--password", default="")
    p.add_argument("--mse-output-dir", default="./mse2_output")
    p.add_argument("--poll-interval", type=float, default=1.0)
    p.add_argument("--stability-window", type=float, default=1.5)
    return p.parse_args()


def _is_stable(path: Path, window_s: float) -> bool:
    age = time.time() - path.stat().st_mtime
    return age >= window_s


def main() -> int:
    args = parse_args()
    from obsws_python import ReqClient

    ws = ReqClient(host=args.host, port=args.port, password=args.password, timeout=8)
    controller = OBSController(ws)
    mse_dir = Path(args.mse_output_dir)
    last_path = None
    while True:
        image = latest_image(mse_dir)
        if image is not None and image != last_path and _is_stable(image, args.stability_window):
            controller.set_speaker_art(str(image))
            last_path = image
            print(f"[mse2_watcher] Updated speaker art: {image}")
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    raise SystemExit(main())
