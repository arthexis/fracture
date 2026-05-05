from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .layout import DEFAULT_LAYOUT, Rect


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

    def ensure_layout(self, chat_url: str, notes_text: str, card_frame_path: str, speaker_art_path: str) -> None:
        self._ensure_scene(self.names.scene)
        self._ensure_color_source(self.names.background, 0xFF111111)
        self._ensure_browser_source(self.names.chat, chat_url, 580, 660)
        self._ensure_text_source(self.names.notes, notes_text)
        self._ensure_image_source(self.names.speaker_frame, card_frame_path)
        self._ensure_image_source(self.names.speaker_art, speaker_art_path)
        self._ensure_display_capture(self.names.share)

        self._ensure_scene_item(self.names.background, Rect(0, 0, 1920, 1080), stretch=True)
        self._ensure_scene_item(self.names.share, DEFAULT_LAYOUT.share_rect, stretch=True)
        self._ensure_scene_item(self.names.chat, DEFAULT_LAYOUT.chat_rect, stretch=True)
        self._ensure_scene_item(self.names.speaker_art, DEFAULT_LAYOUT.speaker_rect, stretch=True)
        self._ensure_scene_item(self.names.speaker_frame, DEFAULT_LAYOUT.speaker_rect, stretch=True)
        self._ensure_scene_item(self.names.notes, DEFAULT_LAYOUT.notes_rect, stretch=True)

    def set_speaker_mode(self, mode: str) -> None:
        if mode not in {"generated", "camera", "hybrid"}:
            raise ValueError("mode must be one of: generated, camera, hybrid")
        self._set_item_enabled(self.names.speaker_art, mode in {"generated", "hybrid"})
        self._set_item_enabled(self.names.speaker_camera, mode in {"camera", "hybrid"})
        self._set_item_enabled(self.names.speaker_frame, True)

    def set_notes(self, text: str) -> None:
        self.ws.set_input_settings(self.names.notes, {"text": text}, True)

    def set_chat_url(self, url: str) -> None:
        self.ws.set_input_settings(self.names.chat, {"url": url}, True)

    def set_speaker_art(self, path: str) -> None:
        self.ws.set_input_settings(self.names.speaker_art, {"file": str(Path(path).resolve())}, True)

    def _ensure_scene(self, name: str) -> None:
        scenes = [s["sceneName"] for s in self.ws.get_scene_list().scenes]
        if name not in scenes:
            self.ws.create_scene(name)

    def _ensure_display_capture(self, name: str) -> None:
        self._ensure_input(name, self.kinds.monitor_capture, {})

    def _ensure_browser_source(self, name: str, url: str, width: int, height: int) -> None:
        self._ensure_input(name, self.kinds.browser_source, {"url": url, "width": width, "height": height})

    def _ensure_text_source(self, name: str, text: str) -> None:
        for kind in self.kinds.text_source:
            try:
                self._ensure_input(name, kind, {"text": text, "font": {"face": "Arial", "size": 28}})
                return
            except Exception:
                continue
        raise RuntimeError("Could not create text source using supported kinds")

    def _ensure_image_source(self, name: str, file_path: str) -> None:
        self._ensure_input(name, self.kinds.image_source, {"file": str(Path(file_path).resolve())})

    def _ensure_color_source(self, name: str, color: int) -> None:
        self._ensure_input(name, self.kinds.color_source, {"color": color, "width": 1920, "height": 1080})

    def _ensure_input(self, name: str, kind: str, settings: dict[str, Any]) -> None:
        existing = [i["inputName"] for i in self.ws.get_input_list().inputs]
        if name not in existing:
            self.ws.create_input(self.names.scene, name, kind, settings, True)
        else:
            self.ws.set_input_settings(name, settings, True)

    def _ensure_scene_item(self, source_name: str, rect: Rect, stretch: bool) -> None:
        item_id = self._scene_item_id(source_name)
        if item_id is None:
            item_id = self.ws.create_scene_item(self.names.scene, source_name).scene_item_id
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

    def _set_item_enabled(self, source_name: str, enabled: bool) -> None:
        item_id = self._scene_item_id(source_name)
        if item_id is None:
            return
        self.ws.set_scene_item_enabled(self.names.scene, item_id, enabled)
