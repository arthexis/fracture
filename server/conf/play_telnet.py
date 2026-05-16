"""Telnet protocol customizations for the SSH play gateway."""

from __future__ import annotations

import re
from pathlib import Path

from evennia.server.portal.telnet import TelnetProtocol
from evennia.utils import logger


SESSION_MAP_DIR = Path("/run/lock/arthexis-evennia-play/sessions")
IP_RE = re.compile(r"^[0-9A-Fa-f:.]{1,64}$")


class PlayTelnetProtocol(TelnetProtocol):
    """Recover the real SSH client IP from the local play bridge."""

    def connectionMade(self):
        super().connectionMade()
        client_address = self.transport.client
        if not client_address or client_address[0] not in {"127.0.0.1", "::1"}:
            return

        map_path = SESSION_MAP_DIR / str(client_address[1])
        try:
            client_ip = map_path.read_text(encoding="ascii").strip()
            map_path.unlink(missing_ok=True)
        except OSError:
            return

        if not IP_RE.match(client_ip):
            logger.log_warn(f"Ignoring invalid SSH play client IP mapping: {client_ip!r}")
            return

        self.address = client_ip
        self.protocol_flags["SSH_CLIENT_IP"] = client_ip
        if self.sessid and getattr(self, "server_connected", False):
            self.sessionhandler.sync(self)
