"""OAuth helpers for Google Calendar and Microsoft Graph."""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.schemas import CalendarProvider

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
MICROSOFT_AUTH_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
MICROSOFT_SCOPES = ["offline_access", "User.Read", "Calendars.ReadWrite"]


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _unb64url(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(payload: str, secret: str) -> str:
    return _b64url(hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest())


def make_state(secret: str, user_id: int, provider: CalendarProvider, redirect_uri: str, ttl_seconds: int = 600) -> str:
    if not secret:
        raise ValueError("WORKFLOW_OAUTH_STATE_SECRET is required")
    payload = _b64url(json.dumps({
        "user_id": user_id,
        "provider": provider.value,
        "redirect_uri": redirect_uri,
        "exp": int(time.time()) + ttl_seconds,
    }, separators=(",", ":")).encode("utf-8"))
    return f"{payload}.{_sign(payload, secret)}"


def parse_state(secret: str, state: str) -> dict[str, Any]:
    if not secret:
        raise ValueError("WORKFLOW_OAUTH_STATE_SECRET is required")
    try:
        payload, signature = state.split(".", 1)
    except ValueError as exc:
        raise ValueError("Invalid OAuth state") from exc
    expected = _sign(payload, secret)
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid OAuth state signature")
    data = json.loads(_unb64url(payload))
    if int(data.get("exp", 0)) < int(time.time()):
        raise ValueError("OAuth state expired")
    return data


def callback_url(settings: Settings, provider: CalendarProvider) -> str:
    return f"{settings.public_base_url}/workflow/oauth/{provider.value}/callback"


def authorization_url(settings: Settings, provider: CalendarProvider, user_id: int) -> str:
    redirect_uri = callback_url(settings, provider)
    state = make_state(settings.oauth_state_secret, user_id, provider, redirect_uri)
    if provider == CalendarProvider.GOOGLE:
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_SCOPES),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    params = {
        "client_id": settings.microsoft_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "response_mode": "query",
        "scope": " ".join(MICROSOFT_SCOPES),
        "state": state,
    }
    return f"{MICROSOFT_AUTH_URL_TEMPLATE.format(tenant=settings.microsoft_tenant_id)}?{urlencode(params)}"


async def exchange_code(settings: Settings, provider: CalendarProvider, code: str, redirect_uri: str, http_client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    if provider == CalendarProvider.GOOGLE:
        url = GOOGLE_TOKEN_URL
        data = {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
    else:
        url = MICROSOFT_TOKEN_URL_TEMPLATE.format(tenant=settings.microsoft_tenant_id)
        data = {
            "client_id": settings.microsoft_client_id,
            "client_secret": settings.microsoft_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(MICROSOFT_SCOPES),
        }

    response = await _post_form(url, data, http_client)
    return response.json()


async def refresh_token(settings: Settings, provider: CalendarProvider, refresh_token_value: str, http_client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    if provider == CalendarProvider.GOOGLE:
        url = GOOGLE_TOKEN_URL
        data = {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token_value,
        }
    else:
        url = MICROSOFT_TOKEN_URL_TEMPLATE.format(tenant=settings.microsoft_tenant_id)
        data = {
            "client_id": settings.microsoft_client_id,
            "client_secret": settings.microsoft_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token_value,
            "scope": " ".join(MICROSOFT_SCOPES),
        }

    response = await _post_form(url, data, http_client)
    return response.json()


def token_expiry(token_response: dict[str, Any]) -> datetime | None:
    expires_in = token_response.get("expires_in")
    if not expires_in:
        return None
    return datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))


async def _post_form(url: str, data: dict[str, str], http_client: httpx.AsyncClient | None = None) -> httpx.Response:
    if http_client is not None:
        response = await http_client.post(url, data=data)
    else:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=data)
    response.raise_for_status()
    return response
