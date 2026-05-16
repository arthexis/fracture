# Arthexis Game Source Control

Last verified on 2026-05-16 UTC.

The Evennia game directory is a Git repository:

```text
/home/ubuntu/evennia-game/arthexis
```

Source-control baseline when this file was added:

- Branch: `main`
- Initial source commit: `f8abebe Initial Evennia game source`
- Operations runbook commit: `8a1a771 Add Evennia operations runbook`
- Local Git identity: `Arthexis Server <arthexis@localhost>`
- Remote: none configured at verification time.

Use `git log` for the current HEAD; this file records the repository location
and operating policy rather than every future commit.

Use this command before editing game code or source-controlled documentation:

```bash
git -C /home/ubuntu/evennia-game/arthexis status --short --branch
```

Repository policy:

- Commit Evennia game source, proposals, and operator documentation that should
  survive future sessions.
- Do not commit runtime state, secrets, local databases, logs, pids, private
  keys, generated static/media output, or initial superuser credentials.
- The game tree is runtime-owned by `evennia:ubuntu`; Git metadata may be owned
  by `ubuntu`.
- `/home/ubuntu/evennia-game/arthexis` is configured as a Git safe directory for
  the operator account because of the mixed runtime/source ownership.

Useful commands:

```bash
git -C /home/ubuntu/evennia-game/arthexis log --oneline --decorate -5
git -C /home/ubuntu/evennia-game/arthexis diff --stat
git -C /home/ubuntu/evennia-game/arthexis status --ignored --short
```
