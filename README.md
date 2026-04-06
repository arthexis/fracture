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
