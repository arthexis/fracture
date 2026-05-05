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
    notes: str = "Overlay_Notes"
    background: str = "Background"


class OBSController:
    def __init__(self, ws: Any, names: OverlaySourceNames | None = None) -> None:
        self.ws = ws
        self.names = names or OverlaySourceNames()

    def ensure_layout(self, chat_url: str, notes_text: str, card_frame_path: str, speaker_art_path: str) -> None:
        self._ensure_scene(self.names.scene)
        self._ensure_color_source(self.names.background, 0xFF111111)
        self._ensure_browser_source(self.names.chat, chat_url, 580, 660)
        self._ensure_text_source(self.names.notes, notes_text)
        self._ensure_image_source(self.names.speaker_frame, card_frame_path)
        self._ensure_image_source(self.names.speaker_art, speaker_art_path)
        self._ensure_display_capture(self.names.share)

        self._ensure_scene_item(self.names.background, DEFAULT_LAYOUT.share_rect)
        self._ensure_scene_item(self.names.share, DEFAULT_LAYOUT.share_rect)
        self._ensure_scene_item(self.names.chat, DEFAULT_LAYOUT.chat_rect)
        self._ensure_scene_item(self.names.speaker_art, DEFAULT_LAYOUT.speaker_rect)
        self._ensure_scene_item(self.names.speaker_frame, DEFAULT_LAYOUT.speaker_rect)
        self._ensure_scene_item(self.names.notes, DEFAULT_LAYOUT.notes_rect)

    def set_notes(self, text: str) -> None:
        self.ws.set_input_settings(self.names.notes, {"text": text}, True)

    def set_chat_url(self, url: str) -> None:
        self.ws.set_input_settings(self.names.chat, {"url": url}, True)

    def set_speaker_art(self, path: str) -> None:
        p = str(Path(path).resolve())
        self.ws.set_input_settings(self.names.speaker_art, {"file": p}, True)

    def _ensure_scene(self, name: str) -> None:
        scenes = [s["sceneName"] for s in self.ws.get_scene_list().scenes]
        if name not in scenes:
            self.ws.create_scene(name)

    def _ensure_display_capture(self, name: str) -> None:
        self._ensure_input(name, "monitor_capture", {})

    def _ensure_browser_source(self, name: str, url: str, width: int, height: int) -> None:
        self._ensure_input(name, "browser_source", {"url": url, "width": width, "height": height})

    def _ensure_text_source(self, name: str, text: str) -> None:
        self._ensure_input(name, "text_gdiplus_v2", {"text": text, "font": {"face": "Arial", "size": 28}})

    def _ensure_image_source(self, name: str, file_path: str) -> None:
        self._ensure_input(name, "image_source", {"file": str(Path(file_path).resolve())})

    def _ensure_color_source(self, name: str, color: int) -> None:
        self._ensure_input(name, "color_source_v3", {"color": color, "width": 1920, "height": 1080})

    def _ensure_input(self, name: str, kind: str, settings: dict[str, Any]) -> None:
        existing = [i["inputName"] for i in self.ws.get_input_list().inputs]
        if name not in existing:
            self.ws.create_input(self.names.scene, name, kind, settings, True)
        else:
            self.ws.set_input_settings(name, settings, True)

    def _ensure_scene_item(self, source_name: str, rect: Rect) -> None:
        items = self.ws.get_scene_item_list(self.names.scene).scene_items
        item_id = None
        for item in items:
            if item["sourceName"] == source_name:
                item_id = item["sceneItemId"]
                break
        if item_id is None:
            item_id = self.ws.create_scene_item(self.names.scene, source_name).scene_item_id
        self.ws.set_scene_item_transform(
            self.names.scene,
            item_id,
            {
                "positionX": rect.x,
                "positionY": rect.y,
                "boundsType": "OBS_BOUNDS_STRETCH",
                "boundsWidth": rect.width,
                "boundsHeight": rect.height,
            },
        )
