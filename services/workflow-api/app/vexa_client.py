"""Client for Vexa API Gateway bot operations."""

import re
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ScheduledBot:
    platform: str
    native_meeting_id: str
    response: dict[str, Any]


def native_meeting_id(platform: str, meeting_url: str) -> str:
    if platform == "google_meet":
        match = re.search(r"meet\.google\.com/([a-z]{3}-[a-z]{4}-[a-z]{3})", meeting_url)
        if match:
            return match.group(1)
    if platform == "zoom":
        match = re.search(r"/j/(\d+)", meeting_url)
        if match:
            return match.group(1)
    if platform == "teams":
        return meeting_url
    return meeting_url


class VexaClient:
    def __init__(self, base_url: str, api_key: str, http_client: httpx.AsyncClient | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = http_client

    async def schedule_bot(self, platform: str, meeting_url: str, bot_name: str) -> ScheduledBot:
        native_id = native_meeting_id(platform, meeting_url)
        payload = {
            "platform": platform,
            "native_meeting_id": native_id,
            "bot_name": bot_name,
        }
        response = await self._post("/bots", json=payload)
        return ScheduledBot(platform=platform, native_meeting_id=native_id, response=response.json())

    async def _post(self, path: str, **kwargs) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers["X-API-Key"] = self.api_key
        headers["Content-Type"] = "application/json"
        url = f"{self.base_url}{path}"

        if self._client is not None:
            response = await self._client.post(url, headers=headers, **kwargs)
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, **kwargs)
        response.raise_for_status()
        return response
