"""OpenAI-backed meeting summary and task extraction."""

import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.schemas import MeetingExtraction

EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "owner_email": {"type": ["string", "null"]},
                    "due_at": {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["title", "owner_email", "due_at", "description", "confidence"],
            },
        },
    },
    "required": ["summary", "decisions", "tasks"],
}


def transcript_text(transcript: dict[str, Any]) -> str:
    lines = []
    for segment in transcript.get("segments") or []:
        text = (segment.get("text") or "").strip()
        if not text:
            continue
        speaker = (segment.get("speaker") or "Unknown").strip()
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


def _response_text(data: dict[str, Any]) -> str:
    if data.get("output_text"):
        return data["output_text"]
    for output in data.get("output") or []:
        for content in output.get("content") or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return content["text"]
    raise ValueError("OpenAI response did not include output text")


class OpenAIExtractionClient:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None):
        self.settings = settings
        self._client = http_client

    async def extract(self, transcript: dict[str, Any]) -> MeetingExtraction:
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        prompt_text = transcript_text(transcript)
        if not prompt_text:
            return MeetingExtraction(summary="", decisions=[], tasks=[])

        payload = {
            "model": self.settings.openai_model,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "Extract a concise meeting summary, decisions, and assigned action items. "
                        "Return only data grounded in the transcript. If no tasks are explicit, return an empty tasks array."
                    ),
                },
                {"role": "user", "content": prompt_text},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "meeting_extraction",
                    "schema": EXTRACTION_SCHEMA,
                    "strict": True,
                }
            },
        }
        response = await self._post("/responses", json=payload)
        try:
            return MeetingExtraction.model_validate_json(_response_text(response.json()))
        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Invalid OpenAI extraction response: {exc}") from exc

    async def _post(self, path: str, **kwargs) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.settings.openai_api_key}"
        headers["Content-Type"] = "application/json"
        url = f"{self.settings.openai_base_url}{path}"

        if self._client is not None:
            response = await self._client.post(url, headers=headers, **kwargs)
        else:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, **kwargs)
        response.raise_for_status()
        return response
