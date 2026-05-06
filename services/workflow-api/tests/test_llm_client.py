import asyncio
import json

import httpx
import pytest

from app.config import Settings
from app.llm_client import OpenAIExtractionClient, transcript_text


def _settings() -> Settings:
    return Settings(
        service_name="workflow-api",
        log_level="INFO",
        init_db_on_startup=False,
        db_host="postgres",
        db_port="5432",
        db_name="vexa",
        db_user="postgres",
        db_password="postgres",
        db_ssl_mode="disable",
        vexa_api_url="http://api-gateway:8000",
        vexa_api_key="",
        vexa_webhook_secret="",
        encryption_key="",
        oauth_state_secret="",
        public_base_url="http://localhost:8060",
        google_client_id="",
        google_client_secret="",
        microsoft_client_id="",
        microsoft_client_secret="",
        microsoft_tenant_id="common",
        llm_provider="openai",
        openai_api_key="sk-test",
        openai_model="gpt-5-nano",
        openai_base_url="https://api.openai.com/v1",
        local_llm_url="",
        smtp_host="",
        smtp_port=587,
        smtp_username="",
        smtp_password="",
        smtp_from_email="",
        smtp_tls_mode="starttls",
    )


def test_transcript_text_formats_speaker_lines():
    assert transcript_text({
        "segments": [
            {"speaker": "Alice", "text": "We need the launch checklist."},
            {"speaker": "Bob", "text": "I will send it tomorrow."},
        ]
    }) == "Alice: We need the launch checklist.\nBob: I will send it tomorrow."


def test_openai_extraction_posts_structured_output_request():
    captured = {}
    extraction_json = json.dumps({
        "summary": "The team discussed launch tasks.",
        "decisions": ["Use OpenAI for fast launch."],
        "tasks": [
            {
                "title": "Send launch checklist",
                "owner_email": "bob@example.com",
                "due_at": None,
                "description": "Share checklist with team.",
                "confidence": 0.9,
            }
        ],
    })

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"output_text": extraction_json})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            return await OpenAIExtractionClient(_settings(), http_client).extract({
                "segments": [{"speaker": "Bob", "text": "I will send the launch checklist."}]
            })

    extraction = asyncio.run(run())

    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["auth"] == "Bearer sk-test"
    assert captured["json"]["model"] == "gpt-5-nano"
    assert captured["json"]["text"]["format"]["type"] == "json_schema"
    assert captured["json"]["text"]["format"]["strict"] is True
    task_schema = captured["json"]["text"]["format"]["schema"]["properties"]["tasks"]["items"]
    assert "format" not in task_schema["properties"]["owner_email"]
    assert "format" not in task_schema["properties"]["due_at"]
    assert extraction.summary == "The team discussed launch tasks."
    assert extraction.tasks[0].title == "Send launch checklist"
    assert str(extraction.tasks[0].owner_email) == "bob@example.com"


def test_openai_extraction_rejects_invalid_json():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"output_text": "{not json"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            return await OpenAIExtractionClient(_settings(), http_client).extract({
                "segments": [{"speaker": "Bob", "text": "I will send the launch checklist."}]
            })

    with pytest.raises(ValueError, match="Invalid OpenAI extraction response"):
        asyncio.run(run())
