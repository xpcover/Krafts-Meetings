"""Workflow API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar_clients import CalendarClient
from app.crypto import TokenCipher
from app.models import IntegrationAccount, WorkflowCalendarEvent
from app.oauth import authorization_url, exchange_code, parse_state, token_expiry
from app.schemas import CalendarProvider, MeetingCreate, MeetingResponse, OAuthCallbackResponse, OAuthStartResponse
from app.vexa_client import VexaClient

router = APIRouter(prefix="/workflow", tags=["Workflow"])


async def get_db(request: Request):
    async for db in request.app.state.database.session():
        yield db


def get_calendar_client() -> CalendarClient:
    return CalendarClient()


def get_vexa_client(request: Request) -> VexaClient | None:
    settings = request.app.state.settings
    if not settings.vexa_api_key:
        return None
    return VexaClient(settings.vexa_api_url, settings.vexa_api_key)


def _vexa_platform(provider: CalendarProvider) -> str:
    if provider == CalendarProvider.GOOGLE:
        return "google_meet"
    return "teams"


def _oauth_configured(settings, provider: CalendarProvider) -> bool:
    if provider == CalendarProvider.GOOGLE:
        return bool(settings.google_client_id and settings.google_client_secret)
    return bool(settings.microsoft_client_id and settings.microsoft_client_secret)


def _serialize_event(event: WorkflowCalendarEvent) -> MeetingResponse:
    return MeetingResponse(
        id=event.id,
        user_id=event.user_id,
        provider=CalendarProvider(event.provider),
        provider_event_id=event.provider_event_id,
        title=event.title,
        start_time=event.start_time,
        end_time=event.end_time,
        timezone=event.timezone,
        meeting_url=event.meeting_url,
        conference_provider=event.conference_provider,
        vexa_platform=event.vexa_platform,
        vexa_meeting_id=event.vexa_meeting_id,
        attendees=event.attendees or [],
        agenda=event.agenda,
        auto_join=event.auto_join,
        send_invites=event.send_invites,
        sync_status=event.sync_status,
    )


@router.post("/meetings", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    req: MeetingCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    calendar_client: Annotated[CalendarClient, Depends(get_calendar_client)],
    vexa_client: Annotated[VexaClient | None, Depends(get_vexa_client)],
):
    settings = request.app.state.settings
    if not settings.encryption_key:
        raise HTTPException(status_code=503, detail="WORKFLOW_ENCRYPTION_KEY is not configured")

    result = await db.execute(
        select(IntegrationAccount)
        .where(
            IntegrationAccount.user_id == req.user_id,
            IntegrationAccount.provider == req.provider.value,
            IntegrationAccount.status == "connected",
        )
        .order_by(IntegrationAccount.updated_at.desc())
    )
    account = result.scalars().first()
    if not account or not account.encrypted_access_token:
        raise HTTPException(status_code=404, detail=f"No connected {req.provider.value} account for user")

    access_token = TokenCipher(settings.encryption_key).decrypt(account.encrypted_access_token)
    provider_event = await calendar_client.create_event(req.provider, access_token, req)
    vexa_platform = _vexa_platform(req.provider)
    sync_status = "created"
    vexa_meeting_id = None
    metadata = {"provider_response": provider_event.raw}
    if req.auto_join and provider_event.meeting_url:
        if vexa_client is None:
            sync_status = "created_bot_not_configured"
        else:
            scheduled_bot = await vexa_client.schedule_bot(
                vexa_platform,
                provider_event.meeting_url,
                f"Krafts - {req.title}",
            )
            vexa_meeting_id = scheduled_bot.native_meeting_id
            sync_status = "bot_scheduled"
            metadata["vexa_bot"] = scheduled_bot.response

    values = {
        "user_id": req.user_id,
        "integration_account_id": account.id,
        "provider": req.provider.value,
        "provider_event_id": provider_event.provider_event_id,
        "title": req.title,
        "start_time": req.start_time,
        "end_time": req.end_time,
        "timezone": req.timezone,
        "meeting_url": provider_event.meeting_url,
        "conference_provider": provider_event.conference_provider,
        "vexa_platform": vexa_platform,
        "vexa_meeting_id": vexa_meeting_id,
        "attendees": [attendee.model_dump(mode="json") for attendee in req.attendees],
        "agenda": req.agenda,
        "auto_join": req.auto_join,
        "send_invites": req.send_invites,
        "sync_status": sync_status,
        "metadata": metadata,
    }
    stmt = (
        pg_insert(WorkflowCalendarEvent)
        .values(**values)
        .on_conflict_do_update(
            constraint="uq_workflow_calendar_event_provider",
            set_=values,
        )
        .returning(WorkflowCalendarEvent)
    )
    event = (await db.execute(stmt)).scalar_one()
    await db.commit()
    return _serialize_event(event)


@router.get("/meetings", response_model=list[MeetingResponse])
async def list_meetings(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(WorkflowCalendarEvent)
        .where(WorkflowCalendarEvent.user_id == user_id)
        .order_by(WorkflowCalendarEvent.start_time.desc())
    )
    return [_serialize_event(event) for event in result.scalars().all()]


@router.get("/oauth/{provider}/start", response_model=OAuthStartResponse)
async def oauth_start(provider: CalendarProvider, user_id: int, request: Request):
    settings = request.app.state.settings
    if not settings.oauth_state_secret:
        raise HTTPException(status_code=503, detail="WORKFLOW_OAUTH_STATE_SECRET is not configured")
    if not _oauth_configured(settings, provider):
        raise HTTPException(status_code=503, detail=f"{provider.value} OAuth client is not configured")
    return OAuthStartResponse(
        provider=provider,
        authorization_url=authorization_url(settings, provider, user_id),
    )


@router.get("/oauth/{provider}/callback", response_model=OAuthCallbackResponse)
async def oauth_callback(
    provider: CalendarProvider,
    code: str,
    state: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    settings = request.app.state.settings
    if not settings.encryption_key:
        raise HTTPException(status_code=503, detail="WORKFLOW_ENCRYPTION_KEY is not configured")
    try:
        state_data = parse_state(settings.oauth_state_secret, state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if state_data["provider"] != provider.value:
        raise HTTPException(status_code=400, detail="OAuth state provider mismatch")

    token_response = await exchange_code(settings, provider, code, state_data["redirect_uri"])
    access_token = token_response.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="OAuth token response did not include access_token")

    cipher = TokenCipher(settings.encryption_key)
    values = {
        "user_id": int(state_data["user_id"]),
        "provider": provider.value,
        "provider_account_id": token_response.get("sub") or "",
        "encrypted_access_token": cipher.encrypt(access_token),
        "token_expires_at": token_expiry(token_response),
        "scopes": (token_response.get("scope") or "").split(),
        "status": "connected",
        "metadata": {"token_type": token_response.get("token_type")},
    }
    refresh_token = token_response.get("refresh_token")
    if refresh_token:
        values["encrypted_refresh_token"] = cipher.encrypt(refresh_token)

    set_values = {
        "encrypted_access_token": values["encrypted_access_token"],
        "token_expires_at": values["token_expires_at"],
        "scopes": values["scopes"],
        "status": "connected",
        "metadata": values["metadata"],
    }
    if "encrypted_refresh_token" in values:
        set_values["encrypted_refresh_token"] = values["encrypted_refresh_token"]

    stmt = (
        pg_insert(IntegrationAccount)
        .values(**values)
        .on_conflict_do_update(
            constraint="uq_integration_account_provider",
            set_=set_values,
        )
    )
    await db.execute(stmt)
    await db.commit()
    return OAuthCallbackResponse(provider=provider, user_id=int(state_data["user_id"]), status="connected")
