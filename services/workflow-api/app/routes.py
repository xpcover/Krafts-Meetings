"""Workflow API routes."""

from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar_clients import CalendarClient
from app.crypto import TokenCipher
from app.llm_client import OpenAIExtractionClient
from app.models import EmailDelivery, IntegrationAccount, MeetingOutput, WorkflowCalendarEvent, WorkflowTask
from app.oauth import authorization_url, exchange_code, parse_state, token_expiry
from app.schemas import (
    CalendarProvider,
    MailTestResponse,
    MeetingCreate,
    MeetingResponse,
    OAuthCallbackResponse,
    OAuthStartResponse,
)
from app.smtp_client import SmtpClient, SmtpDeliveryError
from app.vexa_client import VexaClient
from app.webhook_security import verify_vexa_signature

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


def get_extraction_client(request: Request) -> OpenAIExtractionClient | None:
    settings = request.app.state.settings
    if settings.llm_provider != "openai" or not settings.openai_api_key:
        return None
    return OpenAIExtractionClient(settings)


def get_smtp_client(request: Request) -> SmtpClient:
    return SmtpClient(request.app.state.settings)


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


def _attendee_emails(event: WorkflowCalendarEvent) -> list[str]:
    emails = []
    for attendee in event.attendees or []:
        email = attendee.get("email") if isinstance(attendee, dict) else None
        if email:
            emails.append(email)
    return list(dict.fromkeys(emails))


def _summary_email_body(event: WorkflowCalendarEvent, summary: str | None, decisions: list[str], task_count: int) -> str:
    decisions_text = "\n".join(f"- {decision}" for decision in decisions) or "- None recorded"
    return (
        f"Meeting: {event.title}\n\n"
        f"Summary:\n{summary or 'No summary generated.'}\n\n"
        f"Decisions:\n{decisions_text}\n\n"
        f"Action items extracted: {task_count}\n"
    )


def _task_email_body(event: WorkflowCalendarEvent, task: WorkflowTask) -> str:
    due_text = task.due_at.isoformat() if task.due_at else "No due date"
    return (
        f"Meeting: {event.title}\n\n"
        f"Action item:\n{task.title}\n\n"
        f"Description:\n{task.description or 'No additional description.'}\n\n"
        f"Due: {due_text}\n"
        f"Confidence: {task.confidence if task.confidence is not None else 'unknown'}\n"
    )


def _delivery_failure_status(exc: SmtpDeliveryError) -> str:
    if exc.retryable is True:
        return "retryable_failed"
    if exc.retryable is False:
        return "permanent_failed"
    return "failed"


async def _log_email_delivery(
    db: AsyncSession,
    event: WorkflowCalendarEvent,
    recipient_email: str,
    template: str,
    status_value: str,
    smtp_response: str | None = None,
    error_message: str | None = None,
    payload_ref: dict | None = None,
    attempts: int = 0,
):
    db.add(EmailDelivery(
        calendar_event_id=event.id,
        recipient_email=recipient_email,
        template=template,
        status=status_value,
        attempts=attempts,
        last_attempt_at=datetime.now(UTC) if attempts else None,
        sent_at=datetime.now(UTC) if status_value == "sent" else None,
        smtp_response=smtp_response,
        error_message=error_message,
        payload_ref=payload_ref or {},
    ))


