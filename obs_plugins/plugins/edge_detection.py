from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2

from .base import PluginContext


@dataclass(slots=True)
class EdgeDetectionPlugin:
    """Basic image edge detection plugin configurable from OBS script UI."""

    name: str = "Edge Detection"
    key: str = "edge"

    _enabled: bool = False
    _input_path: str = ""
    _output_path: str = "./edge_output.png"
    _threshold_low: int = 50
    _threshold_high: int = 150
    _interval_ms: int = 0

    _timer_active: bool = False
    _context: PluginContext | None = None

    def _prefix(self, field: str) -> str:
        return f"{self.key}_{field}"

    def build_properties(self, props: object, obs: object) -> None:
        obs.obs_properties_add_bool(props, self._prefix("enabled"), "Enable edge detection")
        obs.obs_properties_add_path(
            props,
            self._prefix("input_path"),
            "Input image path",
            obs.OBS_PATH_FILE,
            "Images (*.png *.jpg *.jpeg *.bmp)",
            None,
        )
        obs.obs_properties_add_path(
            props,
            self._prefix("output_path"),
            "Output image path",
            obs.OBS_PATH_FILE_SAVE,
            "PNG (*.png)",
            None,
        )
        obs.obs_properties_add_int(props, self._prefix("threshold_low"), "Low threshold", 0, 255, 1)
        obs.obs_properties_add_int(props, self._prefix("threshold_high"), "High threshold", 0, 255, 1)
        obs.obs_properties_add_int(
            props,
            self._prefix("interval_ms"),
            "Auto-run interval (ms, 0 disables)",
            0,
            60000,
            100,
        )
        obs.obs_properties_add_button(
            props,
            self._prefix("run_now"),
            "Run edge detection now",
            self._run_now_button,
        )

    def defaults(self, settings: object, obs: object) -> None:
        obs.obs_data_set_default_bool(settings, self._prefix("enabled"), self._enabled)
        obs.obs_data_set_default_string(settings, self._prefix("input_path"), self._input_path)
        obs.obs_data_set_default_string(settings, self._prefix("output_path"), self._output_path)
        obs.obs_data_set_default_int(settings, self._prefix("threshold_low"), self._threshold_low)
        obs.obs_data_set_default_int(settings, self._prefix("threshold_high"), self._threshold_high)
        obs.obs_data_set_default_int(settings, self._prefix("interval_ms"), self._interval_ms)

    def update(self, settings: object, obs: object) -> None:
        self._enabled = obs.obs_data_get_bool(settings, self._prefix("enabled"))
        self._input_path = obs.obs_data_get_string(settings, self._prefix("input_path"))
        self._output_path = obs.obs_data_get_string(settings, self._prefix("output_path"))
        self._threshold_low = obs.obs_data_get_int(settings, self._prefix("threshold_low"))
        self._threshold_high = obs.obs_data_get_int(settings, self._prefix("threshold_high"))
        self._interval_ms = obs.obs_data_get_int(settings, self._prefix("interval_ms"))

        self._sync_timer(obs)

    def on_load(self, context: PluginContext) -> None:
        self._context = context
        self._sync_timer(context.obs_module)

    def on_unload(self, context: PluginContext) -> None:
        if self._timer_active:
            context.obs_module.timer_remove(self._timer_tick)
            self._timer_active = False
        self._context = None

    def _sync_timer(self, obs: object) -> None:
        should_run = self._enabled and self._interval_ms > 0
        if should_run and not self._timer_active:
            obs.timer_add(self._timer_tick, self._interval_ms)
            self._timer_active = True
        elif not should_run and self._timer_active:
            obs.timer_remove(self._timer_tick)
            self._timer_active = False

    def _run_now_button(self, _props: object, _prop: object) -> bool:
        self._process_once()
        return True

    def _timer_tick(self) -> None:
        self._process_once()

    def _process_once(self) -> None:
        if not self._enabled:
            return

        in_path = Path(self._input_path)
        if not in_path.exists():
            print(f"[EdgeDetectionPlugin] Input not found: {in_path}")
            return

        image = cv2.imread(str(in_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            print(f"[EdgeDetectionPlugin] Could not read image: {in_path}")
            return

        edges = cv2.Canny(image, self._threshold_low, self._threshold_high)
        out_path = Path(self._output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        success = cv2.imwrite(str(out_path), edges)
        if success:
            print(f"[EdgeDetectionPlugin] Wrote: {out_path}")
        else:
            print(f"[EdgeDetectionPlugin] Failed to write: {out_path}")
