"""Unlogged-in command overrides for public account creation."""

from __future__ import annotations

import re

from django.conf import settings

from evennia.accounts.models import AccountDB
from evennia.commands.default.unloggedin import CmdUnconnectedCreate as DefaultCreate
from evennia.utils.utils import class_from_module

from typeclasses.accounts import (
    RESERVED_SUITE_NAME_REJECTION,
    _is_suite_superuser,
    _suite_password_valid,
)


class CmdUnconnectedCreate(DefaultCreate):
    """Create accounts without leaking reserved-name policy details."""

    def func(self):
        """Check unavailable names before the default confirmation prompt."""

        session = self.caller
        args = self.args.strip()
        address = session.address
        Account = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)

        parts = [part.strip() for part in re.split(r'"', args) if part.strip()]
        if len(parts) == 1:
            parts = parts[0].split(None, 1)
        if len(parts) != 2:
            string = (
                "\n Usage (without <>): create <name> <password>"
                "\nIf <name> or <password> contains spaces, enclose it in double quotes."
            )
            session.msg(string)
            return

        username, password = parts
        non_normalized_username = username
        username = Account.normalize_username(username)
        if non_normalized_username != username:
            session.msg(
                "Note: your username was normalized to strip spaces and remove characters "
                "that could be visually confusing."
            )

        existing_account = AccountDB.objects.get_account_from_name(username)
        if existing_account or (
            _is_suite_superuser(username) and not _suite_password_valid(username, password)
        ):
            session.msg(f"|R{RESERVED_SUITE_NAME_REJECTION}|n")
            return

        answer = yield (
            f"You want to create an account '{username}'."
            "\nIs this what you intended? [Y]/N?"
        )
        if answer.lower() in ("n", "no"):
            session.msg("Aborted. If your user name contains spaces, surround it by quotes.")
            return

        account, errors = Account.create(
            username=username, password=password, ip=address, session=session
        )
        if account:
            string = "A new account '%s' was created. Welcome!"
            if " " in username:
                string += (
                    "\n\nYou can now log in with the command "
                    "'connect \"%s\" <your password>'."
                )
            else:
                string += "\n\nYou can now log with the command 'connect %s <your password>'."
            session.msg(string % (username, username))
        else:
            session.msg("|R%s|n" % "\n".join(errors))
