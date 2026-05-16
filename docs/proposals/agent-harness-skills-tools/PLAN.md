# Agent Harness Skills And Tools Proposal

Status: proposal
Created: 2026-05-16 UTC
Scope: documentation and planning only; no production harness deployment in this proposal.

## Goal

Align the operator-local Evennia agent harness skills/tools with the production
Arthexis Evennia node without weakening the current play SSH security boundary.

## Current Production Facts

- Production game source: `/home/ubuntu/evennia-game/arthexis`
- Production runbook: `docs/operations/evennia-security.md`
- Evennia service: `evennia.service`
- Public play SSH service: `sshd-play.service` on port `2222`
- Player command: `ssh -p 2222 play@arthexis.com`
- Forced command: `/usr/local/bin/arthexis-evennia-play`
- Telnet relay: `/usr/local/bin/arthexis-evennia-play-bridge`
- Evennia telnet target: `127.0.0.1:4000`
- Evennia web/socket backend: `127.0.0.1:4006`
- Real client IP restoration: `server/conf/play_telnet.py`

## Related Operator-Local Skills

- `arthexis-evennia-node`: production operations and safety checks.
- `evennia-agent-harness`: local console-owned agent bridge prototype.
- `evennia-game-customization`: game-mechanic implementation guidance for
  Evennia `mygame` code.

## Existing Operator-Local Harness Tools

- `C:\Users\arthexis\evennia-agent.bat`
- `C:\Users\arthexis\Repos\evennia-local\tools\evennia_agent_console.py`
- `C:\Users\arthexis\Repos\evennia-local\mygame\world\agent_bridge.py`

These tools establish a console-owned lease, master-account gating, awareness
logging, hook checks, and a passive Evennia queue. They are not currently a
production service on this node.

## Proposed Direction

1. Keep the production play SSH bridge independent from the agent harness.
2. Keep Evennia passive: no model calls, API keys, GitHub tokens, or SSH secrets
   in Evennia server code.
3. If production integration is requested, add a production-specific bridge that
   is operator-session scoped and disabled when the operator console exits.
4. Reuse the master-account gate and JSONL awareness log concepts from the local
   harness.
5. Route in-game requested skills through an operator-controlled console or a
   tightly scoped command runner, not through autonomous server-side execution.
6. Preserve the public listener policy: only `22`, `2222`, `80`, `443`, and
   `8443` should be public; Evennia `4000/4006` remain loopback-only.
7. Validate with the production runbook checks before and after any future
   implementation.

## Acceptance Criteria For Future Implementation

- The operator can start and stop the harness explicitly.
- In-game agent responses stop when the operator harness exits.
- Only an approved master account can issue obeyed requests.
- All requests, refusals, hook decisions, and responses are logged to one
  operator-visible awareness log.
- Normal players cannot trigger shell, GitHub, SSH, or filesystem actions.
- The existing `sshd-play.service` behavior and one-login-per-source-IP policy
  remain intact.

## Non-Goals

- Do not replace `sshd-play.service` in this proposal.
- Do not expose Evennia `4000` or `4006` publicly.
- Do not run an autonomous persistent LLM worker inside Evennia.
- Do not store model/provider credentials in the game repository or Evennia
  runtime settings.

## Validation Commands For Future Changes

```bash
git -C /home/ubuntu/evennia-game/arthexis status --short --branch
sudo systemctl is-active ssh sshd-play evennia fail2ban nginx
sudo sshd -t
sudo sshd -t -f /etc/ssh/sshd_config_play
sudo nginx -t
sudo ufw status verbose
sudo ss -ltnp
sudo journalctl -u evennia -n 100 --no-pager
```
