# Hidden Per-Account Card Deck Proposal

Status: proposal
Created: 2026-05-16 UTC
Scope: Evennia game mechanic implementation in `/home/ubuntu/evennia-game/arthexis`.
Target worker: remote agent working on the production Evennia game source.

## Goal

Give every player account a hidden 55-card poker deck: standard 52-card deck
plus three jokers. The deck is shuffled when first initialized and can later be
used by game systems for random events, player-vs-player tests, and
player-vs-environment tests.

## Current Source Context

- Game source: `/home/ubuntu/evennia-game/arthexis`
- Account typeclass: `typeclasses/accounts.py`
- Account lifecycle hooks already present:
  - `Account.at_account_creation()`
  - `Account.at_post_login()`
- Existing account logic syncs Arthexis suite permissions. Do not disrupt the
  suite-auth and permission-sync behavior.
- Reusable world modules live under `world/`.
- Commands are registered through `commands/default_cmdsets.py`.

## Design Decision

Store the deck as an Evennia Account Attribute first, not as a custom Django
model. This is simple per-account state and does not require query-heavy
reporting yet.

Suggested attribute key:

```python
account.db.poker_deck
```

Suggested state shape:

```python
{
    "version": 1,
    "deck": ["AS", "10D", "JokerA", "JokerC", "..."],
    "discard": [],
    "draw_count": 0,
    "shuffle_count": 1,
    "created_at": "...",
    "shuffled_at": "...",
}
```

Define the top of the deck as the end of the list and draw with `pop()`.

## Interpretation Of "Shuffle On Start"

Unless the operator refines this rule, interpret "on start" as first account
initialization or first lazy use. `at_post_login()` may ensure a missing deck
exists, but should not reshuffle an existing deck on every login. Provide an
explicit reset/shuffle helper for future mechanics and admin/debug use.

## Proposed Implementation

### Task 1: Add reusable deck service

Scope:

- `world/player_decks.py`

Implement:

- `FULL_DECK`: 52 cards plus `JokerA`, `JokerB`, and `JokerC`.
- `new_deck_state()` or equivalent constructor.
- `get_or_create_deck(account)`.
- `reset_deck(account)`.
- `draw_cards(account, count=1)`.
- `remaining_count(account)`.
- `discard_count(account)`.

Use `random.SystemRandom().shuffle(...)` or equivalent cryptographically backed
shuffle. Keep stored values compact and JSON-like.

Default draw behavior:

- Drawn cards move to `discard`.
- If the deck is exhausted and more cards are requested, reshuffle the discard
  into a new deck, increment `shuffle_count`, and continue.
- Reject counts less than 1.

### Task 2: Initialize accounts lazily and on creation

Scope:

- `typeclasses/accounts.py`

Add a minimal call to the deck service in:

- `Account.at_account_creation()`
- optionally `Account.at_post_login()` only to backfill missing decks

Do not alter the suite-superuser authentication logic or permission-sync policy.

### Task 3: Add admin/debug command surface

Scope:

- `commands/deck.py`
- `commands/default_cmdsets.py`

Add Developer-only commands, for example:

```text
@deck/status <account>
@deck/reset <account>
@deck/draw <account>=<count>
```

Guidelines:

- Lock commands to `Developer` or stronger.
- Do not expose hidden deck state to ordinary players.
- `status` may show counts and metadata. Full deck order should only be shown
  with an explicit debug switch, if implemented at all.
- Register the command on `AccountCmdSet` or another appropriate admin-visible
  cmdset.

### Task 4: Add a small shell-level validation path

Scope:

- No required automated test framework is currently established in this game
  repo; use import and Evennia shell smoke tests.

Add tests only if the remote agent establishes a clear local test pattern.

## Acceptance Criteria

- New and existing accounts can obtain a hidden 55-card deck.
- Decks persist on the Account through Evennia Attributes.
- Existing account auth and Arthexis suite permission sync still work.
- Drawing cards reduces the remaining deck count and increases discard count.
- Resetting restores a shuffled 55-card deck and empty discard pile.
- Non-Developer accounts cannot inspect or manipulate decks through commands.
- No secrets, runtime DB files, logs, pids, or generated output are committed.

## Verification Commands

Run from the production game directory:

```bash
cd /home/ubuntu/evennia-game/arthexis
git status --short --branch
/home/ubuntu/evennia-venv/bin/python -m compileall world typeclasses commands
```

Import smoke test:

```bash
/home/ubuntu/evennia-venv/bin/evennia shell -c "from world import player_decks; print(len(player_decks.FULL_DECK))"
```

Expected output:

```text
55
```

After code changes, reload Evennia when appropriate:

```bash
sudo systemctl reload evennia
sudo journalctl -u evennia -n 100 --no-pager
```

If command locks or permissions are changed, validate with a Developer account
and a normal Player account before considering the feature complete.

## Out Of Scope

- No public player command to view hidden decks.
- No custom Django model unless future reporting/audit requirements justify it.
- No changes to `sshd-play.service`, nginx, UFW, or the public play bridge.
- No replacement of raw random/event systems until a specific mechanic consumes
  the deck service.

## Risk And Rollback

Risk level: low to medium.

Primary risks:

- Accidentally reshuffling every login and losing persistent deck progress.
- Exposing hidden deck order to non-Developer players.
- Disturbing existing account authentication or suite permission sync.

Rollback:

- Revert changes to `world/player_decks.py`, `typeclasses/accounts.py`,
  `commands/deck.py`, and `commands/default_cmdsets.py`.
- Existing `account.db.poker_deck` Attributes can remain harmless, or be removed
  later with a targeted management/shell cleanup if needed.
