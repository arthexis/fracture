"""
Secret character traits.

Secret traits are stored on Characters, not Accounts. They are intended for
server-side mechanics and Developer tooling, not ordinary player inspection.
"""

from __future__ import annotations


SECRET_TRAITS_ATTRIBUTE = "secret_traits"
TRUE_SIGHT = "True Sight"

_KNOWN_TRAITS = {TRUE_SIGHT.lower(): TRUE_SIGHT}
_DEFAULT_TRAITS_BY_CHARACTER = {
    "arthexis": (TRUE_SIGHT,),
}


def normalize_trait_name(trait: object) -> str:
    """Return a canonical trait name."""

    name = str(trait or "").strip()
    return _KNOWN_TRAITS.get(name.lower(), name)


def _stored_traits(character) -> list[str]:
    traits = getattr(character.db, SECRET_TRAITS_ATTRIBUTE, None)
    if not isinstance(traits, (list, tuple, set)):
        return []

    normalized: list[str] = []
    seen = set()
    for trait in traits:
        trait_name = normalize_trait_name(trait)
        trait_key = trait_name.lower()
        if trait_name and trait_key not in seen:
            normalized.append(trait_name)
            seen.add(trait_key)
    return normalized


def set_secret_traits(character, traits) -> list[str]:
    """Replace a character's secret traits with canonical, de-duplicated names."""

    normalized: list[str] = []
    seen = set()
    for trait in traits:
        trait_name = normalize_trait_name(trait)
        trait_key = trait_name.lower()
        if trait_name and trait_key not in seen:
            normalized.append(trait_name)
            seen.add(trait_key)
    setattr(character.db, SECRET_TRAITS_ATTRIBUTE, normalized)
    return normalized


def get_secret_traits(character) -> tuple[str, ...]:
    """Return a character's persisted secret traits."""

    return tuple(_stored_traits(character))


def default_traits_for(character) -> tuple[str, ...]:
    """Return default secret traits for a character."""

    key = str(getattr(character, "key", "") or "").strip().lower()
    return tuple(_DEFAULT_TRAITS_BY_CHARACTER.get(key, ()))


def ensure_default_traits(character) -> tuple[str, ...]:
    """Persist any default secret traits missing from a character."""

    current = list(_stored_traits(character))
    seen = {trait.lower() for trait in current}
    changed = False
    for trait in default_traits_for(character):
        trait_name = normalize_trait_name(trait)
        if trait_name.lower() not in seen:
            current.append(trait_name)
            seen.add(trait_name.lower())
            changed = True
    return tuple(set_secret_traits(character, current) if changed else current)


def add_secret_trait(character, trait: object) -> bool:
    """Add a secret trait. Return True if it changed the character."""

    current = list(_stored_traits(character))
    trait_name = normalize_trait_name(trait)
    if not trait_name:
        return False
    if trait_name.lower() in {existing.lower() for existing in current}:
        return False
    current.append(trait_name)
    set_secret_traits(character, current)
    return True


def remove_secret_trait(character, trait: object) -> bool:
    """Remove a secret trait. Return True if it changed the character."""

    trait_name = normalize_trait_name(trait)
    current = _stored_traits(character)
    filtered = [existing for existing in current if existing.lower() != trait_name.lower()]
    if len(filtered) == len(current):
        return False
    set_secret_traits(character, filtered)
    return True


def has_secret_trait(character, trait: object) -> bool:
    """Return True if a character has a secret trait."""

    if not character:
        return False
    ensure_default_traits(character)
    trait_name = normalize_trait_name(trait)
    return trait_name.lower() in {existing.lower() for existing in _stored_traits(character)}
