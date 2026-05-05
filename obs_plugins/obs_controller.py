from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .layout import DEFAULT_LAYOUT, Rect
from .presets import PRESETS


@dataclass(slots=True)
class OverlaySourceNames:
    scene: str = "LiveLayout_Main"
    share: str = "Main_Share_Capture"
    chat: str = "Chat_Widget"
    speaker_frame: str = "SpeakerCard_Frame"
    speaker_art: str = "SpeakerCard_Art"
    speaker_camera: str = "SpeakerCard_Camera"
    notes: str = "Overlay_Notes"
    background: str = "Background"


@dataclass(slots=True)
class SourceKinds:
    monitor_capture: str = "monitor_capture"
    browser_source: str = "browser_source"
    image_source: str = "image_source"
    color_source: str = "color_source_v3"
    text_source: tuple[str, ...] = ("text_gdiplus_v2", "text_ft2_source_v2")


class OBSController:
    def __init__(self, ws: Any, names: OverlaySourceNames | None = None, kinds: SourceKinds | None = None) -> None:
        self.ws = ws
        self.names = names or OverlaySourceNames()
        self.kinds = kinds or SourceKinds()
        self._layout_locked = False

    def probe_capabilities(self) -> dict[str, Any]:
        input_kinds = {entry.get("inputKind") for entry in self.ws.get_input_kind_list(False).input_kinds}
        return {
            "text_source_supported": any(kind in input_kinds for kind in self.kinds.text_source),
            "monitor_capture_supported": self.kinds.monitor_capture in input_kinds,
            "browser_source_supported": self.kinds.browser_source in input_kinds,
            "image_source_supported": self.kinds.image_source in input_kinds,
            "color_source_supported": self.kinds.color_source in input_kinds,
        }

    def ensure_layout(self, chat_url: str, notes_text: str, card_frame_path: str, speaker_art_path: str) -> dict[str, list[str]]:
        self._assert_unlocked()
        report = {"created": [], "updated": [], "scene_items_created": []}
        self._ensure_scene(self.names.scene)
        self._ensure_color_source(self.names.background, 0xFF111111, report)
        self._ensure_browser_source(self.names.chat, chat_url, 580, 660, report)
        self._ensure_text_source(self.names.notes, notes_text, report)
        self._ensure_image_source(self.names.speaker_frame, card_frame_path, report)
        self._ensure_image_source(self.names.speaker_art, speaker_art_path, report)
        self._ensure_display_capture(self.names.share, report)

        self._ensure_scene_item(self.names.background, Rect(0, 0, 1920, 1080), stretch=True, report=report)
        self._ensure_scene_item(self.names.share, DEFAULT_LAYOUT.share_rect, stretch=True, report=report)
        self._ensure_scene_item(self.names.chat, DEFAULT_LAYOUT.chat_rect, stretch=True, report=report)
        self._ensure_scene_item(self.names.speaker_art, DEFAULT_LAYOUT.speaker_rect, stretch=True, report=report)
        self._ensure_scene_item(self.names.speaker_frame, DEFAULT_LAYOUT.speaker_rect, stretch=True, report=report)
        self._ensure_scene_item(self.names.notes, DEFAULT_LAYOUT.notes_rect, stretch=True, report=report)
        return report


    def ensure_camera_source(self, device_id: str = "") -> None:
        self._assert_unlocked()
        kinds = ("dshow_input", "av_capture_input", "v4l2_input")
        last_error = None
        for kind in kinds:
            try:
                self._ensure_input(self.names.speaker_camera, kind, {"video_device_id": device_id}, {"created": [], "updated": [], "scene_items_created": []})
                self._ensure_scene_item(self.names.speaker_camera, DEFAULT_LAYOUT.speaker_rect, stretch=True, report={"created": [], "updated": [], "scene_items_created": []})
                return
            except Exception as exc:
                last_error = exc
        raise RuntimeError("Unable to create camera source using known input kinds") from last_error

    def set_camera_crop(self, left: int, top: int, right: int, bottom: int) -> None:
        self._assert_unlocked()
        item_id = self._scene_item_id(self.names.speaker_camera)
        if item_id is None:
            return
        self.ws.set_scene_item_transform(
            self.names.scene,
            item_id,
            {"cropLeft": left, "cropTop": top, "cropRight": right, "cropBottom": bottom},
        )

    def set_camera_filter_preset(self, preset: str) -> None:
        self._assert_unlocked()
        key = preset.lower()
        if key == "none":
            self._remove_filter_if_exists(self.names.speaker_camera, "SpeakerColorCorrection")
            return
        if key == "cinematic":
            self._upsert_filter(
                self.names.speaker_camera,
                "SpeakerColorCorrection",
                "color_filter_v2",
                {"gamma": -0.12, "contrast": 0.18, "saturation": -0.08},
            )
            return
        if key == "high_contrast":
            self._upsert_filter(
                self.names.speaker_camera,
                "SpeakerColorCorrection",
                "color_filter_v2",
                {"gamma": -0.2, "contrast": 0.3, "saturation": 0.0},
            )
            return
        raise ValueError("Unknown camera filter preset")

    def set_speaker_mode(self, mode: str) -> None:
        self._assert_unlocked()
        if mode not in {"generated", "camera", "hybrid"}:
            raise ValueError("mode must be one of: generated, camera, hybrid")
        self._set_item_enabled(self.names.speaker_art, mode in {"generated", "hybrid"})
        self._set_item_enabled(self.names.speaker_camera, mode in {"camera", "hybrid"})
        self._set_item_enabled(self.names.speaker_frame, True)

    def apply_preset(self, name: str) -> None:
        self._assert_unlocked()
        key = name.lower()
        if key not in PRESETS:
            raise ValueError(f"unknown preset: {name}")
        preset = PRESETS[key]
        self._set_item_enabled(self.names.share, preset.share)
        self._set_item_enabled(self.names.chat, preset.chat)
        self._set_item_enabled(self.names.speaker_frame, preset.speaker_frame)
        self._set_item_enabled(self.names.speaker_art, preset.speaker_art)
        self._set_item_enabled(self.names.speaker_camera, preset.speaker_camera)
        self._set_item_enabled(self.names.notes, preset.notes)


    def lock_layout(self) -> None:
        self._layout_locked = True

    def unlock_layout(self) -> None:
        self._layout_locked = False

    def is_layout_locked(self) -> bool:
        return self._layout_locked

    def set_share_source(self, source_name: str) -> None:
        if self._layout_locked:
            raise RuntimeError("layout is locked")
        self.names.share = source_name

    def snapshot_state(self) -> dict[str, Any]:
        return {
            "scene": self.names.scene,
            "share": self.names.share,
            "chat": self.names.chat,
            "speaker_frame": self.names.speaker_frame,
            "speaker_art": self.names.speaker_art,
            "speaker_camera": self.names.speaker_camera,
            "notes": self.names.notes,
            "background": self.names.background,
            "layout_locked": self._layout_locked,
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        if self._layout_locked:
            raise RuntimeError("layout is locked")
        self.names.scene = state.get("scene", self.names.scene)
        self.names.share = state.get("share", self.names.share)
        self.names.chat = state.get("chat", self.names.chat)
        self.names.speaker_frame = state.get("speaker_frame", self.names.speaker_frame)
        self.names.speaker_art = state.get("speaker_art", self.names.speaker_art)
        self.names.speaker_camera = state.get("speaker_camera", self.names.speaker_camera)
        self.names.notes = state.get("notes", self.names.notes)
        self.names.background = state.get("background", self.names.background)
        self._layout_locked = bool(state.get("layout_locked", self._layout_locked))

    def set_notes(self, text: str) -> None:
        self._assert_unlocked()
        self.ws.set_input_settings(self.names.notes, {"text": text}, True)

    def set_chat_url(self, url: str) -> None:
        self._assert_unlocked()
        self.ws.set_input_settings(self.names.chat, {"url": url}, True)

    def set_speaker_art(self, path: str) -> None:
        self._assert_unlocked()
        self.ws.set_input_settings(self.names.speaker_art, {"file": str(Path(path).resolve())}, True)

    def _ensure_scene(self, name: str) -> None:
        scenes = [s["sceneName"] for s in self.ws.get_scene_list().scenes]
        if name not in scenes:
            self.ws.create_scene(name)

    def _ensure_display_capture(self, name: str, report: dict[str, list[str]]) -> None:
        self._ensure_input(name, self.kinds.monitor_capture, {}, report)

    def _ensure_browser_source(self, name: str, url: str, width: int, height: int, report: dict[str, list[str]]) -> None:
        self._ensure_input(name, self.kinds.browser_source, {"url": url, "width": width, "height": height}, report)

    def _ensure_text_source(self, name: str, text: str, report: dict[str, list[str]]) -> None:
        for kind in self.kinds.text_source:
            try:
                self._ensure_input(name, kind, {"text": text, "font": {"face": "Arial", "size": 28}}, report)
                return
            except Exception:
                continue
        raise RuntimeError("Could not create text source using supported kinds")

    def _ensure_image_source(self, name: str, file_path: str, report: dict[str, list[str]]) -> None:
        self._ensure_input(name, self.kinds.image_source, {"file": str(Path(file_path).resolve())}, report)

    def _ensure_color_source(self, name: str, color: int, report: dict[str, list[str]]) -> None:
        self._ensure_input(name, self.kinds.color_source, {"color": color, "width": 1920, "height": 1080}, report)

    def _ensure_input(self, name: str, kind: str, settings: dict[str, Any], report: dict[str, list[str]]) -> None:
        existing = [i["inputName"] for i in self.ws.get_input_list().inputs]
        if name not in existing:
            self.ws.create_input(self.names.scene, name, kind, settings, True)
            report["created"].append(name)
        else:
            self.ws.set_input_settings(name, settings, True)
            report["updated"].append(name)

    def _ensure_scene_item(self, source_name: str, rect: Rect, stretch: bool, report: dict[str, list[str]]) -> None:
        item_id = self._scene_item_id(source_name)
        if item_id is None:
            item_id = self.ws.create_scene_item(self.names.scene, source_name).scene_item_id
            report["scene_items_created"].append(source_name)
        transform = {"positionX": rect.x, "positionY": rect.y}
        if stretch:
            transform.update({"boundsType": "OBS_BOUNDS_STRETCH", "boundsWidth": rect.width, "boundsHeight": rect.height})
        self.ws.set_scene_item_transform(self.names.scene, item_id, transform)

    def _scene_item_id(self, source_name: str) -> int | None:
        items = self.ws.get_scene_item_list(self.names.scene).scene_items
        for item in items:
            if item["sourceName"] == source_name:
                return item["sceneItemId"]
        return None

    def _upsert_filter(self, source_name: str, filter_name: str, filter_kind: str, settings: dict[str, Any]) -> None:
        filters = self.ws.get_source_filter_list(source_name).filters
        names = {f["filterName"] for f in filters}
        if filter_name not in names:
            self.ws.create_source_filter(source_name, filter_name, filter_kind, settings)
        else:
            self.ws.set_source_filter_settings(source_name, filter_name, settings, True)

    def _remove_filter_if_exists(self, source_name: str, filter_name: str) -> None:
        filters = self.ws.get_source_filter_list(source_name).filters
        names = {f["filterName"] for f in filters}
        if filter_name in names:
            self.ws.remove_source_filter(source_name, filter_name)

    def _assert_unlocked(self) -> None:
        if self._layout_locked:
            raise RuntimeError("layout is locked")

    def _set_item_enabled(self, source_name: str, enabled: bool) -> None:
        item_id = self._scene_item_id(source_name)
        if item_id is None:
            return
        self.ws.set_scene_item_enabled(self.names.scene, item_id, enabled)
