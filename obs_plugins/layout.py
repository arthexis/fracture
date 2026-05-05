from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rect:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class LayoutSpec:
    canvas_width: int = 1920
    canvas_height: int = 1080
    left_column_width: int = 580
    notes_height: int = 120
    speaker_height: int = 420

    @property
    def chat_rect(self) -> Rect:
        return Rect(0, 0, self.left_column_width, self.canvas_height - self.speaker_height)

    @property
    def speaker_rect(self) -> Rect:
        return Rect(
            0,
            self.canvas_height - self.speaker_height,
            self.left_column_width,
            self.speaker_height,
        )

    @property
    def share_rect(self) -> Rect:
        return Rect(
            self.left_column_width,
            0,
            self.canvas_width - self.left_column_width,
            self.canvas_height - self.notes_height,
        )

    @property
    def notes_rect(self) -> Rect:
        return Rect(
            self.left_column_width,
            self.canvas_height - self.notes_height,
            self.canvas_width - self.left_column_width,
            self.notes_height,
        )


DEFAULT_LAYOUT = LayoutSpec()
