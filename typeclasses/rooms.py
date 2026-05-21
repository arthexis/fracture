"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """

    pass



class DesertDeathRoom(Room):
    """A desert threshold that burns cards before returning characters home."""

    exposure_script = "typeclasses.scripts.DesertSunExposureScript"
    exposure_key = "desert_sun_exposure"

    def at_object_receive(self, obj, source_location, **kwargs):
        super().at_object_receive(obj, source_location, **kwargs)
        if not obj.is_typeclass("typeclasses.characters.Character", exact=False):
            return

        if not obj.scripts.has(self.exposure_key):
            obj.scripts.add(self.exposure_script, key=self.exposure_key)
        else:
            obj.scripts.start(self.exposure_key)
        obj.msg("The desert sun settles on you like a verdict.")

    def at_object_leave(self, obj, target_location, move_type="move", **kwargs):
        super().at_object_leave(obj, target_location, move_type=move_type, **kwargs)
        if not obj.is_typeclass("typeclasses.characters.Character", exact=False):
            return

        try:
            obj.scripts.stop(self.exposure_key)
        except Exception:
            pass