async def _send_post_meeting_emails(
    db: AsyncSession,
    event: WorkflowCalendarEvent,
    smtp_client: SmtpClient,
    summary: str | None,
    decisions: list[str],
    inserted_tasks: list[WorkflowTask],
):
    existing_delivery = (
        await db.execute(select(EmailDelivery.id).where(EmailDelivery.calendar_event_id == event.id).limit(1))
    ).first()
    if existing_delivery:
        return

    recipients = _attendee_emails(event)
    if not recipients and not inserted_tasks:
        return

    if not smtp_client.configured:
        for recipient in recipients:
            await _log_email_delivery(
                db,
                event,
                recipient,
                "meeting_summary",
                "smtp_not_configured",
                error_message="SMTP_HOST and SMTP_FROM_EMAIL are required",
                payload_ref={"task_count": len(inserted_tasks)},
            )
        for task in inserted_tasks:
            if task.owner_email:
                await _log_email_delivery(
                    db,
                    event,
                    task.owner_email,
                    "task_assignment",
                    "smtp_not_configured",
                    error_message="SMTP_HOST and SMTP_FROM_EMAIL are required",
                    payload_ref={"task_title": task.title},
                )
        return

    if recipients:
        body = _summary_email_body(event, summary, decisions, len(inserted_tasks))
        for recipient in recipients:
            try:
                result = await smtp_client.send([recipient], f"Meeting summary: {event.title}", body)
                await _log_email_delivery(
                    db,
                    event,
                    recipient,
                    "meeting_summary",
                    result.status,
                    smtp_response=result.response,
                    payload_ref={"task_count": len(inserted_tasks)},
                    attempts=1,
                )
            except SmtpDeliveryError as exc:
                await _log_email_delivery(
                    db,
                    event,
                    recipient,
                    "meeting_summary",
                    _delivery_failure_status(exc),
                    error_message=str(exc),
                    payload_ref={"task_count": len(inserted_tasks)},
                    attempts=1,
                )

    for task in inserted_tasks:
        if not task.owner_email:
            continue
        try:
            result = await smtp_client.send(
                [task.owner_email],
                f"Action item: {task.title}",
                _task_email_body(event, task),
            )
            await _log_email_delivery(
                db,
                event,
                task.owner_email,
                "task_assignment",
                result.status,
                smtp_response=result.response,
                payload_ref={"task_title": task.title},
                attempts=1,
            )
        except SmtpDeliveryError as exc:
            await _log_email_delivery(
                db,
                event,
                task.owner_email,
                "task_assignment",
                _delivery_failure_status(exc),
                error_message=str(exc),
                payload_ref={"task_title": task.title},
                attempts=1,
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


@router.post("/mail/test", response_model=MailTestResponse)
async def test_mail(smtp_client: Annotated[SmtpClient, Depends(get_smtp_client)]):
    try:
        result = await smtp_client.verify()
    except SmtpDeliveryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return MailTestResponse(status=result.status, smtp_response=result.response)


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


@router.post("/webhooks/vexa/meeting-completed")
async def vexa_meeting_completed(
    payload: dict,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    vexa_client: Annotated[VexaClient | None, Depends(get_vexa_client)],
    extraction_client: Annotated[OpenAIExtractionClient | None, Depends(get_extraction_client)],
    smtp_client: Annotated[SmtpClient, Depends(get_smtp_client)],
):
    settings = request.app.state.settings
    if not settings.vexa_webhook_secret:
        raise HTTPException(status_code=503, detail="WORKFLOW_VEXA_WEBHOOK_SECRET is not configured")

    body = await request.body()
    if not verify_vexa_signature(
        body,
        settings.vexa_webhook_secret,
        request.headers.get("x-webhook-signature"),
        request.headers.get("x-webhook-timestamp"),
    ):
        raise HTTPException(status_code=401, detail="Invalid Vexa webhook signature")

    if payload.get("event_type") != "meeting.completed":
        raise HTTPException(status_code=400, detail="Unsupported Vexa webhook event")
    meeting = (payload.get("data") or {}).get("meeting") or {}
    platform = meeting.get("platform")
    native_id = meeting.get("native_meeting_id")
    if not platform or not native_id:
        raise HTTPException(status_code=400, detail="Missing meeting platform/native_meeting_id")
    if vexa_client is None:
        raise HTTPException(status_code=503, detail="VEXA_API_KEY is not configured")

    event = (
        await db.execute(
            select(WorkflowCalendarEvent).where(
                WorkflowCalendarEvent.vexa_platform == platform,
                WorkflowCalendarEvent.vexa_meeting_id == native_id,
            )
        )
    ).scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Workflow calendar event not found for Vexa meeting")

    transcript = await vexa_client.get_transcript(platform, native_id)
    segments = transcript.get("segments") or []
    transcript_ref = {
        "source": "vexa",
        "platform": platform,
        "native_meeting_id": native_id,
        "segment_count": len(segments),
    }
    extraction = None
    generation_status = "transcript_fetched"
    error_message = None
    if extraction_client is None:
        generation_status = "llm_not_configured"
    else:
        try:
            extraction = await extraction_client.extract(transcript)
            generation_status = "extracted"
        except (ValueError, httpx.HTTPError) as exc:
            generation_status = "extraction_failed"
            error_message = str(exc)
    generated_at = datetime.now(UTC) if extraction else None

    stmt = (
        pg_insert(MeetingOutput)
        .values(
            calendar_event_id=event.id,
            vexa_platform=platform,
            vexa_meeting_id=native_id,
            transcript_ref=transcript_ref,
            summary=extraction.summary if extraction else None,
            decisions=extraction.decisions if extraction else [],
            generation_status=generation_status,
            generated_at=generated_at,
            error_message=error_message,
        )
        .on_conflict_do_update(
            constraint="uq_meeting_outputs_calendar_event",
            set_={
                "vexa_platform": platform,
                "vexa_meeting_id": native_id,
                "transcript_ref": transcript_ref,
                "summary": extraction.summary if extraction else None,
                "decisions": extraction.decisions if extraction else [],
                "generation_status": generation_status,
                "generated_at": generated_at,
                "error_message": error_message,
            },
        )
    )
    await db.execute(stmt)
    inserted_tasks = []
    if extraction:
        # Idempotent enough for v1 webhook retries: replace tasks for this event with
        # the latest extraction output before inserting the current set.
        existing_tasks = (
            await db.execute(select(WorkflowTask).where(WorkflowTask.calendar_event_id == event.id))
        ).scalars().all()
        for task in existing_tasks:
            await db.delete(task)
        for task in extraction.tasks:
            workflow_task = WorkflowTask(
                calendar_event_id=event.id,
                owner_email=str(task.owner_email) if task.owner_email else None,
                title=task.title,
                description=task.description,
                due_at=task.due_at,
                status="open",
                confidence=task.confidence,
                source={"provider": "openai", "model": settings.openai_model},
            )
            db.add(workflow_task)
            inserted_tasks.append(workflow_task)
        await _send_post_meeting_emails(
            db,
            event,
            smtp_client,
            extraction.summary,
            extraction.decisions,
            inserted_tasks,
        )

    event.sync_status = generation_status
    await db.commit()
    return {
        "status": generation_status,
        "calendar_event_id": event.id,
        "segment_count": len(segments),
        "task_count": len(extraction.tasks) if extraction else 0,
    }
