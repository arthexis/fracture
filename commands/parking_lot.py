"""Player interactions for the parking lot, service van, and charge point."""

from __future__ import annotations

from collections.abc import MutableMapping

from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils.search import search_object

from world.workgroup_start import PARKING_LOT, WAITING_ROOM


CHARGE_STATE_ATTRIBUTE = "parking_lot_charge_session"


def _in_parking_lot(caller) -> bool:
    return getattr(getattr(caller, "location", None), "key", "") == PARKING_LOT


def _charge_state(caller) -> dict[str, bool]:
    state = getattr(caller.db, CHARGE_STATE_ATTRIBUTE, None)
    if not isinstance(state, MutableMapping):
        state = {}
    state.setdefault("near_cover_checked", False)
    state.setdefault("far_cover_checked", False)
    state.setdefault("cable_taken", False)
    state.setdefault("plugged", False)
    return state


def _save_charge_state(caller, state: dict[str, bool]) -> None:
    setattr(caller.db, CHARGE_STATE_ATTRIBUTE, dict(state))


def _clear_charge_state(caller) -> None:
    caller.attributes.remove(CHARGE_STATE_ATTRIBUTE)


def _waiting_room():
    matches = search_object(WAITING_ROOM, exact=True)
    return matches[0] if matches else None


class CmdVan(MuxCommand):
    """
    Inspect or drive the service van.

    Usage:
      van
      drive van
    """

    key = "van"
    aliases = ("service van", "vehicle", "keys", "ignition", "drive")
    help_category = "General"

    def func(self):
        if not _in_parking_lot(self.caller):
            self.msg("There is no service van here.")
            return

        text = f"{self.cmdstring} {self.args}".casefold()
        if "drive" in text or "start" in text:
            self._drive()
            return

        self.msg(
            "\n".join(
                (
                    "The van is unlocked, dusty, and waiting too politely.",
                    "The keys are inside, fused into the ignition by melted plastic.",
                    "The instrument cluster wakes on reserve power: BATTERY 1%.",
                    "Two charging covers break the bodywork. The closer one is not the",
                    "right inlet for the charger cable; the matching inlet is on the",
                    "far side of the van.",
                )
            )
        )

    def _drive(self):
        caller = self.caller
        location = caller.location
        _clear_charge_state(caller)
        caller.msg(
            "\n".join(
                (
                    "You twist the fused keys. The van accepts this as consent.",
                    "The drive motor catches with a dry electrical whine, and the",
                    "service van lurches out of the parking lot toward the open sand.",
                    "",
                    "The sandstorm arrives as a wall. The battery indicator blinks 1%,",
                    "0%, then nothing. The motor dies.",
                    "",
                    "For one clean second, gravity forgets you. The steering wheel floats",
                    "out of your hands. Sand hangs in the air like a paused signal.",
                )
            )
        )
        location.msg_contents(
            f"{caller.key} starts the service van and drives into the sandstorm.",
            exclude=caller,
        )
        waiting_room = _waiting_room()
        if not waiting_room:
            caller.msg("The reset has nowhere to put you.")
            return
        caller.move_to(waiting_room, quiet=True, move_type="reset")
        caller.msg(
            "The air conditioning hums you half asleep. You wake again in "
            "The Waiting Room."
        )
        waiting_room.msg_contents(
            f"{caller.key} wakes under the air conditioning.",
            exclude=caller,
        )


class CmdChargePoint(MuxCommand):
    """
    Work with the parking lot charge point.

    Usage:
      charger
      charge cover
      charge cable
      charge plug near
      charge plug far
      scan card
      charge unplug
    """

    key = "charger"
    aliases = (
        "charge",
        "charge point",
        "station",
        "evse",
        "cable",
        "plug",
        "scan",
        "rfid",
    )
    help_category = "General"

    def func(self):
        if not _in_parking_lot(self.caller):
            self.msg("There is no charger here.")
            return

        text = f"{self.cmdstring} {self.args}".casefold().strip()
        if any(word in text for word in ("scan", "rfid", "card")):
            self._scan()
        elif "unplug" in text or "disconnect" in text:
            self._unplug()
        elif "plug" in text or "connect" in text:
            self._plug(text)
        elif any(word in text for word in ("cable", "lead", "cord", "take")):
            self._take_cable()
        elif any(word in text for word in ("cover", "port", "inlet", "flap", "socket")):
            self._locate_cover(text)
        else:
            self._status()

    def _status(self):
        state = _charge_state(self.caller)
        if state["plugged"]:
            self.msg(
                "The charger display reads VEHICLE CONNECTED. AUTHORIZATION REQUIRED. "
                "The contactor is open, the cable is latched, and the van still reports 1%."
            )
            return
        self.msg(
            "The charge point display cycles AVAILABLE, PRESENT CARD, 0.00 kW. "
            "The tethered cable is holstered beside the card reader."
        )

    def _locate_cover(self, text: str):
        state = _charge_state(self.caller)
        if any(word in text for word in ("far", "other", "passenger", "right", "opposite")):
            state["far_cover_checked"] = True
            _save_charge_state(self.caller, state)
            self.msg(
                "On the far side of the van, a second flap clicks open. This inlet matches "
                "the heavy charger plug: two large DC pins below the smaller signal pins."
            )
            return

        state["near_cover_checked"] = True
        _save_charge_state(self.caller, state)
        self.msg(
            "The closer charging cover opens with a dusty snap, but the inlet is wrong: "
            "a smaller AC socket, not the DC fast-charge connector on the cable. The "
            "body seam on the far side suggests another cover."
        )

    def _take_cable(self):
        state = _charge_state(self.caller)
        if state["cable_taken"]:
            self.msg("You already have the heavy charger cable in hand.")
            return
        state["cable_taken"] = True
        _save_charge_state(self.caller, state)
        self.msg(
            "You lift the tethered cable out of its holster. The connector is heavy, "
            "scratched, and shaped for the van's DC inlet."
        )

    def _plug(self, text: str):
        state = _charge_state(self.caller)
        if not state["cable_taken"]:
            self.msg("The cable is still in its holster. You need to take it first.")
            return
        if any(word in text for word in ("near", "close", "nearest", "wrong", "left")):
            state["near_cover_checked"] = True
            _save_charge_state(self.caller, state)
            self.msg(
                "The connector will not seat in the closer inlet. The pilot pins do not "
                "line up, and forcing it would only scar the socket."
            )
            return
        if not any(word in text for word in ("far", "other", "passenger", "right", "opposite")):
            self.msg(
                "The closer inlet is wrong for this connector. The matching charge cover "
                "is on the other side of the van."
            )
            return
        state["far_cover_checked"] = True
        state["plugged"] = True
        _save_charge_state(self.caller, state)
        self.msg(
            "You carry the cable around the van and press it into the far-side inlet. "
            "The latch clicks. The charger display changes to VEHICLE CONNECTED, "
            "then AUTHORIZATION REQUIRED."
        )

    def _scan(self):
        state = _charge_state(self.caller)
        if not state["plugged"]:
            self.msg(
                "The reader wakes, but the display asks for a vehicle connection before "
                "authorization."
            )
            return
        self.msg(
            "You check your pockets and come up with no charge card. The reader waits "
            "for RFID authorization, the contactor stays open, and the van remains at 1%."
        )

    def _unplug(self):
        state = _charge_state(self.caller)
        if not state["plugged"] and not state["cable_taken"]:
            self.msg("The cable is already holstered.")
            return
        _clear_charge_state(self.caller)
        self.msg(
            "You release the latch, return the cable to its holster, and the charger "
            "falls back to AVAILABLE."
        )
