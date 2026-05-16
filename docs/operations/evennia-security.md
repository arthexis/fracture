# Arthexis Evennia Node Operations

Last verified on 2026-05-16 UTC.

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
play SSH gateway, UFW/fail2ban/nginx/sshd hardening, and safe validation
workflow. The skill is intentionally node-local and is not part of this game
repo.

## Public Network Policy

UFW is active with default deny incoming and allow outgoing. The intended public
listeners are:

- `22/tcp`: administrative SSH. The shared `play` user is denied here.
- `2222/tcp`: Evennia play SSH, served by `sshd-play.service`.
- `443/tcp`: HTTPS and WSS through nginx.
- `8443/tcp`: alternate HTTPS and WSS through nginx.
- `80/tcp`: HTTP only for Let's Encrypt HTTP-01 renewal and HTTP to HTTPS
  redirect.

Everything else should be loopback-only unless there is a documented reason.
Validate with:

```bash
sudo ufw status verbose
sudo ss -ltnp
```

Expected loopback-only listeners include Redis, local DNS, Evennia telnet/web
backend ports, and Django backend ports. At the time of verification:

- Evennia telnet bridge target: `127.0.0.1:4000`
- Evennia web/socket backend: `127.0.0.1:4006`
- Django app backends: `127.0.0.1:8888-8891`
- Redis: `127.0.0.1:6379` and `[::1]:6379`

## SSH Split

There are two SSH roles on this node.

The normal OpenSSH service handles administration on port `22` and explicitly
denies the shared `play` user:

- Service: `ssh.service`
- Config drop-in: `/etc/ssh/sshd_config.d/90-evennia-play.conf`

The dedicated play SSH daemon handles public game logins on port `2222`:

- Service: `sshd-play.service`
- Unit file: `/etc/systemd/system/sshd-play.service`
- Config: `/etc/ssh/sshd_config_play`
- Forced command: `/usr/local/bin/arthexis-evennia-play`
- Bridge command: `/usr/local/bin/arthexis-evennia-play-bridge`
- Runtime dirs: `/run/lock/arthexis-evennia-play` and
  `/run/lock/arthexis-evennia-play/sessions`
- tmpfiles config: `/etc/tmpfiles.d/arthexis-evennia-play.conf`

Important play SSH settings:

- `AllowUsers play`
- `PasswordAuthentication yes`
- `PubkeyAuthentication no`
- `KbdInteractiveAuthentication no`
- `AuthenticationMethods password`
- `MaxAuthTries 3`
- `LoginGraceTime 30`
- `MaxSessions 1`
- `MaxStartups 30:30:100`
- `PerSourceMaxStartups 2`
- `PerSourceNetBlockSize 32:128`
- `DisableForwarding yes`
- `ForceCommand /usr/local/bin/arthexis-evennia-play`

Player command:

```bash
ssh -p 2222 play@HOSTNAME_OR_IP
```

## One Login Per Source IP

The one-login policy is enforced in the forced command before the Evennia bridge
starts. `/usr/local/bin/arthexis-evennia-play` reads the source address from
`SSH_CONNECTION`, normalizes it into a lock-file key, and takes a non-blocking
`flock` under `/run/lock/arthexis-evennia-play`. A second concurrent login from
the same source IP is rejected with:

```text
Only one Arthexis Evennia play login is allowed per IP address.
```

After acquiring the lock, the wrapper exports `ARTHEXIS_PLAY_CLIENT_IP` and execs
the Python bridge. The bridge connects to Evennia's loopback telnet port
`127.0.0.1:4000`, records a temporary local-source-port to real-client-IP mapping
in `/run/lock/arthexis-evennia-play/sessions`, and relays the terminal stream.

Evennia uses `server/conf/play_telnet.py` via this setting:

```python
TELNET_PROTOCOL_CLASS = "server.conf.play_telnet.PlayTelnetProtocol"
```

That protocol class lets Evennia recover the real SSH client IP rather than
seeing every play SSH session as `127.0.0.1`.

This one-IP lock applies to the play SSH path. HTTPS/WSS paths do not use this
SSH lock; if browser gameplay is exposed, enforce equivalent limits at the web
or Evennia layer before relying on the one-login policy globally.

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

Fail2ban protects both admin SSH and play SSH:

- Config: `/etc/fail2ban/jail.d/arthexis-ssh.local`
- Admin jail: `sshd`, port `22`, `maxretry = 5`
- Play jail: `sshd-play`, port `2222`, aggressive sshd filter,
  `maxretry = 3`, `findtime = 10m`, `bantime = 4h`
- Play journal match: `_SYSTEMD_UNIT=sshd-play.service + _COMM=sshd`

Useful commands:

```bash
sudo fail2ban-client status
sudo fail2ban-client status sshd
sudo fail2ban-client status sshd-play
sudo journalctl -u fail2ban -n 100 --no-pager
```

## Capacity Notes

The play SSH daemon limits unauthenticated connection pressure with
`MaxStartups 30:30:100` and `PerSourceMaxStartups 2`. Authenticated play sessions
are limited by the one-session-per-source-IP lock, system resources, Evennia, and
the database.

There is no load-test-backed player capacity number for this node. Treat the
current setup as suitable for low to moderate traffic until tested. PostgreSQL
was intentionally not enabled; SQLite can become the limiting factor under
write-heavy multi-player load. Revisit PostgreSQL before advertising high
concurrency.

## Safe Change Workflow

Before editing live security configuration:

```bash
git -C /home/ubuntu/evennia-game/arthexis status --short --branch
sudo systemctl is-active ssh sshd-play evennia fail2ban nginx
sudo ufw status verbose
sudo ss -ltnp
```

After changing SSH, nginx, firewall, fail2ban, or Evennia settings:

```bash
sudo sshd -t
sudo sshd -t -f /etc/ssh/sshd_config_play
sudo nginx -t
sudo systemctl restart sshd-play
sudo systemctl reload ssh
sudo systemctl restart fail2ban
sudo systemctl reload nginx
sudo systemctl reload evennia
sudo systemctl is-active ssh sshd-play evennia fail2ban nginx
sudo fail2ban-client status
sudo ufw status verbose
sudo ss -ltnp
```

Only run the restart/reload commands for services affected by the change.
Validate from a separate terminal before closing an existing administrative SSH
session.
