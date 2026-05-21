"""
Hidden per-account poker decks.

Deck state is stored as an Evennia Account Attribute so game systems can draw
cards without exposing deck order to ordinary players.
"""

from __future__ import annotations

import copy
from collections.abc import MutableMapping, MutableSequence
from datetime import UTC, datetime
from random import SystemRandom
from typing import Any


DECK_ATTRIBUTE = "poker_deck"
DECK_VERSION = 3
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
SUITS = ("D", "V", "M", "S")
JOKERS = ("JokerA", "JokerB", "JokerC")
FULL_DECK = tuple(f"{rank}{suit}" for suit in SUITS for rank in RANKS) + JOKERS
CARD_VALUES = {
    "A": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
    "JokerA": 15,
    "JokerB": 15,
    "JokerC": 15,
}
LEGACY_SUIT_MIGRATION = {
    "S": "D",  # Spades -> Daggers
    "C": "S",  # Clubs -> Spindles
    "H": "V",  # Hearts -> Vessels
    "D": "M",  # Diamonds -> Masques
}
JOKER_DISPLAY = {
    "JokerA": "XX",
    "JokerB": "XY",
    "JokerC": "YY",
}

_RANDOM = SystemRandom()


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _shuffled(cards: list[str]) -> list[str]:
    _RANDOM.shuffle(cards)
    return cards


def new_deck_state() -> dict[str, Any]:
    """Return a fresh shuffled 55-card deck state."""

    now = _timestamp()
    return {
        "version": DECK_VERSION,
        "deck": _shuffled(list(FULL_DECK)),
        "discard": [],
        "burned": [],
        "draw_count": 0,
        "burn_count": 0,
        "desert_shield_minutes": 0,
        "shuffle_count": 1,
        "created_at": now,
        "shuffled_at": now,
    }


def _state_is_usable(state: object) -> bool:
    return (
        isinstance(state, MutableMapping)
        and isinstance(state.get("deck"), MutableSequence)
        and isinstance(state.get("discard"), MutableSequence)
    )


def _save_state(account, state: dict[str, Any]) -> dict[str, Any]:
    saved_state = copy.deepcopy(state)
    setattr(account.db, DECK_ATTRIBUTE, saved_state)
    return saved_state


def _state_version(state: dict[str, Any]) -> int:
    try:
        return int(state.get("version", 1))
    except (TypeError, ValueError):
        return 1


def _migrate_legacy_card(card: str) -> str:
    if card in JOKERS or not card:
        return card
    rank, suit = card[:-1], card[-1]
    if rank in RANKS and suit in LEGACY_SUIT_MIGRATION:
        return f"{rank}{LEGACY_SUIT_MIGRATION[suit]}"
    return card


def _migrate_legacy_cards(cards: list[str]) -> list[str]:
    return [_migrate_legacy_card(card) for card in cards]


def get_or_create_deck(account) -> dict[str, Any]:
    """Return an account's deck state, creating one if missing or unusable."""

    state = getattr(account.db, DECK_ATTRIBUTE, None)
    if not _state_is_usable(state):
        return _save_state(account, new_deck_state())

    current_version = _state_version(state)
    state.setdefault("discard", [])
    state.setdefault("burned", [])
    state.setdefault("draw_count", 0)
    state.setdefault("burn_count", 0)
    state.setdefault("desert_shield_minutes", 0)
    state.setdefault("shuffle_count", 1)
    created_at = state.setdefault("created_at", _timestamp())
    state.setdefault("shuffled_at", created_at)

    if current_version < 2:
        state["deck"] = _migrate_legacy_cards(state["deck"])
        state["discard"] = _migrate_legacy_cards(state["discard"])
        state["version"] = DECK_VERSION

    if current_version < 3:
        state["burned"] = _migrate_legacy_cards(state["burned"])
        state["version"] = DECK_VERSION

    if (
        "JokerC" not in state["deck"]
        and "JokerC" not in state["discard"]
        and "JokerC" not in state["burned"]
    ):
        state["deck"].append("JokerC")
        _shuffled(state["deck"])
        state["shuffled_at"] = _timestamp()

    state["version"] = DECK_VERSION
    return _save_state(account, state)


