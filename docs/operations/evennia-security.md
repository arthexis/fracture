# Arthexis Evennia Node Operations

Last verified on 2026-05-17 UTC.

This document describes the live Evennia game and security configuration on this
node. It is intentionally operational: use it before changing SSH, firewall,
nginx, fail2ban, systemd, or Evennia settings.

## Game Source

- Game directory: `/home/ubuntu/evennia-game/arthexis`
- Git branch: `main`
- Current repository scope: Evennia game source and this documentation.
- Runtime owner: `evennia:ubuntu` for the game tree; Git metadata may be owned by
  `ubuntu`.
- Local Git identity: `Arthexis Server <arthexis@localhost>`
- Remote: none configured at the time this document was created.

Do not commit runtime state or secrets. The repo `.gitignore` excludes
`server/conf/secret_settings.py`, database files, logs, pids, private SSH keys,
initial superuser credentials, bytecode, and generated static/media output.

## Local Codex Skill

A node-local Codex skill exists at:

```text
/home/ubuntu/.codex/skills/arthexis-evennia-node
```

Use it in future agent sessions for work involving this Evennia deployment,
HTTPS web play, UFW/fail2ban/nginx/sshd hardening, retired play SSH rollback, and safe validation
workflow. The skill is intentionally node-local and is not part of this game
repo.

## Agent Harness Skills And Tools

Operator-side agent harness work is split between local Codex skills and this
node-local operational skill.

Operator-local skills currently associated with this work:

- `arthexis-evennia-node`: production node operations and safety checks.
- `evennia-agent-harness`: local console-owned Evennia agent bridge prototype,
  including master-account gating and awareness logging.
- `evennia-game-customization`: game mechanics in the Evennia `mygame` layer,
  such as account state, commands, cmdsets, scripts, and Attributes.

Operator-local harness tools are not deployed as production services on this
node. The current prototype lives on the operator Windows host, including:

- `C:\Users\arthexis\evennia-agent.bat`
- `C:\Users\arthexis\Repos\evennia-local\tools\evennia_agent_console.py`
- `C:\Users\arthexis\Repos\evennia-local\mygame\world\agent_bridge.py`

The live production play path is the HTTPS Evennia web client. Public users enter at
`https://arthexis.com/play`, which nginx redirects to `/webclient/`, and the web
client connects through `wss://arthexis.com/evennia-websocket/`. The old `sshd-play.service` on port `2222` has been decommissioned. Its unit, bridge, wrapper, tmpfiles config, and related password-rotation units are archived under `/root/arthexis-retired-evennia-ssh-play-20260517T184321Z` and the systemd units are masked.

Do not couple the public player path with a model-calling agent harness without
an explicit proposal and operator approval.

Proposal material for aligning the local harness skills/tools with this
production node lives under:

```text
docs/proposals/agent-harness-skills-tools/
```

## Public Network Policy

UFW is active with default deny incoming and allow outgoing. The intended public
listeners are:

- `22/tcp`: administrative SSH. The shared `play` user is denied here.
- `443/tcp`: HTTPS and WSS through nginx, including `/play`, `/webclient/`, and
  `/evennia-websocket/`.
- `8443/tcp`: alternate HTTPS and WSS through nginx.
- `80/tcp`: HTTP only for Let's Encrypt HTTP-01 renewal and HTTP to HTTPS
  redirect.

Port `2222/tcp` is decommissioned and should stay closed unless the operator explicitly asks for rollback.

Everything else should be loopback-only unless there is a documented reason.
Validate with:

```bash
sudo ufw status verbose
sudo ss -ltnp
```

Expected loopback-only listeners include Redis, local DNS, Evennia telnet/web
backend ports, and Django backend ports. At the time of verification:

- Evennia telnet bridge target: `127.0.0.1:4000`
- Evennia web backend: `127.0.0.1:4001` and `127.0.0.1:4005`
- Evennia websocket backend: `127.0.0.1:4002`
- Evennia AMP backend: `127.0.0.1:4006`
- Suite Django backend: `0.0.0.0:8888`, protected from public access by UFW.
- Other Django app backends may bind locally on `127.0.0.1:8889-8891`.
- Redis: `127.0.0.1:6379` and `[::1]:6379`

## SSH And Web Play

The normal OpenSSH service handles administration on port `22` and explicitly
denies the shared `play` user:

- Service: `ssh.service`
- Config drop-in: `/etc/ssh/sshd_config.d/90-evennia-play.conf`

Public player ingress is now web-based:

- Public URL: `https://arthexis.com/play`
- Web client URL: `https://arthexis.com/webclient/`
- Websocket URL: `wss://arthexis.com/evennia-websocket/`
- Nginx live config: `/etc/nginx/sites-enabled/arthexis.conf`
- Nginx rate limit zone: `/etc/nginx/conf.d/evennia-webplay-limits.conf`

Evennia settings for this path live in
`/home/ubuntu/evennia-game/arthexis/server/conf/settings.py` and currently bind
the Evennia web and websocket services to loopback-only interfaces. Nginx is the
only public frontend for those services.

Retired SSH play artifacts were archived for audit under `/root/arthexis-retired-evennia-ssh-play-20260517T184321Z`. The live paths below should be absent or masked:

