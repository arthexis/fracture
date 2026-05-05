from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VisibilityPreset:
    share: bool
    chat: bool
    speaker_frame: bool
    speaker_art: bool
    speaker_camera: bool
    notes: bool


PRESETS: dict[str, VisibilityPreset] = {
    "prep": VisibilityPreset(share=False, chat=True, speaker_frame=True, speaker_art=True, speaker_camera=False, notes=True),
    "live": VisibilityPreset(share=True, chat=True, speaker_frame=True, speaker_art=True, speaker_camera=False, notes=True),
    "discussion": VisibilityPreset(share=True, chat=True, speaker_frame=True, speaker_art=False, speaker_camera=True, notes=True),
    "brb": VisibilityPreset(share=False, chat=False, speaker_frame=False, speaker_art=False, speaker_camera=False, notes=True),
}
