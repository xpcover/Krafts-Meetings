import asyncio
import smtplib

import pytest

from app.config import Settings
from app.smtp_client import SmtpClient, SmtpDeliveryError


def _settings(**overrides) -> Settings:
    values = {
        "service_name": "workflow-api",
        "log_level": "INFO",
        "init_db_on_startup": False,
        "db_host": "postgres",
        "db_port": "5432",
        "db_name": "vexa",
        "db_user": "postgres",
        "db_password": "postgres",
        "db_ssl_mode": "disable",
        "vexa_api_url": "http://api-gateway:8000",
        "vexa_api_key": "",
        "vexa_webhook_secret": "",
        "encryption_key": "",
        "oauth_state_secret": "",
        "public_base_url": "http://localhost:8060",
        "google_client_id": "",
        "google_client_secret": "",
        "microsoft_client_id": "",
        "microsoft_client_secret": "",
        "microsoft_tenant_id": "common",
        "llm_provider": "openai",
        "openai_api_key": "",
        "openai_model": "gpt-5-nano",
        "openai_base_url": "https://api.openai.com/v1",
        "local_llm_url": "",
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_username": "user",
        "smtp_password": "pass",
        "smtp_from_email": "meetings@example.com",
        "smtp_tls_mode": "starttls",
    }
    values.update(overrides)
    return Settings(**values)


class FakeSMTP:
    sent_messages = []
    logins = []
    started_tls = False

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def ehlo(self):
        return (250, b"ok")

    def starttls(self):
        FakeSMTP.started_tls = True
        return (220, b"ready")

    def login(self, username, password):
        FakeSMTP.logins.append((username, password))
        return (235, b"authenticated")

    def noop(self):
        return (250, b"ok")

    def send_message(self, message):
        FakeSMTP.sent_messages.append(message)
        return {}


def test_smtp_verify_connects_and_authenticates(monkeypatch):
    FakeSMTP.logins = []
    FakeSMTP.started_tls = False
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)

    result = asyncio.run(SmtpClient(_settings()).verify())

    assert result.status == "verified"
    assert FakeSMTP.started_tls is True
    assert FakeSMTP.logins == [("user", "pass")]


def test_smtp_send_builds_email_message(monkeypatch):
    FakeSMTP.sent_messages = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)

    result = asyncio.run(SmtpClient(_settings()).send(["a@example.com"], "Subject", "Body"))

    assert result.status == "sent"
    message = FakeSMTP.sent_messages[0]
    assert message["From"] == "meetings@example.com"
    assert message["To"] == "a@example.com"
    assert message["Subject"] == "Subject"


def test_smtp_verify_requires_host_and_from_email():
    with pytest.raises(SmtpDeliveryError, match="SMTP_HOST and SMTP_FROM_EMAIL"):
        asyncio.run(SmtpClient(_settings(smtp_host="")).verify())


def test_smtp_send_rejects_refused_recipient(monkeypatch):
    class RefusingSMTP(FakeSMTP):
        def send_message(self, message):
            return {"a@example.com": (550, b"rejected")}

    monkeypatch.setattr(smtplib, "SMTP", RefusingSMTP)

    with pytest.raises(SmtpDeliveryError, match="refused recipients") as exc_info:
        asyncio.run(SmtpClient(_settings()).send(["a@example.com"], "Subject", "Body"))
    assert exc_info.value.retryable is False


def test_smtp_send_classifies_temporary_refusal(monkeypatch):
    class RefusingSMTP(FakeSMTP):
        def send_message(self, message):
            return {"a@example.com": (451, b"try later")}

    monkeypatch.setattr(smtplib, "SMTP", RefusingSMTP)

    with pytest.raises(SmtpDeliveryError, match="refused recipients") as exc_info:
        asyncio.run(SmtpClient(_settings()).send(["a@example.com"], "Subject", "Body"))
    assert exc_info.value.retryable is True
