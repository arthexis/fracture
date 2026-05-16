"""
Hidden per-account poker decks.

Deck state is stored as an Evennia Account Attribute so game systems can draw
cards without exposing deck order to ordinary players.
"""

from __future__ import annotations

from datetime import UTC, datetime
from random import SystemRandom
from typing import Any


DECK_ATTRIBUTE = "poker_deck"
DECK_VERSION = 1
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
SUITS = ("S", "H", "D", "C")
JOKERS = ("JokerA", "JokerB", "JokerC")
FULL_DECK = tuple(f"{rank}{suit}" for suit in SUITS for rank in RANKS) + JOKERS

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
        "draw_count": 0,
        "shuffle_count": 1,
        "created_at": now,
        "shuffled_at": now,
    }


def _state_is_usable(state: object) -> bool:
    return (
        isinstance(state, dict)
        and isinstance(state.get("deck"), list)
        and isinstance(state.get("discard"), list)
    )


def _save_state(account, state: dict[str, Any]) -> dict[str, Any]:
    setattr(account.db, DECK_ATTRIBUTE, state)
    return state


def get_or_create_deck(account) -> dict[str, Any]:
    """Return an account's deck state, creating one if missing or unusable."""

    state = getattr(account.db, DECK_ATTRIBUTE, None)
    if not _state_is_usable(state):
        return _save_state(account, new_deck_state())

    state.setdefault("version", DECK_VERSION)
    state.setdefault("discard", [])
    state.setdefault("draw_count", 0)
    state.setdefault("shuffle_count", 1)
    created_at = state.setdefault("created_at", _timestamp())
    state.setdefault("shuffled_at", created_at)

    if "JokerC" not in state["deck"] and "JokerC" not in state["discard"]:
        state["deck"].append("JokerC")
        _shuffled(state["deck"])
        state["shuffled_at"] = _timestamp()

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


def remaining_count(account) -> int:
    """Return the number of cards left before the next reshuffle."""

    return len(get_or_create_deck(account)["deck"])


def discard_count(account) -> int:
    """Return the number of drawn cards waiting in discard."""

    return len(get_or_create_deck(account)["discard"])
