# Arthexis OBS Plugin Host (Python)

This repository is a starter skeleton for hosting multiple OBS Python plugins behind one OBS script entrypoint.

## Quick start

1. Install dependencies:
   ```bash
   pip install -e .
   ```
2. Open OBS, then go to **Tools -> Scripts**.
3. Add `scripts/obs_plugin_host.py`.
4. Configure plugin settings from OBS properties.

## Current plugin

- **Edge Detection Plugin**
  - Reads an input image path.
  - Runs Canny edge detection with configurable thresholds.
  - Writes the output image to a configurable path.
  - Can auto-run on an interval or run manually via a button.

## Structure

- `scripts/obs_plugin_host.py` - OBS-facing script entrypoint.
- `obs_plugins/core.py` - plugin manager and shared state.
- `obs_plugins/plugins/base.py` - plugin protocol/base class.
- `obs_plugins/plugins/edge_detection.py` - initial plugin implementation.

## Notes

This is intentionally a foundation so we can add many Arthexis-side automations and plugin modules over time.


## OBS overlay automation

This repo now includes an automated overlay stack and MCP control server.

### One-shot OBS setup script

Use `scripts/setup_obs_overlay.py` to configure OBS sources/scenes automatically:

```bash
python scripts/setup_obs_overlay.py   --chat-url "https://your-chat-widget"   --card-frame ./assets/card_frame.png   --speaker-art ./assets/speaker_default.png
```

Prerequisites:
- OBS with WebSocket enabled (default port 4455).
- Python dependencies installed.

### MCP server for model-driven control

Run:

```bash
python scripts/overlay_mcp_server.py --mse-output-dir ./mse2_output
```

Tools exposed:
- `ensure_layout`
- `set_notes`
- `set_chat_url`
- `set_speaker_art`
- `refresh_from_mse2_latest`
- `health`


### Continuous MSE2 watcher

To keep OBS synced automatically with newly generated cards:

```bash
python scripts/mse2_watcher.py --mse-output-dir ./mse2_output
```

### Additional MCP tools

- `apply_preset` (`prep`, `live`, `discussion`, `brb`)
- `set_speaker_mode` (`generated`, `camera`, `hybrid`)


### Setup reconciliation and capability report

`setup_obs_overlay.py` now prints a JSON report with:
- detected OBS input-kind capabilities
- created/updated sources
- created scene-items


### Phase 2 camera controls

New MCP camera tools:
- `ensure_camera_source`
- `set_camera_crop`
- `set_camera_filter_preset` (`none`, `cinematic`, `high_contrast`)


### Phase 3 orchestration tools

New MCP workflow tools:
- `snapshot_layout`
- `restore_snapshot`
- `set_share_source`
- `lock_layout` / `unlock_layout`
- `preview_preset`


### Phase 4 test coverage

Added negative/failure-path tests for:
- invalid mode/preset/filter inputs
- lock enforcement on mutable operations
- reconcile update behavior on repeat layout runs
- empty directory behavior for latest-image selection


### Final operational notes

- Layout lock now guards all mutating operations (preset/mode/source/text/image updates).
- Camera source provisioning now tries multiple input kinds for cross-platform compatibility (`dshow_input`, `av_capture_input`, `v4l2_input`).
