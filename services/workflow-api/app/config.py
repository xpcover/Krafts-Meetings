"""Environment-backed configuration for workflow-api."""

import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    service_name: str
    log_level: str
    init_db_on_startup: bool
    db_host: Optional[str]
    db_port: Optional[str]
    db_name: Optional[str]
    db_user: Optional[str]
    db_password: Optional[str]
    db_ssl_mode: str
    vexa_api_url: str
    vexa_api_key: str
    encryption_key: str
    google_client_id: str
    google_client_secret: str
    microsoft_client_id: str
    microsoft_client_secret: str
    microsoft_tenant_id: str
    local_llm_url: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    smtp_tls_mode: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            service_name=os.getenv("WORKFLOW_SERVICE_NAME", "workflow-api"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            init_db_on_startup=_bool_env("WORKFLOW_INIT_DB_ON_STARTUP", False),
            db_host=os.getenv("DB_HOST"),
            db_port=os.getenv("DB_PORT", "5432"),
            db_name=os.getenv("DB_NAME"),
            db_user=os.getenv("DB_USER"),
            db_password=os.getenv("DB_PASSWORD"),
            db_ssl_mode=os.getenv("DB_SSL_MODE", "prefer"),
            vexa_api_url=os.getenv("VEXA_API_URL", "http://api-gateway:8000").rstrip("/"),
            vexa_api_key=os.getenv("VEXA_API_KEY", ""),
            encryption_key=os.getenv("WORKFLOW_ENCRYPTION_KEY", ""),
            google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
            google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
            microsoft_client_id=os.getenv("MICROSOFT_CLIENT_ID", ""),
            microsoft_client_secret=os.getenv("MICROSOFT_CLIENT_SECRET", ""),
            microsoft_tenant_id=os.getenv("MICROSOFT_TENANT_ID", "common"),
            local_llm_url=os.getenv("LOCAL_LLM_URL", "").rstrip("/"),
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            smtp_from_email=os.getenv("SMTP_FROM_EMAIL", ""),
            smtp_tls_mode=os.getenv("SMTP_TLS_MODE", "starttls"),
        )

    @property
    def missing_db_vars(self) -> list[str]:
        required = {
            "DB_HOST": self.db_host,
            "DB_PORT": self.db_port,
            "DB_NAME": self.db_name,
            "DB_USER": self.db_user,
            "DB_PASSWORD": self.db_password,
        }
        return [name for name, value in required.items() if not value]

    @property
    def database_configured(self) -> bool:
        return not self.missing_db_vars

    @property
    def database_url(self) -> str:
        missing = self.missing_db_vars
        if missing:
            raise ValueError(f"Missing required database environment variables: {', '.join(missing)}")

        user = quote_plus(self.db_user or "")
        password = quote_plus(self.db_password or "")
        host = self.db_host or ""
        port = self.db_port or "5432"
        name = self.db_name or ""
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"
