"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

from evennia.objects.objects import DefaultCharacter

from world import player_decks, secret_traits

from .objects import ObjectParent


class Character(ObjectParent, DefaultCharacter):
    """
    The Character just re-implements some of the Object's methods and hooks
    to represent a Character entity in-game.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Object child classes like this.

    """

    def at_object_creation(self):
        super().at_object_creation()
        secret_traits.ensure_default_traits(self)

    def at_init(self):
        super().at_init()
        secret_traits.ensure_default_traits(self)

    def at_post_puppet(self, **kwargs):
        secret_traits.ensure_default_traits(self)
        super().at_post_puppet(**kwargs)

    def get_display_name(self, looker=None, **kwargs):
        name = super().get_display_name(looker=looker, **kwargs)
        if not hasattr(looker, "db_account"):
            return name
        if not secret_traits.has_secret_trait(looker, secret_traits.TRUE_SIGHT):
            return name

        account = getattr(self, "account", None)
        if not account:
            return name

        card_window = player_decks.format_top_bottom(account)
        if not card_window:
            return name
        return f"{name} [{card_window}]"
