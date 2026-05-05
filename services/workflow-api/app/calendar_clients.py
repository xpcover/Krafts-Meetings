"""Calendar provider clients for Google Calendar and Microsoft Graph."""

from uuid import uuid4

import httpx

from app.schemas import CalendarProvider, MeetingCreate, ProviderEvent

GOOGLE_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
MICROSOFT_EVENTS_URL = "https://graph.microsoft.com/v1.0/me/events"


def _google_event_payload(req: MeetingCreate) -> dict:
    return {
        "summary": req.title,
        "description": req.agenda or "",
        "start": {
            "dateTime": req.start_time.isoformat(),
            "timeZone": req.timezone,
        },
        "end": {
            "dateTime": req.end_time.isoformat(),
            "timeZone": req.timezone,
        },
        "attendees": [{"email": attendee.email, **({"displayName": attendee.name} if attendee.name else {})} for attendee in req.attendees],
        "conferenceData": {
            "createRequest": {
                "requestId": f"krafts-{uuid4().hex}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
        "guestsCanModify": False,
    }


def _microsoft_event_payload(req: MeetingCreate) -> dict:
    return {
        "subject": req.title,
        "body": {
            "contentType": "HTML",
            "content": req.agenda or "",
        },
        "start": {
            "dateTime": req.start_time.isoformat(),
            "timeZone": req.timezone,
        },
        "end": {
            "dateTime": req.end_time.isoformat(),
            "timeZone": req.timezone,
        },
        "attendees": [
            {
                "emailAddress": {
                    "address": attendee.email,
                    "name": attendee.name or attendee.email,
                },
                "type": "required",
            }
            for attendee in req.attendees
        ],
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness",
    }


def _extract_google_meeting_url(data: dict) -> str | None:
    for entry_point in data.get("conferenceData", {}).get("entryPoints", []):
        if entry_point.get("entryPointType") == "video" and entry_point.get("uri"):
            return entry_point["uri"]
    return data.get("hangoutLink")


class CalendarClient:
    def __init__(self, http_client: httpx.AsyncClient | None = None):
        self._client = http_client

    async def create_event(self, provider: CalendarProvider, access_token: str, req: MeetingCreate) -> ProviderEvent:
        if provider == CalendarProvider.GOOGLE:
            return await self.create_google_event(access_token, req)
        if provider == CalendarProvider.OUTLOOK:
            return await self.create_microsoft_event(access_token, req)
        raise ValueError(f"Unsupported calendar provider: {provider}")

    async def create_google_event(self, access_token: str, req: MeetingCreate) -> ProviderEvent:
        params = {"conferenceDataVersion": "1"}
        if req.send_invites:
            params["sendUpdates"] = "all"
        else:
            params["sendUpdates"] = "none"

        response = await self._post(
            GOOGLE_EVENTS_URL,
            access_token,
            json=_google_event_payload(req),
            params=params,
        )
        data = response.json()
        return ProviderEvent(
            provider_event_id=data["id"],
            meeting_url=_extract_google_meeting_url(data),
            conference_provider="google_meet",
            raw=data,
        )

    async def create_microsoft_event(self, access_token: str, req: MeetingCreate) -> ProviderEvent:
        response = await self._post(
            MICROSOFT_EVENTS_URL,
            access_token,
            json=_microsoft_event_payload(req),
        )
        data = response.json()
        online_meeting = data.get("onlineMeeting") or {}
        return ProviderEvent(
            provider_event_id=data["id"],
            meeting_url=online_meeting.get("joinUrl") or data.get("webLink"),
            conference_provider="teams",
            raw=data,
        )

    async def _post(self, url: str, access_token: str, **kwargs) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {access_token}"
        headers["Content-Type"] = "application/json"

        if self._client is not None:
            response = await self._client.post(url, headers=headers, **kwargs)
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, **kwargs)
        response.raise_for_status()
        return response
