import asyncio
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.config import Settings
from app.oauth import GOOGLE_TOKEN_URL, authorization_url, exchange_code, make_state, parse_state
from app.schemas import CalendarProvider


def _settings() -> Settings:
    return Settings(
        service_name="workflow-api",
        log_level="INFO",
        init_db_on_startup=False,
        db_host="postgres",
        db_port="5432",
        db_name="vexa",
        db_user="postgres",
        db_password="postgres",
        db_ssl_mode="disable",
        vexa_api_url="http://api-gateway:8000",
        vexa_api_key="",
        vexa_webhook_secret="",
        edge_shared_secret="",
        encryption_key="fernet-key-placeholder",
        oauth_state_secret="state-secret",
        public_base_url="https://meetings.example.com",
        google_client_id="google-client",
        google_client_secret="google-secret",
        microsoft_client_id="ms-client",
        microsoft_client_secret="ms-secret",
        microsoft_tenant_id="common",
        llm_provider="openai",
        openai_api_key="",
        openai_model="gpt-5-nano",
        openai_base_url="https://api.openai.com/v1",
        local_llm_url="",
        smtp_host="",
        smtp_port=587,
        smtp_username="",
        smtp_password="",
        smtp_from_email="",
        smtp_tls_mode="starttls",
    )


def test_state_round_trip_and_tamper_rejection():
    state = make_state("state-secret", 42, CalendarProvider.GOOGLE, "https://example.com/callback")
    parsed = parse_state("state-secret", state)

    assert parsed["user_id"] == 42
    assert parsed["provider"] == "google"
    assert parsed["redirect_uri"] == "https://example.com/callback"

    with pytest.raises(ValueError, match="signature"):
        parse_state("state-secret", state + "tampered")


def test_google_authorization_url_requests_offline_calendar_access():
    url = authorization_url(_settings(), CalendarProvider.GOOGLE, 7)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.netloc == "accounts.google.com"
    assert query["client_id"] == ["google-client"]
    assert query["access_type"] == ["offline"]
    assert query["include_granted_scopes"] == ["true"]
    assert query["scope"] == ["https://www.googleapis.com/auth/calendar.events"]
    assert query["redirect_uri"] == ["https://meetings.example.com/workflow/oauth/google/callback"]


def test_microsoft_authorization_url_requests_calendar_and_refresh_scopes():
    url = authorization_url(_settings(), CalendarProvider.OUTLOOK, 7)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.netloc == "login.microsoftonline.com"
    assert parsed.path == "/common/oauth2/v2.0/authorize"
    assert query["client_id"] == ["ms-client"]
    assert query["scope"] == ["offline_access User.Read Calendars.ReadWrite"]
    assert query["redirect_uri"] == ["https://meetings.example.com/workflow/oauth/outlook/callback"]


def test_exchange_google_code_posts_to_token_endpoint():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["form"] = dict(parse_qs(request.content.decode("utf-8")))
        return httpx.Response(200, json={"access_token": "access", "refresh_token": "refresh"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await exchange_code(_settings(), CalendarProvider.GOOGLE, "auth-code", "https://cb", client)

    token_response = asyncio.run(run())

    assert captured["url"] == GOOGLE_TOKEN_URL
    assert captured["form"]["client_id"] == ["google-client"]
    assert captured["form"]["client_secret"] == ["google-secret"]
    assert captured["form"]["code"] == ["auth-code"]
    assert captured["form"]["grant_type"] == ["authorization_code"]
    assert token_response["access_token"] == "access"
