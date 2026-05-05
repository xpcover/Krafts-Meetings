from app.models import (
    Base,
    EmailDelivery,
    IntegrationAccount,
    MeetingOutput,
    WorkflowCalendarEvent,
    WorkflowTask,
)


def test_workflow_tables_are_registered():
    assert {
        "integration_accounts",
        "workflow_calendar_events",
        "meeting_outputs",
        "tasks",
        "email_deliveries",
    }.issubset(Base.metadata.tables.keys())


def test_calendar_table_is_namespaced_to_avoid_vexa_collision():
    assert WorkflowCalendarEvent.__tablename__ == "workflow_calendar_events"


def test_expected_uniqueness_constraints_exist():
    constraints = {
        constraint.name
        for table in [
            IntegrationAccount.__table__,
            WorkflowCalendarEvent.__table__,
            MeetingOutput.__table__,
        ]
        for constraint in table.constraints
        if constraint.name
    }

    assert "uq_integration_account_provider" in constraints
    assert "uq_workflow_calendar_event_provider" in constraints
    assert "uq_meeting_outputs_calendar_event" in constraints


def test_relationships_are_declared():
    assert "calendar_events" in IntegrationAccount.__mapper__.relationships
    assert "meeting_outputs" in WorkflowCalendarEvent.__mapper__.relationships
    assert "tasks" in WorkflowCalendarEvent.__mapper__.relationships
    assert "email_deliveries" in WorkflowCalendarEvent.__mapper__.relationships
    assert WorkflowTask.__table__.name == "tasks"
    assert EmailDelivery.__table__.name == "email_deliveries"