- Service: `sshd-play.service`
- Unit file: `/etc/systemd/system/sshd-play.service`
- Config: `/etc/ssh/sshd_config_play`
- Forced command: `/usr/local/bin/arthexis-evennia-play`
- Bridge command: `/usr/local/bin/arthexis-evennia-play-bridge`
- Runtime dirs: `/run/lock/arthexis-evennia-play` and
  `/run/lock/arthexis-evennia-play/sessions`
- tmpfiles config: `/etc/tmpfiles.d/arthexis-evennia-play.conf`

The footer item labeled `The Workgroup` points directly to `https://arthexis.com/play`; the old `/workgroup/` page is removed.

The daily password timer is decommissioned and masked on the web-play path. Recreate it only as part of an explicit SSH-play rollback.

The old one-login-per-source-IP lock applies only to the retired SSH wrapper.
HTTPS/WSS browser gameplay does not use that SSH lock; use nginx rate limiting
and Evennia/web-layer controls for browser traffic.

## Evennia Service

Evennia is managed by systemd:

- Service: `evennia.service`
- Unit file: `/etc/systemd/system/evennia.service`
- User/group: `evennia:evennia`
- Working directory: `/home/ubuntu/evennia-game/arthexis`
- Python path: `/home/ubuntu/evennia-venv/bin`

The unit has hardening enabled, including:

- `NoNewPrivileges=true`
- `PrivateTmp=true`
- `PrivateDevices=true`
- `ProtectSystem=full`
- `ProtectKernelTunables=true`
- `ProtectKernelModules=true`
- `ProtectKernelLogs=true`
- `ProtectControlGroups=true`
- `RestrictSUIDSGID=true`
- `LockPersonality=true`
- `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6`
- empty `CapabilityBoundingSet`
- `LimitNOFILE=65536`

Common operations:

```bash
sudo systemctl status evennia
sudo systemctl reload evennia
sudo systemctl restart evennia
sudo journalctl -u evennia -n 100 --no-pager
```

Use reload for normal Evennia code changes when possible. Use restart when the
portal/server process state is suspect or when reload does not pick up a change.

## Nginx And Web Backends

Nginx should expose only HTTP/HTTPS/WSS-facing ports publicly. These live nginx
files currently contain the public listen directives:

- `/etc/nginx/sites-enabled/arthexis.conf`
- `/etc/nginx/conf.d/gelectriic-instances.conf`

The source renderers that can regenerate those nginx files live outside the
Evennia game repo:

- `/home/ubuntu/arthexis/apps/nginx/renderers.py`
- `/home/ubuntu/audi/apps/nginx/renderers.py`
- `/home/ubuntu/porsche/apps/nginx/renderers.py`
- `/home/ubuntu/replicant/apps/nginx/renderers.py`

The Django service start scripts in those trees should bind runserver to
`127.0.0.1` unless `ARTHEXIS_RUNSERVER_HOST` intentionally overrides it:

- `/home/ubuntu/arthexis/scripts/service-start.sh`
- `/home/ubuntu/audi/scripts/service-start.sh`
- `/home/ubuntu/porsche/scripts/service-start.sh`
- `/home/ubuntu/replicant/scripts/service-start.sh`

Validate nginx before reloading:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Fail2ban

Fail2ban protects admin SSH. The retired `sshd-play` jail was removed during the 2026-05-17 web-play cleanup.

- Config: `/etc/fail2ban/jail.d/arthexis-ssh.local`
- Admin jail: `sshd`, port `22`, `maxretry = 5`

Useful commands:

```bash
sudo fail2ban-client status
sudo fail2ban-client status sshd
sudo journalctl -u fail2ban -n 100 --no-pager
```

## Capacity Notes

Web play is exposed through nginx with a dedicated request limit zone for the
Evennia web client and websocket paths. Evennia itself still backs the game
traffic, so capacity is bounded by the Evennia server, web socket handling,
system resources, and the database.

There is no load-test-backed player capacity number for this node. Treat the
current setup as suitable for low to moderate traffic until tested. PostgreSQL
was intentionally not enabled; SQLite can become the limiting factor under
write-heavy multi-player load. Revisit PostgreSQL before advertising high
concurrency.

## Safe Change Workflow

Before editing live security configuration:

```bash
git -C /home/ubuntu/evennia-game/arthexis status --short --branch
sudo systemctl is-active ssh evennia fail2ban nginx
sudo systemctl is-enabled sshd-play arthexis-workgroup-play-password.service arthexis-workgroup-play-password.timer || true
sudo ufw status verbose
sudo ss -ltnp
```

After changing SSH, nginx, firewall, fail2ban, or Evennia settings:

```bash
sudo sshd -t
sudo sshd -t -f /etc/ssh/sshd_config_play  # only for retired play SSH rollback edits
sudo nginx -t
sudo systemctl reload ssh
sudo systemctl restart fail2ban
sudo systemctl reload nginx
sudo systemctl reload evennia
sudo systemctl is-active ssh evennia fail2ban nginx
sudo systemctl is-enabled sshd-play arthexis-workgroup-play-password.service arthexis-workgroup-play-password.timer || true
sudo fail2ban-client status
sudo ufw status verbose
sudo ss -ltnp
```

Only run the restart/reload commands for services affected by the change.
Validate from a separate terminal before closing an existing administrative SSH
session.
