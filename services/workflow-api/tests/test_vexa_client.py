import asyncio
import json

import httpx

from app.vexa_client import VexaClient, native_meeting_id


def test_native_meeting_id_for_google_meet():
    assert native_meeting_id("google_meet", "https://meet.google.com/abc-defg-hij") == "abc-defg-hij"


def test_native_meeting_id_for_teams_keeps_full_join_url():
    url = "https://teams.microsoft.com/l/meetup-join/abc"
    assert native_meeting_id("teams", url) == url


def test_schedule_bot_posts_expected_payload():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers.get("x-api-key")
        captured["json"] = json.loads(request.content)
        return httpx.Response(201, json={"id": 123, "status": "requested"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            return await VexaClient("http://api-gateway:8000", "vxa-test", http_client).schedule_bot(
                "google_meet",
                "https://meet.google.com/abc-defg-hij",
                "Krafts - Roadmap Review",
            )

    scheduled = asyncio.run(run())

    assert captured["url"] == "http://api-gateway:8000/bots"
    assert captured["api_key"] == "vxa-test"
    assert captured["json"] == {
        "platform": "google_meet",
        "native_meeting_id": "abc-defg-hij",
        "bot_name": "Krafts - Roadmap Review",
    }
    assert scheduled.native_meeting_id == "abc-defg-hij"
    assert scheduled.response["id"] == 123


def test_get_transcript_uses_vexa_transcript_endpoint():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers.get("x-api-key")
        return httpx.Response(200, json={"segments": [{"text": "hello"}]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            return await VexaClient("http://api-gateway:8000", "vxa-test", http_client).get_transcript(
                "google_meet",
                "abc-defg-hij",
            )

    transcript = asyncio.run(run())

    assert captured["url"] == "http://api-gateway:8000/transcripts/google_meet/abc-defg-hij"
    assert captured["api_key"] == "vxa-test"
    assert transcript["segments"] == [{"text": "hello"}]
