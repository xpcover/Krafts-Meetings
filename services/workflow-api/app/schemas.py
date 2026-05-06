"""Pydantic schemas for workflow-api."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class CalendarProvider(str, Enum):
    GOOGLE = "google"
    OUTLOOK = "outlook"


class Attendee(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class MeetingCreate(BaseModel):
    user_id: int = Field(..., ge=1)
    provider: CalendarProvider
    title: str = Field(..., min_length=1, max_length=300)
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"
    attendees: list[Attendee] = Field(default_factory=list)
    agenda: Optional[str] = None
    auto_join: bool = True
    send_invites: bool = True


class MeetingResponse(BaseModel):
    id: int
    user_id: int
    provider: CalendarProvider
    provider_event_id: str
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    timezone: str
    meeting_url: Optional[str] = None
    conference_provider: Optional[str] = None
    vexa_platform: Optional[str] = None
    vexa_meeting_id: Optional[str] = None
    attendees: list[dict[str, Any]]
    agenda: Optional[str] = None
    auto_join: bool
    send_invites: bool
    sync_status: str

    model_config = {"from_attributes": True}


class ProviderEvent(BaseModel):
    provider_event_id: str
    meeting_url: Optional[str] = None
    conference_provider: Optional[str] = None
    raw: dict[str, Any] = Field(default_factory=dict)


class OAuthStartResponse(BaseModel):
    provider: CalendarProvider
    authorization_url: str


class OAuthCallbackResponse(BaseModel):
    provider: CalendarProvider
    user_id: int
    status: str


class ExtractedTask(BaseModel):
    title: str = Field(..., min_length=1)
    owner_email: Optional[EmailStr] = None
    due_at: Optional[datetime] = None
    description: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class MeetingExtraction(BaseModel):
    summary: str = ""
    decisions: list[str] = Field(default_factory=list)
    tasks: list[ExtractedTask] = Field(default_factory=list)


class MailTestResponse(BaseModel):
    status: str
    smtp_response: str
