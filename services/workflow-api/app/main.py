"""Workflow API — calendar, task, and email orchestration for Krafts Meetings."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings
from app.database import Database

settings = Settings.from_env()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("workflow-api")
database = Database(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = settings
    app.state.database = database
    if settings.init_db_on_startup:
        logger.info("Initializing workflow-api database schema")
        await database.init_schema()
    try:
        yield
    finally:
        await database.close()


_VEXA_ENV = __import__("os").getenv("VEXA_ENV", "development")
_PUBLIC_DOCS = _VEXA_ENV != "production"

app = FastAPI(
    title="Krafts Meetings Workflow API",
    description="Calendar, task extraction, and email workflow service for Vexa.",
    docs_url="/docs" if _PUBLIC_DOCS else None,
    redoc_url="/redoc" if _PUBLIC_DOCS else None,
    openapi_url="/openapi.json" if _PUBLIC_DOCS else None,
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.service_name,
        "database_configured": settings.database_configured,
        "vexa_api_url": settings.vexa_api_url,
    }
