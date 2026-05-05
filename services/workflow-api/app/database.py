"""Database connection helpers for workflow-api."""

import ssl
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings


def _asyncpg_ssl(settings: Settings):
    mode = (settings.db_ssl_mode or "").lower()
    if mode in {"require", "prefer"}:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context
    if mode in {"verify-ca", "verify-full"}:
        return True
    if mode == "disable":
        return False
    return None


def create_engine(settings: Settings) -> AsyncEngine:
    connect_args = {"statement_cache_size": 0}
    ssl_value = _asyncpg_ssl(settings)
    if ssl_value is not None:
        connect_args["ssl"] = ssl_value

    return create_async_engine(
        settings.database_url,
        connect_args=connect_args,
        pool_size=5,
        max_overflow=5,
        pool_timeout=10,
        pool_recycle=1800,
        pool_pre_ping=True,
    )


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[sessionmaker] = None

    def configure(self) -> None:
        if self.engine is not None:
            return
        self.engine = create_engine(self.settings)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def ping(self) -> None:
        self.configure()
        assert self.engine is not None
        async with self.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    async def close(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None

    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        self.configure()
        assert self.session_factory is not None
        async with self.session_factory() as db:
            yield db
