"""
Account typeclasses for Arthexis Evennia.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import check_password

from evennia.accounts.accounts import DefaultAccount, DefaultGuest
from evennia.accounts.models import AccountDB

from world import player_decks


SUITE_DB_PATH = Path("/home/ubuntu/arthexis/db.sqlite3")
SUITE_PRIVILEGED_PERM = "Developer"
DEFAULT_PLAYER_PERM = "Player"
PRIVILEGED_PERMS = ("Helper", "Builder", "Admin", "Developer")
ADMIN_DEFAULT_REJECTION = "admin/admin is not a valid Evennia login."
RESERVED_SUITE_NAME_REJECTION = (
    "That account name is reserved for an Arthexis suite superuser."
)


def _normalized_username(username: object) -> str:
    return str(username or "").strip()


def _suite_user_table(connection: sqlite3.Connection) -> str | None:
    """Return the Arthexis suite user table name from the local DB schema."""

    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = ? ORDER BY name",
        ("table",),
    ).fetchall()
    for row in rows:
        table_name = row[0]
        columns = {info[1] for info in connection.execute(f"PRAGMA table_info({table_name})")}
        if {"username", "password", "is_superuser", "is_active"}.issubset(columns):
            return table_name
    return None


def _suite_user_row(username: object) -> dict[str, object] | None:
    """Return the matching Arthexis suite user row, if the local suite DB exists."""

    normalized = _normalized_username(username)
    if not normalized or not SUITE_DB_PATH.exists():
        return None
    try:
        with sqlite3.connect(str(SUITE_DB_PATH)) as connection:
            connection.row_factory = sqlite3.Row
            table_name = _suite_user_table(connection)
            if not table_name:
                return None
            row = connection.execute(
                f"""
                SELECT username, password, is_superuser, is_active
                FROM {table_name}
                WHERE lower(username) = lower(?)
                LIMIT 1
                """,
                (normalized,),
            ).fetchone()
    except sqlite3.Error:
        return None
    return dict(row) if row else None


def _is_suite_superuser(username: object) -> bool:
    row = _suite_user_row(username)
    return bool(row and row.get("is_active") and row.get("is_superuser"))


def _suite_password_valid(username: object, password: object) -> bool:
    row = _suite_user_row(username)
    if not row or not row.get("is_active") or not row.get("is_superuser"):
        return False
    encoded = str(row.get("password") or "")
    return check_password(str(password or ""), encoded)


def _is_admin_default_pair(username: object, password: object) -> bool:
    return _normalized_username(username).lower() == "admin" and str(password or "") == "admin"


class Account(DefaultAccount):
    """Account policy tied to Arthexis suite superuser status."""

    @classmethod
    def create(cls, *args, **kwargs):
        username = kwargs.get("username", args[0] if args else "")
        password = kwargs.get("password", args[1] if len(args) > 1 else "")
        username = cls.normalize_username(username)

        if _is_admin_default_pair(username, password):
            return None, [ADMIN_DEFAULT_REJECTION]

        if _is_suite_superuser(username) and not _suite_password_valid(username, password):
            return None, [RESERVED_SUITE_NAME_REJECTION]

        kwargs["permissions"] = [settings.PERMISSION_ACCOUNT_DEFAULT]
        account, errors = super().create(*args, **kwargs)
        if account:
            account.sync_arthexis_suite_permissions()
        return account, errors

    @classmethod
    def authenticate(cls, username, password, ip="", **kwargs):
        username = cls.normalize_username(username)

        if _is_admin_default_pair(username, password):
            return None, [ADMIN_DEFAULT_REJECTION]

        if _is_suite_superuser(username):
            if not _suite_password_valid(username, password):
                return None, [RESERVED_SUITE_NAME_REJECTION]
            account = AccountDB.objects.get_account_from_name(username)
            if not account:
                account, errors = cls.create(
                    username=username,
                    password=password,
                    ip=ip,
                    session=kwargs.get("session"),
                    permissions=[settings.PERMISSION_ACCOUNT_DEFAULT],
                )
                if not account:
                    return None, errors
            account.sync_arthexis_suite_permissions()
            return account, []

        account, errors = super().authenticate(username, password, ip=ip, **kwargs)
        if account:
            account.sync_arthexis_suite_permissions()
        return account, errors

    def at_account_creation(self):
        super().at_account_creation()
        self.sync_arthexis_suite_permissions()
        player_decks.get_or_create_deck(self)

    def at_post_login(self, session=None, **kwargs):
        self.sync_arthexis_suite_permissions()
        player_decks.get_or_create_deck(self)
        super().at_post_login(session=session, **kwargs)

    def sync_arthexis_suite_permissions(self):
        """Promote only Arthexis suite superusers; demote every other account."""

        suite_superuser = _is_suite_superuser(self.username)
        changed_fields = []
        if self.is_superuser != suite_superuser:
            self.is_superuser = suite_superuser
            changed_fields.append("is_superuser")
        if self.is_staff != suite_superuser:
            self.is_staff = suite_superuser
            changed_fields.append("is_staff")
        if changed_fields:
            self.save(update_fields=changed_fields)

        for perm in PRIVILEGED_PERMS:
            self.permissions.remove(perm)
        self.permissions.add(DEFAULT_PLAYER_PERM)
        if suite_superuser:
            self.permissions.add(SUITE_PRIVILEGED_PERM)
        return suite_superuser


class Guest(DefaultGuest):
    """Guest accounts are disabled unless explicitly enabled in settings."""

    pass
