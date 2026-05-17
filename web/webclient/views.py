"""Arthexis suite-aware Evennia webclient view."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from typeclasses.accounts import Account


def _client_ip(request) -> str:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        for value in forwarded_for.split(","):
            candidate = value.strip()
            if candidate:
                return candidate
    return request.META.get("REMOTE_ADDR", "")


def _suite_session_cookie(request) -> tuple[str, str] | tuple[None, None]:
    cookie_name = getattr(settings, "WORKGROUP_PLAY_SUITE_SESSION_COOKIE_NAME", "sessionid")
    cookie_value = request.COOKIES.get(cookie_name)
    if not cookie_value:
        return None, None
    return cookie_name, cookie_value


def _suite_session_user(request) -> str | None:
    cookie_name, cookie_value = _suite_session_cookie(request)
    if not cookie_name or not cookie_value:
        return None

    url = str(getattr(settings, "WORKGROUP_PLAY_SUITE_SESSION_URL", "") or "").strip()
    if not url:
        return None

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Cookie": f"{cookie_name}={cookie_value}",
            "X-Arthexis-Evennia-Handoff": "1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status != 200:
                return None
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, ValueError):
        return None

    if not data.get("authenticated"):
        return None
    username = str(data.get("username") or "").strip()
    return username or None


def _apply_suite_handoff(request) -> None:
    username = _suite_session_user(request)
    if not username:
        return

    account, _errors = Account.authenticate_suite_handoff(
        username,
        ip=_client_ip(request),
        session=None,
    )
    if not account:
        return

    request.session["webclient_authenticated_uid"] = account.id
    request.session.save()


def webclient(request):
    """Render the webclient and auto-login trusted suite superusers."""

    if not settings.WEBCLIENT_ENABLED:
        raise Http404

    _apply_suite_handoff(request)
    if not request.session.session_key:
        request.session.save()

    return render(request, "webclient.html", {"browser_sessid": request.session.session_key})
