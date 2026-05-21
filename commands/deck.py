"""
Developer-only commands for hidden per-account card decks.
"""

from __future__ import annotations

from evennia.commands.default.muxcommand import MuxAccountCommand

from world import player_decks


class CmdDeck(MuxAccountCommand):
    """
    Inspect and manage hidden account card decks.

    Usage:
      @deck/status <account>
      @deck/reset <account>
      @deck/draw <account> = <count>

    This command is restricted to Developer accounts.
    """

    key = "@deck"
    locks = "cmd:perm(Developer)"
    help_category = "Admin"
    switch_options = ("status", "reset", "draw")

    def _usage(self) -> None:
        self.msg(
            "Usage: @deck/status <account> | @deck/reset <account> | "
            "@deck/draw <account> = <count>"
        )

    def _target_account(self):
        if not self.lhs:
            self._usage()
            return None
        return self.caller.search_account(self.lhs.lstrip("*"))

    def _status(self, account) -> None:
        state = player_decks.get_or_create_deck(account)
        self.msg(
            "\n".join(
                (
                    f"Deck for {account.key}:",
                    f"  version: {state.get('version')}",
                    f"  deck size: {len(player_decks.FULL_DECK)}",
                    f"  remaining: {len(state['deck'])}",
                    f"  discard: {len(state['discard'])}",
                    f"  burned: {len(state['burned'])}",
                    f"  desert_shield_minutes: {state.get('desert_shield_minutes', 0)}",
                    f"  draw_count: {state.get('draw_count', 0)}",
                    f"  burn_count: {state.get('burn_count', 0)}",
                    f"  shuffle_count: {state.get('shuffle_count', 0)}",
                    f"  created_at: {state.get('created_at', '')}",
                    f"  shuffled_at: {state.get('shuffled_at', '')}",
                )
            )
        )

    def _reset(self, account) -> None:
        state = player_decks.reset_deck(account)
        self.msg(
            f"Reset deck for {account.key}: {len(state['deck'])} remaining, "
            f"{len(state['discard'])} discarded."
        )

    def _draw(self, account) -> None:
        if not self.rhs:
            self._usage()
            return
        try:
            count = int(self.rhs)
            drawn = player_decks.draw_cards(account, count)
        except ValueError as err:
            self.msg(str(err))
            return

        state = player_decks.get_or_create_deck(account)
        self.msg(
            f"Drew {len(drawn)} card(s) for {account.key}: {', '.join(drawn)}\n"
            f"Remaining: {len(state['deck'])}; discard: {len(state['discard'])}."
        )

    def func(self):
        if not self.switches:
            self._usage()
            return
        if len(self.switches) > 1:
            self.msg("Use one @deck switch at a time.")
            return

        account = self._target_account()
        if not account:
            return

        switch = self.switches[0]
        if switch == "status":
            self._status(account)
        elif switch == "reset":
            self._reset(account)
        elif switch == "draw":
            self._draw(account)
