"""
File-backed bridge between Evennia and the operator console harness.

The game server never calls an LLM or holds operator secrets. It only records
requests and delivers responses while a console-owned bridge session is alive.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BRIDGE_DIR_ENV = "EVENNIA_AGENT_BRIDGE_DIR"
DEFAULT_LEASE_SECONDS = 30
DEFAULT_MASTER_ACCOUNT = "arthexis"
DEFAULT_LOG_FILENAME = "agent-awareness.jsonl"
_WRITE_LOCK = threading.RLock()


class BridgeOffline(RuntimeError):
    """Raised when an in-game caller tries to use the bridge while offline."""


class BridgeUnauthorized(RuntimeError):
    """Raised when an in-game caller is not the bridge session master."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def bridge_dir() -> Path:
    configured = os.environ.get(BRIDGE_DIR_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "server" / "agent_bridge"


def ensure_bridge_dirs() -> Path:
    root = bridge_dir()
    for name in ("requests", "responses", "delivered", "archive", "hook_prompts"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def default_log_path() -> Path:
    return bridge_dir() / DEFAULT_LOG_FILENAME


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    with _WRITE_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        tmp_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        try:
            for attempt in range(5):
                try:
                    os.replace(tmp_path, path)
                    return
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.05 * (attempt + 1))
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass


def _json_default(value: Any) -> str:
    return str(value)


def log_path(session: dict[str, Any] | None = None) -> Path:
    session = session or read_session() or {}
    configured = session.get("log_file")
    if configured:
        return Path(configured).expanduser().resolve()
    return default_log_path()


def append_journal_event(event: str, *, session: dict[str, Any] | None = None, **payload: Any) -> None:
    """
    Append one awareness event to the bridge journal.

    This is deliberately best-effort; bridge behavior should not fail because
    the operator journal cannot be written.
    """
    session = session or read_session() or {}
    record = {
        "timestamp": format_time(utc_now()),
        "event": event,
        "session_id": session.get("id", ""),
        "operator": session.get("operator", ""),
        "master_account": session.get("master_account", DEFAULT_MASTER_ACCOUNT),
        **payload,
    }
    path = log_path(session)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = (json.dumps(record, sort_keys=True, default=_json_default) + "\n").encode("utf-8")
        fd = os.open(str(path), os.O_APPEND | os.O_CREAT | os.O_WRONLY)
        try:
            os.write(fd, encoded)
        finally:
            os.close(fd)
    except OSError:
        pass


def _iter_json_files(subdir: str) -> list[tuple[Path, dict[str, Any]]]:
    root = ensure_bridge_dirs() / subdir
    items: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(root.glob("*.json"), key=lambda item: (item.stat().st_mtime, item.name)):
        data = _read_json(path)
        if data is not None:
            items.append((path, data))
    return items


def session_path() -> Path:
    return ensure_bridge_dirs() / "session.json"


def read_session() -> dict[str, Any] | None:
    return _read_json(session_path())


def session_status(now: datetime | None = None) -> dict[str, Any]:
    now = now or utc_now()
    session = read_session() or {}
    expires_at = parse_time(session.get("expires_at"))
    active = session.get("status") == "active" and expires_at is not None and expires_at > now
    seconds_remaining = int((expires_at - now).total_seconds()) if active and expires_at else 0
    return {
        "active": active,
        "seconds_remaining": max(0, seconds_remaining),
        "session": session,
    }


def active_session(now: datetime | None = None) -> dict[str, Any] | None:
    status = session_status(now=now)
    return status["session"] if status["active"] else None


def write_session(
    session_id: str,
    *,
    operator: str,
    master_account: str = DEFAULT_MASTER_ACCOUNT,
    log_file: str | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    capabilities: list[str] | None = None,
) -> dict[str, Any]:
    now = utc_now()
    current = read_session() or {}
    if current.get("id") == session_id:
        created_at = current.get("created_at") or format_time(now)
    else:
        created_at = format_time(now)
    session = {
        "id": session_id,
        "status": "active",
        "operator": operator,
        "master_account": master_account or DEFAULT_MASTER_ACCOUNT,
        "log_file": log_file or current.get("log_file") or str(default_log_path()),
        "capabilities": capabilities or [],
        "created_at": created_at,
        "heartbeat_at": format_time(now),
        "expires_at": format_time(now + timedelta(seconds=lease_seconds)),
        "lease_seconds": lease_seconds,
    }
    _write_json_atomic(session_path(), session)
    return session


def close_session(session_id: str) -> None:
    session = read_session()
    if not session or session.get("id") != session_id:
        return
    now = utc_now()
    session.update(
        {
            "status": "offline",
            "closed_at": format_time(now),
            "heartbeat_at": format_time(now),
            "expires_at": format_time(now),
        }
    )
    _write_json_atomic(session_path(), session)


def _dbref(obj: Any) -> str:
    dbref = getattr(obj, "dbref", None)
    if dbref:
        return str(dbref)
    obj_id = getattr(obj, "id", None)
    return f"#{obj_id}" if obj_id is not None else ""


def _key(obj: Any) -> str:
    return str(getattr(obj, "key", "") or getattr(obj, "name", "") or "")


def target_for_caller(caller: Any) -> dict[str, str]:
    location = getattr(caller, "location", None)
    return {
        "caller_dbref": _dbref(caller),
        "character_name": _key(caller),
        "account_name": caller_account_name(caller),
        "location_dbref": _dbref(location) if location else "",
        "location_name": _key(location) if location else "",
    }


def caller_account_name(caller: Any) -> str:
    account = getattr(caller, "account", None)
    return _key(account) if account else _key(caller)


def master_account_name(session: dict[str, Any] | None) -> str:
    if not session:
        return DEFAULT_MASTER_ACCOUNT
    return session.get("master_account") or DEFAULT_MASTER_ACCOUNT


def caller_is_master(caller: Any, session: dict[str, Any] | None = None) -> bool:
    account_name = caller_account_name(caller)
    master = master_account_name(session or read_session())
    return bool(account_name) and account_name.casefold() == master.casefold()


def submit_request(message: str, caller: Any, *, skill: str | None = None) -> dict[str, Any]:
    session = active_session()
    if not session:
        raise BridgeOffline("Console agent is offline.")
    target = target_for_caller(caller)
    if not caller_is_master(caller, session=session):
        append_journal_event(
            "game.request_rejected",
            session=session,
            reason="unauthorized_account",
            message=message,
            requested_skill=skill or "",
            target=target,
        )
        raise BridgeUnauthorized("Console agent does not accept requests from this account.")

    ensure_bridge_dirs()
    now = utc_now()
    request_id = uuid.uuid4().hex
    data = {
        "id": request_id,
        "session_id": session["id"],
        "source": "evennia",
        "created_at": format_time(now),
        "message": message,
        "requested_skill": skill or "",
        "target": target,
    }
    filename = f"{now.strftime('%Y%m%dT%H%M%SZ')}_{request_id}.json"
    _write_json_atomic(ensure_bridge_dirs() / "requests" / filename, data)
    append_journal_event("game.request_queued", session=session, request=data)
    return data


def pending_requests(session_id: str | None = None) -> list[tuple[Path, dict[str, Any]]]:
    requests = []
    for path, data in _iter_json_files("requests"):
        if session_id and data.get("session_id") != session_id:
            continue
        if response_path_for(data).exists():
            continue
        requests.append((path, data))
    return requests


def response_path_for(request: dict[str, Any]) -> Path:
    return ensure_bridge_dirs() / "responses" / f"{request['id']}.json"


def write_response(
    request: dict[str, Any],
    text: str,
    *,
    hook: dict[str, Any] | None = None,
    refused: bool = False,
) -> dict[str, Any]:
    now = utc_now()
    response = {
        "id": request["id"],
        "session_id": request.get("session_id", ""),
        "source": "operator_console",
        "created_at": format_time(now),
        "text": text,
        "refused": bool(refused),
        "hook": hook or {},
        "target": request.get("target", {}),
        "request": request,
    }
    _write_json_atomic(response_path_for(request), response)
    append_journal_event("console.response_written", request_id=request["id"], refused=bool(refused), response=response)
    return response


def archive_request(path: Path, *, status: str) -> None:
    if not path.exists():
        return
    archive_dir = ensure_bridge_dirs() / "archive" / "requests"
    archive_dir.mkdir(parents=True, exist_ok=True)
    destination = archive_dir / f"{path.stem}.{status}.json"
    if destination.exists():
        destination = archive_dir / f"{path.stem}.{status}.{uuid.uuid4().hex}.json"
    shutil.move(str(path), str(destination))


def pending_responses() -> list[tuple[Path, dict[str, Any]]]:
    return _iter_json_files("responses")


def mark_response_delivered(path: Path, *, delivered: bool, reason: str = "") -> None:
    data = _read_json(path) or {}
    data.update(
        {
            "delivery_status": "delivered" if delivered else "undelivered",
            "delivery_reason": reason,
            "delivered_at": format_time(utc_now()),
        }
    )
    destination = ensure_bridge_dirs() / "delivered" / path.name
    _write_json_atomic(destination, data)
    try:
        path.unlink()
    except OSError:
        pass
