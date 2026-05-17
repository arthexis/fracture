"""
In-game command surface for the console-owned agent bridge.
"""

from __future__ import annotations

from commands.command import Command
from world import agent_bridge


class CmdAgent(Command):
    """
    Send a message to the operator console agent.

    Usage:
      agent <message>
      agent status
      @agent <message>

    The command only queues requests. The agent responds only while the local
    operator console harness is running.
    """

    key = "agent"
    aliases = ["@agent"]
    locks = "cmd:all()"
    help_category = "Agent"

    def func(self):
        text = self.args.strip()
        if not text or text.lower() == "status":
            self._show_status()
            return

        skill, message = self._parse_skill(text)
        try:
            request = agent_bridge.submit_request(message, self.caller, skill=skill)
        except agent_bridge.BridgeOffline:
            self.caller.msg("Console agent is offline. Start evennia-agent.bat from the operator console.")
            return
        except agent_bridge.BridgeUnauthorized as exc:
            self.caller.msg(str(exc))
            return

        suffix = f" with skill {skill}" if skill else ""
        self.caller.msg(f"Queued for the console agent{suffix} as {request['id'][:8]}.")

    def _show_status(self):
        status = agent_bridge.session_status()
        if not status["active"]:
            self.caller.msg("Console agent is offline.")
            return
        target = agent_bridge.target_for_caller(self.caller)
        if not agent_bridge.caller_is_master(self.caller, session=status["session"]):
            agent_bridge.append_journal_event(
                "game.status_rejected",
                session=status["session"],
                reason="unauthorized_account",
                target=target,
            )
            self.caller.msg("Console agent does not accept requests from this account.")
            return
        session = status["session"]
        agent_bridge.append_journal_event("game.status_requested", session=session, target=target)
        operator = session.get("operator") or "operator"
        master = agent_bridge.master_account_name(session)
        seconds = status["seconds_remaining"]
        self.caller.msg(
            f"Console agent is online for {operator}; master account is {master}; "
            f"lease refreshes in {seconds}s."
        )

    @staticmethod
    def _parse_skill(text: str) -> tuple[str | None, str]:
        parts = text.split(None, 2)
        if len(parts) >= 3 and parts[0].lower() == "@skill":
            return parts[1], parts[2]
        return None, text
