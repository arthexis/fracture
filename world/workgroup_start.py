"""World setup for The Workgroup starting area."""

from __future__ import annotations

import random

from evennia.utils import create, logger
from evennia.utils.search import search_object

WAITING_ROOM = "The Waiting Room"
EXAM_ROOM = "Examination Room A"
DESERT_STOP = "A Solitary Bus Stop"
INTERCAL = "Intercal"

ROOM_TYPECLASS = "typeclasses.rooms.Room"
DESERT_TYPECLASS = "typeclasses.rooms.DesertDeathRoom"
EXIT_TYPECLASS = "typeclasses.exits.Exit"
CHARACTER_TYPECLASS = "typeclasses.characters.Character"

WAITING_ROOM_DESC = """
The Waiting Room looks like it belongs equally to a clinic and to a
bureaucratic office that has forgotten which counter handles which form.
Fluorescent panels buzz overhead. The air conditioning is too cold, too
steady, and almost musical if you let your eyes close for a moment.

A small area of plastic chairs and tired couches faces a low table stacked
with old magazines and blank intake forms. One door is labeled Examination
Room A. Another points Out to the Desert.
""".strip()

EXAM_ROOM_DESC = """
Examination Room A is clean, narrow, and unused. A paper-covered examination
table waits under a careful white light. The cabinets are closed. The sink is
dry. Whatever this room is meant to become, it has not started yet.
""".strip()

DESERT_STOP_DESC = """
A solitary bus stop stands outside the building in the middle of the desert.
The sign is sun-faded, the schedule is blank, and the road runs straight until
heat shimmer edits it out of view.
""".strip()

INTERCAL_DESC = """
Intercal occupies a teal service chassis built around a squared television
head. The body is broad-shouldered and industrial, softened by a deliberately
fake nurse costume: a crisp white apron-dress, bright red trim, and a cap that
sits at an angle no hospital would authorize.

The TV face can display text in friendly phosphor-green letters, but Intercal
can also speak through a warm robotic voice from a grille beneath the screen.
Both modes seem prepared to be helpful, apologetic, and a little too calm for
the room.
""".strip()

DESERT_DEATH_MESSAGES = (
    "The bus schedule unfolds from the heat shimmer and stamps your name FINAL.",
    "A clipboard drops out of the white sky, already signed, and files you under done.",
    "The sun catches you in a perfect administrative spotlight and audits you out of the scene.",
    "A vending machine flickers, dispenses a paper cup of night, and everything goes quiet.",
    "A clerk behind the horizon calls your number; the desert answers for you.",
)


def _first_exact(key: str):
    matches = search_object(key, exact=True)
    return matches[0] if matches else None


def _ensure_aliases(obj, aliases: tuple[str, ...]) -> None:
    if aliases:
        obj.aliases.add(list(aliases))


def _ensure_room(key: str, description: str, typeclass: str = ROOM_TYPECLASS):
    room = _first_exact(key)
    if room is None:
        room = create.create_object(typeclass, key=key)
    if room.typeclass_path != typeclass:
        room.swap_typeclass(typeclass, clean_attributes=False)
    room.db.desc = description
    room.tags.add("workgroup_start", category="world")
    return room


def _ensure_exit(location, key: str, destination, aliases: tuple[str, ...] = ()):
    for obj in location.contents:
        if obj.key.lower() == key.lower() and obj.destination:
            exit_obj = obj
            break
    else:
        exit_obj = create.create_object(
            EXIT_TYPECLASS,
            key=key,
            location=location,
            destination=destination,
            aliases=list(aliases),
        )
    exit_obj.destination = destination
    _ensure_aliases(exit_obj, aliases)
    exit_obj.tags.add("workgroup_start", category="world")
    return exit_obj


def ensure_intercal_body(waiting_room=None):
    waiting_room = waiting_room or ensure_workgroup_world(create_intercal=False)[0]
    intercal = _first_exact(INTERCAL)
    if intercal is None:
        intercal = create.create_object(CHARACTER_TYPECLASS, key=INTERCAL)
    intercal.db.desc = INTERCAL_DESC
    intercal.home = waiting_room
    _ensure_aliases(intercal, ("teal robot", "tv robot", "nurse robot"))
    intercal.tags.add("workgroup_start", category="world")
    if intercal.location is None or getattr(intercal.location, "key", "") == "Limbo":
        intercal.move_to(waiting_room, quiet=True, move_type="wake")
    return intercal


def ensure_character_home(character) -> None:
    waiting_room, _exam_room, _desert_stop = ensure_workgroup_world(create_intercal=False)
    if character.home != waiting_room:
        character.home = waiting_room


def wake_if_unplaced(character) -> None:
    waiting_room, _exam_room, _desert_stop = ensure_workgroup_world(create_intercal=False)
    if character.home != waiting_room:
        character.home = waiting_room
    if character.location is None or getattr(character.location, "key", "") == "Limbo":
        character.move_to(waiting_room, quiet=True, move_type="wake")
        character.msg(
            "The air conditioning hums you half asleep. You wake again in "
            "The Waiting Room."
        )


def kill_in_desert(character, death_room) -> None:
    waiting_room, _exam_room, _desert_stop = ensure_workgroup_world(create_intercal=False)
    death = random.choice(DESERT_DEATH_MESSAGES)
    character.msg(f"{death} You die.")
    death_room.msg_contents(
        f"{character.key} vanishes in a hard blink of desert light.",
        exclude=character,
    )
    character.move_to(waiting_room, quiet=True, move_type="death")
    character.msg(
        "The air conditioning lulls you half asleep. You wake again in "
        "The Waiting Room."
    )
    waiting_room.msg_contents(
        f"{character.key} wakes under the air conditioning.",
        exclude=character,
    )


def ensure_workgroup_world(*, create_intercal: bool = True):
    """Create or repair The Workgroup starting rooms and Intercal body."""

    waiting_room = _ensure_room(WAITING_ROOM, WAITING_ROOM_DESC)
    exam_room = _ensure_room(EXAM_ROOM, EXAM_ROOM_DESC)
    desert_stop = _ensure_room(DESERT_STOP, DESERT_STOP_DESC, DESERT_TYPECLASS)

    _ensure_exit(
        waiting_room,
        EXAM_ROOM,
        exam_room,
        aliases=("exam", "examination", "room a", "a"),
    )
    _ensure_exit(exam_room, WAITING_ROOM, waiting_room, aliases=("waiting", "back"))
    _ensure_exit(
        waiting_room,
        "Out to the Desert",
        desert_stop,
        aliases=("out", "desert", "bus stop"),
    )
    _ensure_exit(desert_stop, "Back Inside", waiting_room, aliases=("inside", "back"))

    if create_intercal:
        ensure_intercal_body(waiting_room)

    return waiting_room, exam_room, desert_stop


def ensure_workgroup_world_safe() -> None:
    try:
        ensure_workgroup_world()
    except Exception:
        logger.log_trace()
