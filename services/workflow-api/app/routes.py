"""Workflow API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar_clients import CalendarClient
from app.crypto import TokenCipher
from app.models import IntegrationAccount, WorkflowCalendarEvent
from app.schemas import CalendarProvider, MeetingCreate, MeetingResponse

router = APIRouter(prefix="/workflow", tags=["Workflow"])


async def get_db(request: Request):
    async for db in request.app.state.database.session():
        yield db


def get_calendar_client() -> CalendarClient:
    return CalendarClient()


def _vexa_platform(provider: CalendarProvider) -> str:
    if provider == CalendarProvider.GOOGLE:
        return "google_meet"
    return "teams"


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
        "vexa_platform": _vexa_platform(req.provider),
        "attendees": [attendee.model_dump() for attendee in req.attendees],
        "agenda": req.agenda,
        "auto_join": req.auto_join,
        "send_invites": req.send_invites,
        "sync_status": "created",
        "metadata": {"provider_response": provider_event.raw},
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