def reset_deck(account) -> dict[str, Any]:
    """Replace an account's deck with a fresh shuffled 55-card deck."""

    return _save_state(account, new_deck_state())


def _reshuffle_discard_into_deck(state: dict[str, Any]) -> None:
    discard = state.get("discard", [])
    if not discard:
        return
    state["deck"] = _shuffled(list(discard))
    state["discard"] = []
    state["shuffle_count"] = int(state.get("shuffle_count", 0)) + 1
    state["shuffled_at"] = _timestamp()


def draw_cards(account, count: int = 1) -> list[str]:
    """Draw cards from an account deck and move them to discard."""

    if count < 1:
        raise ValueError("count must be at least 1")

    state = get_or_create_deck(account)
    drawn: list[str] = []
    for _ in range(count):
        if not state["deck"]:
            _reshuffle_discard_into_deck(state)
        if not state["deck"]:
            break
        card = state["deck"].pop()
        drawn.append(card)
        state["discard"].append(card)

    state["draw_count"] = int(state.get("draw_count", 0)) + len(drawn)
    _save_state(account, state)
    return drawn


def card_value(card: str | None) -> int:
    """Return the desert-shield minute value for a card."""

    if not card:
        return 0
    if card in JOKERS:
        return CARD_VALUES[card]
    return CARD_VALUES.get(card[:-1], 0)


def apply_desert_sun_minute(account) -> dict[str, Any]:
    """
    Resolve one minute of desert sun exposure.

    If the account has shield minutes, one minute is consumed. Otherwise a
    random card is burned from the live deck into the persistent burned pile.
    Discarded cards are not reshuffled into the deck for desert exposure.
    """

    state = get_or_create_deck(account)
    shield_minutes = max(0, int(state.get("desert_shield_minutes", 0)))
    if shield_minutes:
        state["desert_shield_minutes"] = shield_minutes - 1
        _save_state(account, state)
        return {
            "action": "shield",
            "shield_minutes": state["desert_shield_minutes"],
            "dead": False,
        }

    deck = state["deck"]
    if not deck:
        return {
            "action": "dead",
            "card": None,
            "value": 0,
            "remaining": 0,
            "shield_minutes": 0,
            "dead": True,
        }

    card = deck.pop(_RANDOM.randrange(len(deck)))
    value = card_value(card)
    state["burned"].append(card)
    state["burn_count"] = int(state.get("burn_count", 0)) + 1
    state["desert_shield_minutes"] = shield_minutes + value
    state["last_burned_at"] = _timestamp()
    dead = not deck
    _save_state(account, state)
    return {
        "action": "burn_dead" if dead else "burn",
        "card": card,
        "value": value,
        "remaining": len(deck),
        "shield_minutes": state["desert_shield_minutes"],
        "dead": dead,
    }


def peek_top_bottom(account) -> tuple[str | None, str | None]:
    """Return the next card to draw and bottom card without changing state."""

    deck = get_or_create_deck(account)["deck"]
    if not deck:
        return None, None
    return deck[-1], deck[0]


def format_card(card: str | None) -> str:
    """Return a compact ASCII card display code."""

    if not card:
        return "--"
    return JOKER_DISPLAY.get(card, card)


def format_top_bottom(account) -> str | None:
    """Return a [top/bottom]-ready card pair for an account deck."""

    top, bottom = peek_top_bottom(account)
    if top is None:
        return None
    return f"{format_card(top)}/{format_card(bottom)}"


def remaining_count(account) -> int:
    """Return the number of cards left before the next reshuffle."""

    return len(get_or_create_deck(account)["deck"])


def discard_count(account) -> int:
    """Return the number of drawn cards waiting in discard."""

    return len(get_or_create_deck(account)["discard"])


def burned_count(account) -> int:
    """Return the number of permanently sun-burned cards."""

    return len(get_or_create_deck(account)["burned"])
