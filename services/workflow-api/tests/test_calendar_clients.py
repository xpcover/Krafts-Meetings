from datetime import datetime, timezone
import asyncio

import httpx

from app.calendar_clients import GOOGLE_EVENTS_URL, MICROSOFT_EVENTS_URL, CalendarClient
from app.schemas import Attendee, CalendarProvider, MeetingCreate


def _meeting(provider: CalendarProvider) -> MeetingCreate:
    return MeetingCreate(
        user_id=7,
        provider=provider,
        title="Roadmap Review",
        start_time=datetime(2026, 5, 10, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 5, 10, 10, 30, tzinfo=timezone.utc),
        timezone="UTC",
        attendees=[Attendee(email="a@example.com", name="Alice")],
        agenda="Discuss launch tasks",
        auto_join=True,
        send_invites=True,
    )


def test_google_create_event_uses_conference_data_and_attendees():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["json"] = __import__("json").loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "google-event-1",
                "conferenceData": {
                    "entryPoints": [
                        {"entryPointType": "video", "uri": "https://meet.google.com/abc-defg-hij"}
                    ]
                },
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            return await CalendarClient(http_client).create_event(CalendarProvider.GOOGLE, "token-123", _meeting(CalendarProvider.GOOGLE))

    event = asyncio.run(run())

    assert captured["url"].startswith(GOOGLE_EVENTS_URL)
    assert "conferenceDataVersion=1" in captured["url"]
    assert captured["auth"] == "Bearer token-123"
    assert captured["json"]["summary"] == "Roadmap Review"
    assert captured["json"]["attendees"] == [{"email": "a@example.com", "displayName": "Alice"}]
    assert captured["json"]["conferenceData"]["createRequest"]["conferenceSolutionKey"]["type"] == "hangoutsMeet"
    assert event.provider_event_id == "google-event-1"
    assert event.meeting_url == "https://meet.google.com/abc-defg-hij"
    assert event.conference_provider == "google_meet"


def test_microsoft_create_event_uses_teams_online_meeting():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["json"] = __import__("json").loads(request.content)
        return httpx.Response(
            201,
            json={
                "id": "outlook-event-1",
                "onlineMeeting": {"joinUrl": "https://teams.microsoft.com/l/meetup-join/abc"},
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            return await CalendarClient(http_client).create_event(CalendarProvider.OUTLOOK, "token-456", _meeting(CalendarProvider.OUTLOOK))

    event = asyncio.run(run())

    assert captured["url"] == MICROSOFT_EVENTS_URL
    assert captured["auth"] == "Bearer token-456"
    assert captured["json"]["subject"] == "Roadmap Review"
    assert captured["json"]["isOnlineMeeting"] is True
    assert captured["json"]["onlineMeetingProvider"] == "teamsForBusiness"
    assert captured["json"]["attendees"][0]["emailAddress"]["address"] == "a@example.com"
    assert event.provider_event_id == "outlook-event-1"
    assert event.meeting_url == "https://teams.microsoft.com/l/meetup-join/abc"
    assert event.conference_provider == "teams"
