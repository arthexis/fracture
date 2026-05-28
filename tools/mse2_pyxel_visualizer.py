"""Pyxel visualizer for Magic Set Editor 2 ``.mse-set`` card files.

The visualizer intentionally renders a compact, generic card approximation
instead of trying to execute MSE style scripts. It is meant for quick review of
MSE2-created cards inside this repo's tooling, with enough field handling to
cover Magic-style cards and other MSE games such as Wingspan.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


CARD_WIDTH = 228
CARD_HEIGHT = 320
SCREEN_WIDTH = 520
SCREEN_HEIGHT = 360
DEFAULT_DISPLAY_SCALE = 2

ART_X = 16
ART_Y = 42
ART_WIDTH = 196
ART_HEIGHT = 134
HEADER_X = 14
HEADER_Y = 15
HEADER_WIDTH = CARD_WIDTH - (HEADER_X * 2)
HEADER_HEIGHT = 22
TEXT_BOX_X = 14
TEXT_BOX_WIDTH = CARD_WIDTH - (TEXT_BOX_X * 2)
LINE_HEIGHT = 8
MANA_CHAR_WIDTH = 5

FIELD_NAME_RE = re.compile(r"^\t([A-Za-z0-9_ -]+):(.*)$")
TOP_LEVEL_FIELD_RE = re.compile(r"^([A-Za-z0-9_ -]+):(.*)$")
TAG_RE = re.compile(r"<[^>]+>")
SYM_RE = re.compile(r"<sym(?:-[^>]*)?>(.*?)</sym(?:-[^>]*)?>", re.IGNORECASE | re.DOTALL)
WORD_LIST_RE = re.compile(
    r"<word-list-[^>]+>(.*?)</word-list-[^>]+>", re.IGNORECASE | re.DOTALL
)
SPANISH_FALLBACK_TRANSLATION = str.maketrans(
    {
        "\u00e1": "a",
        "\u00e9": "e",
        "\u00ed": "i",
        "\u00f3": "o",
        "\u00fa": "u",
        "\u00c1": "A",
        "\u00c9": "E",
        "\u00cd": "I",
        "\u00d3": "O",
        "\u00da": "U",
        "\u00f1": "n",
        "\u00d1": "N",
        "\u00fc": "u",
        "\u00dc": "U",
        "\u00bf": "?",
        "\u00a1": "!",
    }
)
SPANISH_GLYPHS = {
    "\u00e1": ("a", "acute"),
    "\u00e9": ("e", "acute"),
    "\u00ed": ("i", "acute"),
    "\u00f3": ("o", "acute"),
    "\u00fa": ("u", "acute"),
    "\u00c1": ("A", "acute"),
    "\u00c9": ("E", "acute"),
    "\u00cd": ("I", "acute"),
    "\u00d3": ("O", "acute"),
    "\u00da": ("U", "acute"),
    "\u00f1": ("n", "tilde"),
    "\u00d1": ("N", "tilde"),
    "\u00fc": ("u", "diaeresis"),
    "\u00dc": ("U", "diaeresis"),
    "\u00bf": ("?", "inverted-question"),
    "\u00a1": ("!", "inverted-exclamation"),
}
BORDER_PERSONALITIES = {
    "white": {"base": 6, "colors": (7, 10, 6), "step": 17, "speed": 6, "pattern": "spark"},
    "blue": {"base": 12, "colors": (12, 5, 1), "step": 13, "speed": 5, "pattern": "wave"},
    "black": {"base": 0, "colors": (0, 13, 5), "step": 19, "speed": 8, "pattern": "shadow"},
    "red": {"base": 8, "colors": (8, 9, 10), "step": 11, "speed": 4, "pattern": "dash"},
    "green": {"base": 11, "colors": (11, 3, 10), "step": 15, "speed": 7, "pattern": "thorn"},
    "artifact": {"base": 13, "colors": (13, 6, 5), "step": 14, "speed": 9, "pattern": "grid"},
    "land": {"base": 4, "colors": (4, 10, 3), "step": 16, "speed": 10, "pattern": "grain"},
    "colorless": {"base": 13, "colors": (13, 6, 7), "step": 18, "speed": 10, "pattern": "grid"},
}


@dataclass(frozen=True)
class MSECard:
    """Parsed card fields relevant to the generic visualizer."""

    index: int
    name: str
    fields: dict[str, str]
    art_entry: str = ""

    @property
    def card_type(self) -> str:
        primary = self.fields.get("super_type", "")
        subtype = self.fields.get("sub_type", "")
        if primary and subtype:
            return f"{primary} - {subtype}"
        return primary or subtype or self.fields.get("sciencename", "")

    @property
    def rules(self) -> str:
        for key in ("rule_text", "rules_text", "text", "power", "ability", "abilities"):
            if self.fields.get(key):
                return self.fields[key]
        return ""

    @property
    def flavor(self) -> str:
        return self.fields.get("flavor_text", "") or self.fields.get("funfacts", "")

    @property
    def cost(self) -> str:
        return self.fields.get("casting_cost", "") or self.fields.get("foodcost", "")

    @property
    def footer_left(self) -> str:
        return self.fields.get("illustrator", "") or self.fields.get("nest", "")

    @property
    def footer_right(self) -> str:
        power = self.fields.get("power", "")
        toughness = self.fields.get("toughness", "")
        if toughness or _looks_like_stat(power):
            return f"{power}/{toughness}".strip("/")
        points = self.fields.get("points", "")
        wingspan = self.fields.get("wingspan", "")
        return " ".join(part for part in (points, wingspan) if part)


@dataclass
class MSESet:
    """Parsed MSE2 set plus access to embedded art assets."""

    path: Path
    title: str
    game: str
    stylesheet: str
    cards: list[MSECard]
    archive_entries: set[str]

    def open_asset(self, entry_name: str) -> bytes:
        """Return raw bytes for an embedded set asset."""

        if not entry_name:
            raise FileNotFoundError("empty asset name")
        if self.path.is_dir():
            return (self.path / entry_name).read_bytes()
        with zipfile.ZipFile(self.path) as archive:
            return archive.read(entry_name)


@dataclass(frozen=True)
class RichGlyph:
    """Single display glyph plus visual style."""

    text: str
    style: str = "normal"


def parse_mse_set(path: str | Path) -> MSESet:
    """Parse a zipped or extracted MSE2 set."""

    set_path = Path(path).expanduser()
    set_text, entries = _read_mse_set_text(set_path)
    lines = set_text.splitlines()
    metadata = _parse_top_level_metadata(lines)
    set_info = _parse_named_top_level_block(lines, "set_info")
    cards = _parse_cards(lines, entries)
    title = _clean_text(set_info.get("title", "")) or set_path.stem
    return MSESet(
        path=set_path,
        title=title,
        game=_clean_text(metadata.get("game", "")),
        stylesheet=_clean_text(metadata.get("stylesheet", "")),
        cards=cards,
        archive_entries=entries,
    )


def _read_mse_set_text(path: Path) -> tuple[str, set[str]]:
    if path.is_dir():
        set_file = path / "set"
        if not set_file.exists():
            raise FileNotFoundError(f"{path} does not contain an MSE2 'set' file")
        entries = {
            item.relative_to(path).as_posix()
            for item in path.rglob("*")
            if item.is_file()
        }
        return _decode_text(set_file.read_bytes()), entries

    if not path.exists():
        raise FileNotFoundError(path)
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if "set" not in names:
            raise FileNotFoundError(f"{path} does not contain an MSE2 'set' entry")
        return _decode_text(archive.read("set")), names


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _parse_top_level_metadata(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        if line.startswith("\t") or not line.strip():
            continue
        match = TOP_LEVEL_FIELD_RE.match(line)
        if not match:
            continue
        key = match.group(1).strip()
        if key in {"card", "styling", "set_info"}:
            continue
        fields[key] = _clean_text(match.group(2).strip())
    return fields


def _parse_named_top_level_block(lines: list[str], block_name: str) -> dict[str, str]:
    block: list[str] = []
    collecting = False
    marker = f"{block_name}:"
    for line in lines:
        if line == marker:
            collecting = True
            continue
        if collecting and line and not line.startswith("\t"):
            break
        if collecting:
            block.append(line)
    return _parse_card_block(block)


def _parse_cards(lines: list[str], entries: set[str]) -> list[MSECard]:
    cards: list[MSECard] = []
    block: list[str] = []
    collecting = False
    for line in lines:
        if line == "card:":
            if collecting:
                cards.append(_build_card(len(cards), block, entries))
                block = []
            collecting = True
            continue
        if collecting:
            block.append(line)
    if collecting:
        cards.append(_build_card(len(cards), block, entries))
    return cards


def _build_card(index: int, block: list[str], entries: set[str]) -> MSECard:
    fields = _parse_card_block(block)
    name = fields.get("name", "") or f"Card {index + 1}"
    art_entry = _resolve_art_entry(fields, entries)
    return MSECard(index=index, name=name, fields=fields, art_entry=art_entry)


def _parse_card_block(block: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    i = 0
    while i < len(block):
        line = block[i]
        match = FIELD_NAME_RE.match(line)
        if not match:
            i += 1
            continue
        key = match.group(1).strip()
        inline_value = match.group(2)
        if inline_value.startswith(" "):
            inline_value = inline_value[1:]
        i += 1
        if inline_value:
            fields[key] = _clean_text(inline_value)
            continue

        value_lines: list[str] = []
        while i < len(block):
            next_line = block[i]
            if FIELD_NAME_RE.match(next_line):
                break
            if next_line.startswith("\t\t"):
                value_lines.append(next_line[2:])
            elif next_line.startswith("\t"):
                value_lines.append(next_line[1:])
            else:
                value_lines.append(next_line)
            i += 1
        fields[key] = _clean_text("\n".join(value_lines))
    return fields


def _resolve_art_entry(fields: dict[str, str], entries: set[str]) -> str:
    for field_name in ("image", "art", "mainframe_image", "image_2"):
        value = fields.get(field_name, "").strip()
        if not value:
            continue
        for candidate in _asset_candidates(value):
            if candidate in entries:
                return candidate
    return ""


def _asset_candidates(value: str) -> Iterable[str]:
    cleaned = value.replace("\\", "/").strip()
    if not cleaned:
        return ()
    candidates = [cleaned]
    if not Path(cleaned).suffix:
        candidates.extend(f"{cleaned}{suffix}" for suffix in (".png", ".jpg", ".jpeg", ".webp"))
    return tuple(candidates)


def _clean_text(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = WORD_LIST_RE.sub(lambda match: match.group(1), text)
    text = SYM_RE.sub(lambda match: "{" + match.group(1).strip() + "}", text)
    text = TAG_RE.sub("", text)
    text = html.unescape(text)
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    lines = [" ".join(line.strip().split()) for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def _dump_json(mse_set: MSESet) -> str:
    payload = {
        "path": str(mse_set.path),
        "title": mse_set.title,
        "game": mse_set.game,
        "stylesheet": mse_set.stylesheet,
        "cards": [
            {
                "index": card.index,
                "name": card.name,
                "type": card.card_type,
                "cost": card.cost,
                "art": card.art_entry,
                "fields": card.fields,
            }
            for card in mse_set.cards
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def run_visualizer(
    mse_set: MSESet,
    start_index: int = 0,
    no_art: bool = False,
    display_scale: int = DEFAULT_DISPLAY_SCALE,
    save_dir: Path | None = None,
    image_scale: int = 1,
) -> None:
    """Launch the Pyxel app."""

    try:
        import pyxel
    except ImportError as exc:
        raise SystemExit(
            "Pyxel is required for the visualizer. Install it with "
            "`python -m pip install pyxel Pillow`."
        ) from exc

    app = MSE2PyxelApp(
        pyxel,
        mse_set,
        start_index=start_index,
        no_art=no_art,
        display_scale=display_scale,
        save_dir=save_dir,
        image_scale=image_scale,
    )
    app.run()


def render_card_images(
    mse_set: MSESet,
    *,
    start_index: int = 0,
    output_file: Path | None = None,
    output_dir: Path | None = None,
    no_art: bool = False,
    image_scale: int = 1,
) -> list[Path]:
    """Render card PNG exports with the same Pyxel drawing path as the viewer."""

    try:
        import pyxel
    except ImportError as exc:
        raise SystemExit(
            "Pyxel is required for image export. Install it with "
            "`python -m pip install pyxel Pillow`."
        ) from exc

    app = MSE2PyxelApp(
        pyxel,
        mse_set,
        start_index=start_index,
        no_art=no_art,
        headless=True,
        screen_width=CARD_WIDTH,
        screen_height=CARD_HEIGHT,
        card_origin=(0, 0),
        show_sidebar=False,
        image_scale=image_scale,
    )
    try:
        if output_dir is not None:
            paths: list[Path] = []
            for index, card in enumerate(mse_set.cards):
                app._set_index(index)
                path = _png_path(output_dir / _card_export_filename(card))
                app.export_current_card(path)
                paths.append(path)
            return paths
        path = _png_path(output_file or _default_export_path(mse_set, app.card))
        app.export_current_card(path)
        return [path]
    finally:
        app.close()


class MSE2PyxelApp:
    """Interactive Pyxel card viewer."""

    def __init__(
        self,
        pyxel_module,
        mse_set: MSESet,
        start_index: int = 0,
        no_art: bool = False,
        display_scale: int = DEFAULT_DISPLAY_SCALE,
        save_dir: Path | None = None,
        image_scale: int = 1,
        headless: bool = False,
        screen_width: int = SCREEN_WIDTH,
        screen_height: int = SCREEN_HEIGHT,
        card_origin: tuple[int, int] = (18, 16),
        show_sidebar: bool = True,
    ):
        self.pyxel = pyxel_module
        self.mse_set = mse_set
        self.card_index = max(0, min(start_index, len(mse_set.cards) - 1))
        self.no_art = no_art
        self.save_dir = save_dir
        self.image_scale = max(1, int(image_scale))
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.card_origin = card_origin
        self.show_sidebar = show_sidebar
        self.pending_export_path: Path | None = None
        self.export_message = ""
        self.export_message_until = 0
        self.temp_dir = tempfile.TemporaryDirectory(prefix="fracture-mse2-")
        self.loaded_art = ""
        self.art_size = (0, 0)
        self.art_warning = ""
        self.pyxel.init(
            screen_width,
            screen_height,
            title=f"MSE2 Visualizer - {mse_set.title}",
            fps=30,
            display_scale=max(1, int(display_scale)),
            headless=headless,
        )
        self.pyxel.mouse(True)
        self._load_current_art()

    def run(self) -> None:
        self.pyxel.run(self.update, self.draw)

    def close(self) -> None:
        self.temp_dir.cleanup()

    @property
    def card(self) -> MSECard:
        return self.mse_set.cards[self.card_index]

    def update(self) -> None:
        pyxel = self.pyxel
        if pyxel.btnp(pyxel.KEY_Q) or pyxel.btnp(pyxel.KEY_ESCAPE):
            self.close()
            pyxel.quit()
            return
        if pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D) or pyxel.btnp(pyxel.KEY_J):
            self._move(1)
        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A) or pyxel.btnp(pyxel.KEY_K):
            self._move(-1)
        if pyxel.btnp(pyxel.KEY_HOME):
            self._set_index(0)
        if pyxel.btnp(pyxel.KEY_END):
            self._set_index(len(self.mse_set.cards) - 1)
        if pyxel.btnp(pyxel.KEY_S):
            self.pending_export_path = _default_export_path(self.mse_set, self.card, self.save_dir)

    def draw(self) -> None:
        pyxel = self.pyxel
        pyxel.cls(1)
        self._draw_card(*self.card_origin)
        if self.show_sidebar:
            self._draw_sidebar(270, 16)
        if self.pending_export_path is not None:
            path = self.pending_export_path
            self.pending_export_path = None
            try:
                self._write_current_frame_card(path, self.image_scale)
                self.export_message = f"Saved {path.name}"
            except Exception as exc:  # noqa: BLE001 - keep GUI export errors visible
                self.export_message = f"Save failed: {exc}"
            self.export_message_until = pyxel.frame_count + 90

    def export_current_card(self, output_path: Path) -> None:
        self.pyxel.cls(1)
        self._draw_card(*self.card_origin)
        self._write_current_frame_card(output_path, self.image_scale)

    def _move(self, delta: int) -> None:
        if not self.mse_set.cards:
            return
        self._set_index((self.card_index + delta) % len(self.mse_set.cards))

    def _set_index(self, index: int) -> None:
        index = max(0, min(index, len(self.mse_set.cards) - 1))
        if index == self.card_index:
            return
        self.card_index = index
        self._load_current_art()

    def _draw_card(self, x: int, y: int) -> None:
        pyxel = self.pyxel
        card = self.card
        frame_color = _frame_color(card)
        pyxel.rect(x, y, CARD_WIDTH, CARD_HEIGHT, frame_color)
        self._draw_animated_border(x, y, card)
        pyxel.rect(x + 9, y + 9, CARD_WIDTH - 18, CARD_HEIGHT - 18, 7)
        pyxel.rectb(x + 9, y + 9, CARD_WIDTH - 18, CARD_HEIGHT - 18, 0)

        pyxel.rect(x + HEADER_X, y + HEADER_Y, HEADER_WIDTH, HEADER_HEIGHT, 6)
        pyxel.rectb(x + HEADER_X, y + HEADER_Y, HEADER_WIDTH, HEADER_HEIGHT, 0)
        cost_width = _mana_cost_width(card.cost)
        name_width = max(72, HEADER_WIDTH - 16 - cost_width)
        self._text(x + HEADER_X + 5, y + HEADER_Y + 8, self._fit_text(card.name, name_width), 0)
        self._draw_mana_cost(
            x + HEADER_X + HEADER_WIDTH - 5,
            y + HEADER_Y + 2,
            card.cost,
        )

        pyxel.rect(x + ART_X, y + ART_Y, ART_WIDTH, ART_HEIGHT, 13)
        pyxel.rectb(x + ART_X, y + ART_Y, ART_WIDTH, ART_HEIGHT, 0)
        self._draw_art(x + ART_X, y + ART_Y)

        type_y = y + ART_Y + ART_HEIGHT + 8
        pyxel.rect(x + TEXT_BOX_X, type_y, TEXT_BOX_WIDTH, 18, 6)
        pyxel.rectb(x + TEXT_BOX_X, type_y, TEXT_BOX_WIDTH, 18, 0)
        self._text(x + TEXT_BOX_X + 5, type_y + 6, self._fit_text(card.card_type, TEXT_BOX_WIDTH - 10), 0)

        rules_y = type_y + 24
        footer_y = y + CARD_HEIGHT - 18
        text_bottom = footer_y - 5
        if card.flavor:
            flavor_height = self._flavor_height(card.flavor, text_bottom - rules_y)
            rules_height = max(34, text_bottom - rules_y - flavor_height - 4)
            self._draw_text_panel(
                x + TEXT_BOX_X,
                rules_y,
                TEXT_BOX_WIDTH,
                rules_height,
                card.rules,
                background=7,
                text_color=0,
            )
            self._draw_text_panel(
                x + TEXT_BOX_X,
                rules_y + rules_height + 4,
                TEXT_BOX_WIDTH,
                flavor_height,
                card.flavor,
                background=7,
                text_color=5,
            )
        else:
            self._draw_text_panel(
                x + TEXT_BOX_X,
                rules_y,
                TEXT_BOX_WIDTH,
                text_bottom - rules_y,
                card.rules,
                background=7,
                text_color=0,
            )

        self._text(x + 16, footer_y, _fit(card.footer_left, 32), 5)
        right = _fit(card.footer_right, 14)
        self._text(x + CARD_WIDTH - 18 - self._text_width(right), footer_y, right, 5)

    def _draw_art(self, x: int, y: int) -> None:
        pyxel = self.pyxel
        if self.loaded_art:
            width, height = self.art_size
            pyxel.blt(x + 2, y + 2, 0, 0, 0, width, height)
            return
        message = self.art_warning or "No embedded art"
        self._wrapped_text(x + 8, y + 40, message, 38, 4, 6)

    def _draw_animated_border(self, x: int, y: int, card: MSECard) -> None:
        personalities = _border_personalities(card)
        for layer, personality in enumerate(personalities):
            phase = (self.pyxel.frame_count // personality["speed"] + layer * 3) % personality["step"]
            colors = personality["colors"]
            pattern = personality["pattern"]
            for pos in range(layer, CARD_WIDTH - layer, 2):
                if (pos + phase) % personality["step"] != 0:
                    continue
                color = colors[(pos // personality["step"] + phase + layer) % len(colors)]
                self._border_pixel(x + pos, y + layer, color, pattern, horizontal=True)
                self._border_pixel(
                    x + CARD_WIDTH - 1 - pos,
                    y + CARD_HEIGHT - 1 - layer,
                    color,
                    pattern,
                    horizontal=True,
                )
            for pos in range(layer, CARD_HEIGHT - layer, 2):
                if (pos + phase + personality["step"] // 2) % personality["step"] != 0:
                    continue
                color = colors[(pos // personality["step"] + phase + layer) % len(colors)]
                self._border_pixel(x + layer, y + pos, color, pattern, horizontal=False)
                self._border_pixel(
                    x + CARD_WIDTH - 1 - layer,
                    y + CARD_HEIGHT - 1 - pos,
                    color,
                    pattern,
                    horizontal=False,
                )

    def _border_pixel(self, x: int, y: int, color: int, pattern: str, *, horizontal: bool) -> None:
        pyxel = self.pyxel
        pyxel.pset(x, y, color)
        if pattern == "dash":
            pyxel.pset(x + (1 if horizontal else 0), y + (0 if horizontal else 1), color)
        elif pattern == "spark":
            pyxel.pset(x, y + (1 if horizontal else 0), color)
        elif pattern == "wave":
            pyxel.pset(x + (0 if horizontal else 1), y + (1 if horizontal else 0), color)
        elif pattern == "thorn":
            pyxel.pset(x + (1 if horizontal else 0), y + (1 if horizontal else 0), color)
        elif pattern == "grid":
            pyxel.pset(x + (1 if horizontal else 0), y + (0 if horizontal else 1), color)

    def _draw_sidebar(self, x: int, y: int) -> None:
        pyxel = self.pyxel
        pyxel.rect(x, y, self.screen_width - x - 14, self.screen_height - 32, 5)
        pyxel.rectb(x, y, self.screen_width - x - 14, self.screen_height - 32, 0)
        self._text(x + 8, y + 9, self.mse_set.title, 7)
        self._text(x + 8, y + 21, f"{self.mse_set.game or 'MSE2'} / {self.mse_set.stylesheet}", 6)
        self._text(x + 8, y + 37, f"Card {self.card_index + 1} of {len(self.mse_set.cards)}", 7)
        self._text(x + 8, y + 54, "Left/Right or A/D: card", 6)
        self._text(x + 8, y + 64, "Home/End: first/last", 6)
        self._text(x + 8, y + 74, "S: save PNG", 6)
        self._text(x + 8, y + 84, "Q/Esc: quit", 6)
        if self.export_message and self.pyxel.frame_count <= self.export_message_until:
            self._text(x + 8, y + 104, self._fit_text(self.export_message, self.screen_width - x - 28), 7)

        list_y = y + 124
        start = max(0, min(self.card_index - 8, max(0, len(self.mse_set.cards) - 16)))
        for offset, card in enumerate(self.mse_set.cards[start : start + 17]):
            row_y = list_y + offset * 12
            color = 7 if card.index == self.card_index else 6
            if card.index == self.card_index:
                pyxel.rect(x + 5, row_y - 2, self.screen_width - x - 24, 10, 1)
            self._text(
                x + 8,
                row_y,
                self._fit_text(f"{card.index + 1}. {card.name}", self.screen_width - x - 28),
                color,
            )

    def _write_current_frame_card(self, output_path: Path, scale: int) -> None:
        output_path = _png_path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        scale = max(1, int(scale))
        temp_path = Path(self.temp_dir.name) / "_frame.png"
        self.pyxel.screenshot(str(temp_path), scale=1)
        _crop_card_screenshot(temp_path, output_path, self.card_origin, scale)

    def _load_current_art(self) -> None:
        self.loaded_art = ""
        self.art_size = (0, 0)
        self.art_warning = ""
        if self.no_art or not self.card.art_entry:
            return
        try:
            asset = self.mse_set.open_asset(self.card.art_entry)
            art_path, size = _prepare_art_file(asset, self.card.art_entry, Path(self.temp_dir.name))
            self.pyxel.images[0].load(0, 0, str(art_path))
        except Exception as exc:  # noqa: BLE001 - show GUI-safe diagnostics
            self.art_warning = f"Could not load art: {exc}"
            return
        self.loaded_art = str(art_path)
        self.art_size = size

    def _text(self, x: int, y: int, text: str, color: int) -> None:
        cursor_x = x
        for char in str(text or ""):
            base, mark = _display_glyph(char)
            self.pyxel.text(cursor_x, y, base, color)
            if mark:
                self._draw_glyph_mark(cursor_x, y, mark, color)
            cursor_x += 4

    def _text_width(self, text: str) -> int:
        return len(str(text or "")) * 4

    def _fit_text(self, text: str, max_width: int) -> str:
        display_text = str(text or "")
        if self._text_width(display_text) <= max_width:
            return display_text
        suffix = "..."
        available = max_width - self._text_width(suffix)
        if available <= 0:
            return ""
        kept = ""
        for char in display_text:
            if self._text_width(kept + char) > available:
                break
            kept += char
        return kept.rstrip() + suffix

    def _draw_glyph_mark(self, x: int, y: int, mark: str, color: int) -> None:
        pyxel = self.pyxel
        mark_y = max(0, y - 2)
        if mark == "acute":
            pyxel.pset(x + 2, mark_y + 1, color)
            pyxel.pset(x + 3, mark_y, color)
        elif mark == "tilde":
            pyxel.pset(x + 1, mark_y + 1, color)
            pyxel.pset(x + 2, mark_y, color)
            pyxel.pset(x + 3, mark_y + 1, color)
        elif mark == "diaeresis":
            pyxel.pset(x + 1, mark_y + 1, color)
            pyxel.pset(x + 3, mark_y + 1, color)
        elif mark == "inverted-question":
            pyxel.pset(x + 1, y, color)
            pyxel.pset(x + 2, y, color)
        elif mark == "inverted-exclamation":
            pyxel.pset(x + 1, y, color)

    def _wrapped_text(self, x: int, y: int, text: str, width: int, max_lines: int, color: int) -> None:
        line_y = y
        for line in _wrap_text(text, width, max_lines):
            self._text(x, line_y, line, color)
            line_y += LINE_HEIGHT

    def _draw_text_panel(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        text: str,
        *,
        background: int,
        text_color: int,
    ) -> None:
        self.pyxel.rect(x, y, width, height, background)
        self.pyxel.rectb(x, y, width, height, 0)
        max_lines = max(1, (height - 8) // LINE_HEIGHT)
        self._rich_text(x + 5, y + 5, text, width - 10, max_lines, text_color)

    def _rich_text(
        self,
        x: int,
        y: int,
        text: str,
        max_width: int,
        max_lines: int,
        text_color: int,
    ) -> None:
        lines = self._wrap_rich_text(text, max_width, max_lines)
        for line_index, line in enumerate(lines):
            cursor_x = x
            cursor_y = y + line_index * LINE_HEIGHT
            for glyph in line:
                width = self._text_width(glyph.text) if glyph.text else 0
                if glyph.style == "bracket":
                    self.pyxel.rect(cursor_x - 1, cursor_y - 1, max(2, width + 2), LINE_HEIGHT, 0)
                    color = 7
                elif glyph.style == "paren":
                    color = 5
                else:
                    color = text_color
                if glyph.text != " ":
                    self._text(cursor_x, cursor_y, glyph.text, color)
                cursor_x += width

    def _wrap_rich_text(self, text: str, max_width: int, max_lines: int) -> list[list[RichGlyph]]:
        lines: list[list[RichGlyph]] = []
        for paragraph in text.split("\n"):
            line: list[RichGlyph] = []
            line_width = 0
            for unit in _rich_wrap_units(_rich_glyphs(paragraph)):
                if not line:
                    unit = _strip_leading_spaces(unit)
                if not unit:
                    continue
                width = self._rich_width(unit)
                if line and line_width + width > max_width:
                    lines.append(_trim_trailing_spaces(line))
                    if len(lines) >= max_lines:
                        return self._ellipsize_rich_lines(lines, max_width)
                    unit = _strip_leading_spaces(unit)
                    if not unit:
                        continue
                    line = list(unit)
                    line_width = self._rich_width(line)
                    continue
                line.extend(unit)
                line_width += width
            lines.append(_trim_trailing_spaces(line))
            if len(lines) >= max_lines:
                return self._ellipsize_rich_lines(lines, max_width)
        return lines[:max_lines]

    def _ellipsize_rich_lines(self, lines: list[list[RichGlyph]], max_width: int) -> list[list[RichGlyph]]:
        if not lines:
            return lines
        suffix = RichGlyph("...", "normal")
        suffix_width = self._text_width(suffix.text)
        line = _trim_trailing_spaces(lines[-1])
        while line and self._rich_width(line) + suffix_width > max_width:
            line = _drop_last_rich_word(line)
        if self._rich_width(line) + suffix_width <= max_width:
            line.append(suffix)
        elif suffix_width <= max_width:
            line = [suffix]
        lines[-1] = line
        return lines

    def _rich_width(self, glyphs: Iterable[RichGlyph]) -> int:
        return sum(self._text_width(glyph.text) for glyph in glyphs)

    def _draw_mana_cost(self, right_x: int, y: int, cost: str) -> None:
        tokens = _mana_cost_tokens(cost)
        if not tokens:
            return
        total_width = _mana_cost_width(cost)
        cursor = right_x - total_width
        for token in tokens:
            width = _mana_token_width(token)
            self._draw_mana_token(cursor, y, width, token)
            cursor += width + 2

    def _draw_mana_token(self, x: int, y: int, width: int, token: str) -> None:
        pyxel = self.pyxel
        if _is_fraction_token(token):
            top, bottom = token[0], token[1:]
            pyxel.rect(x, y, width, 18, _mana_color(top))
            pyxel.rectb(x, y, width, 18, 0)
            pyxel.line(x + 1, y + 9, x + width - 2, y + 9, 0)
            self._centered_mana_text(x, y + 2, width, top, _mana_text_color(top))
            self._centered_mana_text(x, y + 11, width, bottom, _mana_text_color(bottom))
            return
        pyxel.rect(x, y + 4, width, 12, _mana_color(token))
        pyxel.rectb(x, y + 4, width, 12, 0)
        self._centered_mana_text(x, y + 7, width, token, _mana_text_color(token))

    def _centered_text(self, x: int, y: int, width: int, text: str, color: int) -> None:
        self._text(x + max(1, (width - self._text_width(text)) // 2), y, text, color)

    def _centered_mana_text(self, x: int, y: int, width: int, text: str, color: int) -> None:
        self._mana_text(x + max(1, (width - _mana_text_width(text)) // 2), y, text, color)

    def _mana_text(self, x: int, y: int, text: str, color: int) -> None:
        cursor_x = x
        for char in str(text or ""):
            base, mark = _display_glyph(char)
            self.pyxel.text(cursor_x, y, base, color)
            self.pyxel.text(cursor_x + 1, y, base, color)
            if mark:
                self._draw_glyph_mark(cursor_x, y, mark, color)
            cursor_x += MANA_CHAR_WIDTH

    def _flavor_height(self, text: str, available_height: int) -> int:
        line_count = len(_wrap_text(text, (TEXT_BOX_WIDTH - 10) // 4, 8))
        preferred = min(42, max(22, line_count * 8 + 8))
        return max(18, min(preferred, available_height - 38))


def _prepare_art_file(data: bytes, entry_name: str, temp_dir: Path) -> tuple[Path, tuple[int, int]]:
    """Write an art image that Pyxel can load, resizing when Pillow is present."""

    suffix = Path(entry_name).suffix.lower() or _guess_image_suffix(data) or ".png"
    target = temp_dir / f"art{suffix}"
    try:
        from PIL import Image
    except ImportError:
        target.write_bytes(data)
        return target, (ART_WIDTH - 4, ART_HEIGHT - 4)

    source = temp_dir / f"source{suffix}"
    source.write_bytes(data)
    with Image.open(source) as image:
        image = image.convert("RGB")
        canvas_size = (ART_WIDTH - 4, ART_HEIGHT - 4)
        canvas = _cover_resize(image, canvas_size)
        target = temp_dir / "art.png"
        canvas.save(target)
        return target, canvas.size


def _cover_resize(image, size: tuple[int, int]):
    """Resize and center-crop an image to fill the target area."""

    from PIL import Image

    target_width, target_height = size
    target_ratio = target_width / target_height
    source_ratio = image.width / image.height
    if source_ratio > target_ratio:
        crop_width = int(image.height * target_ratio)
        left = (image.width - crop_width) // 2
        image = image.crop((left, 0, left + crop_width, image.height))
    elif source_ratio < target_ratio:
        crop_height = int(image.width / target_ratio)
        top = (image.height - crop_height) // 2
        image = image.crop((0, top, image.width, top + crop_height))
    return image.resize(size, Image.Resampling.LANCZOS)


def _crop_card_screenshot(
    source: Path,
    target: Path,
    card_origin: tuple[int, int],
    scale: int,
) -> None:
    from PIL import Image

    with Image.open(source) as image:
        x, y = card_origin
        card = image.crop((x, y, x + CARD_WIDTH, y + CARD_HEIGHT))
        if scale > 1:
            card = card.resize((CARD_WIDTH * scale, CARD_HEIGHT * scale), Image.Resampling.NEAREST)
        card.save(target)


def _guess_image_suffix(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return ""


def _default_export_path(mse_set: MSESet, card: MSECard, save_dir: Path | None = None) -> Path:
    directory = save_dir or (mse_set.path.parent / f"{mse_set.path.stem}-exports")
    return _png_path(directory / _card_export_filename(card))


def _card_export_filename(card: MSECard) -> str:
    return f"{card.index + 1:03d}-{_slug(card.name) or 'card'}.png"


def _png_path(path: Path) -> Path:
    path = Path(path).expanduser()
    if path.suffix:
        return path
    return path.with_suffix(".png")


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return slug[:64].strip("-")


def _frame_color(card: MSECard) -> int:
    return BORDER_PERSONALITIES[_border_personalities(card)[0]["key"]]["base"]


def _border_personalities(card: MSECard) -> list[dict[str, object]]:
    keys = _card_color_keys(card)
    if not keys:
        keys = ["colorless"]
    personalities = []
    for key in keys[:4]:
        personality = dict(BORDER_PERSONALITIES[key])
        personality["key"] = key
        personalities.append(personality)
    return personalities


def _card_color_keys(card: MSECard) -> list[str]:
    color_text = " ".join(
        (
            card.fields.get("card_color", ""),
            card.fields.get("border_color", ""),
            card.fields.get("habitat", ""),
        )
    ).lower()
    aliases = (
        ("white", ("white",)),
        ("blue", ("blue", "wetland")),
        ("black", ("black",)),
        ("red", ("red",)),
        ("green", ("green", "forest", "grassland")),
        ("artifact", ("artifact",)),
        ("land", ("land",)),
    )
    found: list[tuple[int, str]] = []
    for key, words in aliases:
        positions = [color_text.find(word) for word in words if color_text.find(word) >= 0]
        if positions:
            found.append((min(positions), key))
    return [key for _position, key in sorted(found)]


def _looks_like_stat(value: str) -> bool:
    return bool(re.fullmatch(r"[-+*?0-9Xx]+", value.strip()))


def _display_glyph(char: str) -> tuple[str, str]:
    glyph = SPANISH_GLYPHS.get(char)
    if glyph:
        return glyph
    return char.translate(SPANISH_FALLBACK_TRANSLATION), ""


def _rich_glyphs(text: str) -> list[RichGlyph]:
    glyphs: list[RichGlyph] = []
    bracket_depth = 0
    paren_depth = 0
    for char in str(text or ""):
        if char == "[":
            glyphs.append(RichGlyph(char, "bracket"))
            bracket_depth += 1
            continue
        if char == "]":
            glyphs.append(RichGlyph(char, "bracket"))
            bracket_depth = max(0, bracket_depth - 1)
            continue
        if bracket_depth:
            glyphs.append(RichGlyph(char, "bracket"))
            continue
        if char == "(":
            glyphs.append(RichGlyph(char, "paren"))
            paren_depth += 1
            continue
        if char == ")":
            glyphs.append(RichGlyph(char, "paren"))
            paren_depth = max(0, paren_depth - 1)
            continue
        glyphs.append(RichGlyph(char, "paren" if paren_depth else "normal"))
    return glyphs


def _rich_wrap_units(glyphs: Iterable[RichGlyph]) -> list[list[RichGlyph]]:
    units: list[list[RichGlyph]] = []
    pending_spaces: list[RichGlyph] = []
    pending_word: list[RichGlyph] = []

    for glyph in glyphs:
        if glyph.text.isspace():
            if pending_word:
                units.append(pending_spaces + pending_word)
                pending_spaces = []
                pending_word = []
            pending_spaces.append(glyph)
            continue
        pending_word.append(glyph)

    if pending_word:
        units.append(pending_spaces + pending_word)
    elif pending_spaces:
        units.append(pending_spaces)
    return units


def _strip_leading_spaces(glyphs: list[RichGlyph]) -> list[RichGlyph]:
    index = 0
    while index < len(glyphs) and glyphs[index].text.isspace():
        index += 1
    return glyphs[index:]


def _trim_trailing_spaces(glyphs: list[RichGlyph]) -> list[RichGlyph]:
    trimmed = list(glyphs)
    while trimmed and trimmed[-1].text.isspace():
        trimmed.pop()
    return trimmed


def _drop_last_rich_word(glyphs: list[RichGlyph]) -> list[RichGlyph]:
    trimmed = _trim_trailing_spaces(glyphs)
    index = len(trimmed)
    while index > 0 and not trimmed[index - 1].text.isspace():
        index -= 1
    while index > 0 and trimmed[index - 1].text.isspace():
        index -= 1
    return trimmed[:index]


def _mana_cost_tokens(cost: str) -> list[str]:
    cleaned = (
        str(cost or "")
        .replace("{", "")
        .replace("}", "")
        .replace("(", "")
        .replace(")", "")
        .strip()
    )
    if not cleaned:
        return []
    parts = re.split(r"[\s,+/]+", cleaned)
    return [part.strip() for part in parts if part.strip()]


def _mana_cost_width(cost: str) -> int:
    tokens = _mana_cost_tokens(cost)
    if not tokens:
        return 0
    return sum(_mana_token_width(token) for token in tokens) + (len(tokens) - 1) * 2


def _mana_token_width(token: str) -> int:
    if _is_fraction_token(token):
        return max(17, _mana_text_width(token[1:]) + 8)
    return max(13, _mana_text_width(token) + 8)


def _mana_text_width(text: str) -> int:
    return len(str(text or "")) * MANA_CHAR_WIDTH


def _is_fraction_token(token: str) -> bool:
    if not 2 <= len(token) <= 3 or token.isdigit():
        return False
    if len(set(token.upper())) == 1:
        return False
    return all(char.upper() in {"0", "1", "2", "X", "W", "U", "B", "R", "G", "C", "S"} for char in token)


def _mana_color(token: str) -> int:
    upper = token.upper()
    if "W" in upper:
        return 7
    if "U" in upper:
        return 12
    if "B" in upper:
        return 0
    if "R" in upper:
        return 8
    if "G" in upper:
        return 11
    if "C" in upper:
        return 13
    return 6


def _mana_text_color(token: str) -> int:
    return 7 if _mana_color(token) in {0, 8, 12, 13} else 0


def _wrap_text(text: str, width: int, max_lines: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if len(candidate) <= width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
                if len(lines) >= max_lines:
                    return _ellipsize_last(lines, width)
        if current:
            lines.append(current)
        if len(lines) >= max_lines:
            return _ellipsize_last(lines, width)
    return lines


def _ellipsize_last(lines: list[str], width: int) -> list[str]:
    if not lines:
        return lines
    if width <= 3:
        lines[-1] = "." * width
    else:
        available = width - 3
        line = lines[-1].rstrip()
        while len(line) > available:
            if " " not in line:
                line = ""
                break
            line = line.rsplit(" ", 1)[0].rstrip()
        lines[-1] = f"{line}..." if line else "..."
    return lines


def _fit(text: str, width: int) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) <= width:
        return normalized
    if width <= 3:
        return normalized[:width]
    return normalized[: width - 3].rstrip() + "..."


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("set_path", help="Path to a zipped or extracted .mse-set")
    parser.add_argument("--card", type=int, default=1, help="1-based card index to open")
    parser.add_argument("--list", action="store_true", help="List parsed cards and exit")
    parser.add_argument("--json", action="store_true", help="Dump parsed set JSON and exit")
    parser.add_argument("--no-art", action="store_true", help="Skip embedded art loading")
    parser.add_argument("--render", help="Render the selected --card to a PNG and exit")
    parser.add_argument("--render-all", help="Render every parsed card to PNGs in this directory and exit")
    parser.add_argument("--save-dir", help="Directory used by the interactive S hotkey")
    parser.add_argument("--image-scale", type=int, default=1, help="Integer scale for exported PNG images")
    parser.add_argument(
        "--display-scale",
        type=int,
        default=DEFAULT_DISPLAY_SCALE,
        help="Integer Pyxel window scale. Use 3 for a larger display.",
    )
    args = parser.parse_args(argv)
    if args.render and args.render_all:
        parser.error("--render and --render-all cannot be used together")

    try:
        mse_set = parse_mse_set(args.set_path)
    except Exception as exc:  # noqa: BLE001 - CLI reports parser failures
        print(f"Failed to parse MSE2 set: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(_dump_json(mse_set))
        return 0
    if args.list:
        print(f"{mse_set.title} ({mse_set.game or 'unknown game'}): {len(mse_set.cards)} card(s)")
        for card in mse_set.cards:
            art = f" art={card.art_entry}" if card.art_entry else ""
            print(f"{card.index + 1:03d}: {card.name}{art}")
        return 0
    if not mse_set.cards:
        print("No cards found in MSE2 set.", file=sys.stderr)
        return 1
    if args.render or args.render_all:
        paths = render_card_images(
            mse_set,
            start_index=max(0, args.card - 1),
            output_file=Path(args.render).expanduser() if args.render else None,
            output_dir=Path(args.render_all).expanduser() if args.render_all else None,
            no_art=args.no_art,
            image_scale=args.image_scale,
        )
        for path in paths:
            print(path)
        return 0

    run_visualizer(
        mse_set,
        start_index=max(0, args.card - 1),
        no_art=args.no_art,
        display_scale=args.display_scale,
        save_dir=Path(args.save_dir).expanduser() if args.save_dir else None,
        image_scale=args.image_scale,
    )
    return 0


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
