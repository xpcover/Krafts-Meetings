import pytest

from app.config import Settings


def test_database_configured_false_when_required_vars_missing():
    settings = Settings(
        service_name="workflow-api",
        log_level="INFO",
        init_db_on_startup=False,
        db_host=None,
        db_port="5432",
        db_name=None,
        db_user=None,
        db_password=None,
        db_ssl_mode="disable",
        vexa_api_url="http://api-gateway:8000",
        vexa_api_key="",
        vexa_webhook_secret="",
        edge_shared_secret="",
        encryption_key="",
        oauth_state_secret="state-secret",
        public_base_url="http://localhost:8060",
        google_client_id="",
        google_client_secret="",
        microsoft_client_id="",
        microsoft_client_secret="",
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

    assert not settings.database_configured
    assert settings.missing_db_vars == ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    with pytest.raises(ValueError, match="DB_HOST"):
        _ = settings.database_url


def test_database_url_escapes_credentials():
    settings = Settings(
        service_name="workflow-api",
        log_level="INFO",
        init_db_on_startup=False,
        db_host="postgres",
        db_port="5432",
        db_name="vexa",
        db_user="user@example.com",
        db_password="p@ss word",
        db_ssl_mode="disable",
        vexa_api_url="http://api-gateway:8000",
        vexa_api_key="",
        vexa_webhook_secret="",
        edge_shared_secret="",
        encryption_key="",
        oauth_state_secret="state-secret",
        public_base_url="http://localhost:8060",
        google_client_id="",
        google_client_secret="",
        microsoft_client_id="",
        microsoft_client_secret="",
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

    assert settings.database_configured
    assert settings.database_url == "postgresql+asyncpg://user%40example.com:p%40ss+word@postgres:5432/vexa"
