"""SQLAlchemy models for Krafts Meetings workflow state."""

import sqlalchemy
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func, text

Base = declarative_base()


class IntegrationAccount(Base):
    __tablename__ = "integration_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    provider_account_id = Column(Text, nullable=False, default="", server_default="")
    encrypted_access_token = Column(Text, nullable=True)
    encrypted_refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    status = Column(String(50), nullable=False, default="connected", server_default="connected")
    extra_metadata = Column("metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    calendar_events = relationship("WorkflowCalendarEvent", back_populates="integration_account")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "provider_account_id", name="uq_integration_account_provider"),
        Index("ix_integration_accounts_user_provider", "user_id", "provider"),
    )


class WorkflowCalendarEvent(Base):
    # Vexa already owns `calendar_events`, so workflow state uses a namespaced table.
    __tablename__ = "workflow_calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    integration_account_id = Column(Integer, ForeignKey("integration_accounts.id"), nullable=True, index=True)
    provider = Column(String(50), nullable=False)
    provider_event_id = Column(Text, nullable=False)
    title = Column(Text, nullable=False, default="", server_default="")
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    timezone = Column(Text, nullable=False, default="UTC", server_default="UTC")
    meeting_url = Column(Text, nullable=True)
    conference_provider = Column(String(50), nullable=True)
    vexa_platform = Column(String(50), nullable=True)
    vexa_meeting_id = Column(Text, nullable=True)
    attendees = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    agenda = Column(Text, nullable=True)
    auto_join = Column(Boolean, nullable=False, default=True, server_default="true")
    send_invites = Column(Boolean, nullable=False, default=True, server_default="true")
    sync_status = Column(String(50), nullable=False, default="created", server_default="created")
    extra_metadata = Column("metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    integration_account = relationship("IntegrationAccount", back_populates="calendar_events")
    meeting_outputs = relationship("MeetingOutput", back_populates="calendar_event", cascade="all, delete-orphan")
    tasks = relationship("WorkflowTask", back_populates="calendar_event", cascade="all, delete-orphan")
    email_deliveries = relationship("EmailDelivery", back_populates="calendar_event", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "provider_event_id", name="uq_workflow_calendar_event_provider"),
        Index("ix_workflow_calendar_events_start_time", "start_time"),
        Index("ix_workflow_calendar_events_vexa_meeting", "vexa_platform", "vexa_meeting_id"),
    )


class MeetingOutput(Base):
    __tablename__ = "meeting_outputs"

    id = Column(Integer, primary_key=True, index=True)
    calendar_event_id = Column(Integer, ForeignKey("workflow_calendar_events.id"), nullable=False, index=True)
    vexa_platform = Column(String(50), nullable=True)
    vexa_meeting_id = Column(Text, nullable=True)
    transcript_ref = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    summary = Column(Text, nullable=True)
    decisions = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    generation_status = Column(String(50), nullable=False, default="pending", server_default="pending")
    generated_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    calendar_event = relationship("WorkflowCalendarEvent", back_populates="meeting_outputs")

    __table_args__ = (
        UniqueConstraint("calendar_event_id", name="uq_meeting_outputs_calendar_event"),
        Index("ix_meeting_outputs_generation_status", "generation_status"),
    )


class WorkflowTask(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    calendar_event_id = Column(Integer, ForeignKey("workflow_calendar_events.id"), nullable=False, index=True)
    owner_email = Column(Text, nullable=True, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="open", server_default="open", index=True)
    confidence = Column(Float, nullable=True)
    source = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    calendar_event = relationship("WorkflowCalendarEvent", back_populates="tasks")

    __table_args__ = (
        Index("ix_tasks_calendar_status", "calendar_event_id", "status"),
    )


class EmailDelivery(Base):
    __tablename__ = "email_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    calendar_event_id = Column(Integer, ForeignKey("workflow_calendar_events.id"), nullable=True, index=True)
    recipient_email = Column(Text, nullable=False, index=True)
    template = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="pending", server_default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0, server_default="0")
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    smtp_response = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    payload_ref = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    calendar_event = relationship("WorkflowCalendarEvent", back_populates="email_deliveries")

    __table_args__ = (
        Index("ix_email_deliveries_status_created", "status", "created_at"),
    )
