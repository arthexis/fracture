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
    """A desert threshold that returns characters to The Waiting Room."""

    def at_object_receive(self, obj, source_location, **kwargs):
        super().at_object_receive(obj, source_location, **kwargs)
        if getattr(obj.ndb, "desert_death_in_progress", False):
            return
        if not obj.is_typeclass("typeclasses.characters.Character", exact=False):
            return

        obj.ndb.desert_death_in_progress = True
        try:
            from world.workgroup_start import kill_in_desert

            kill_in_desert(obj, self)
        finally:
            obj.ndb.desert_death_in_progress = False
