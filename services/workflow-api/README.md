# Workflow API

## Why

Vexa owns meeting bot execution and transcription. Krafts Meetings needs a separate product workflow layer for calendar integrations, task extraction, and outbound email so those concerns do not leak into `vexa-bot` or the meeting runtime.

## What

FastAPI service for the Cloudflare-fronted control plane. In v1 it will own:

- Google Calendar and Microsoft Graph OAuth/token storage
- calendar meeting creation and sync
- Vexa bot scheduling and transcript retrieval
- post-meeting summary and task extraction via OpenAI API for fast launch
- SMTP summary/task delivery

This first slice provides the service skeleton, configuration, database connectivity helpers, Docker image, compose wiring, and tests.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Service health and database configuration status |
| `POST` | `/workflow/meetings` | Create a Google Calendar or Outlook event with conferencing |
| `GET` | `/workflow/meetings?user_id={id}` | List workflow-created/synced meetings for a user |
| `GET` | `/workflow/oauth/{provider}/start?user_id={id}` | Generate a Google/Outlook OAuth authorization URL |
| `GET` | `/workflow/oauth/{provider}/callback` | Exchange OAuth code and store encrypted provider tokens |
| `POST` | `/workflow/webhooks/vexa/meeting-completed` | Verify Vexa webhook, fetch transcript, extract summary/tasks when OpenAI is configured, and mark meeting output |

`POST /workflow/meetings` currently accepts `user_id` in the request body. Cloudflare/Vexa identity header integration is planned for a later auth pass.

## Tables

Workflow API stores its own state in namespaced/product tables. Vexa already has a `calendar_events` table, so the workflow calendar table is named `workflow_calendar_events` to avoid schema collisions.

| Table | Purpose |
| --- | --- |
| `integration_accounts` | Encrypted Google/Microsoft OAuth account state |
| `workflow_calendar_events` | Provider calendar events and Vexa meeting references |
| `meeting_outputs` | Transcript references, summaries, decisions, generation status |
| `tasks` | Assigned action items extracted from meeting transcripts |
| `email_deliveries` | SMTP delivery attempts and responses |

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `WORKFLOW_API_PORT` | `8060` | Host/container port for the service |
| `WORKFLOW_INIT_DB_ON_STARTUP` | `false` | When `true`, validate DB connectivity during startup |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSL_MODE` | inherited | Self-hosted Postgres connection |
| `VEXA_API_URL` | `http://api-gateway:8000` | Internal Vexa API Gateway URL |
| `VEXA_API_KEY` | empty | API key used for bot and transcript calls |
| `WORKFLOW_ENCRYPTION_KEY` | empty | Required before OAuth token storage is implemented |
| `WORKFLOW_OAUTH_STATE_SECRET` | empty | Signs OAuth callback state |
| `WORKFLOW_PUBLIC_BASE_URL` | `http://localhost:8060` | Public callback base URL |
| `WORKFLOW_VEXA_WEBHOOK_SECRET` | empty | Verifies Vexa meeting-completed webhooks |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | empty | Google OAuth credentials |
| `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_TENANT_ID` | empty / `common` | Microsoft Graph OAuth credentials |
| `LLM_PROVIDER` | `openai` | Post-meeting extraction provider |
| `OPENAI_API_KEY` | empty | OpenAI API key for fast-launch summary/task extraction |
| `OPENAI_MODEL` | `gpt-5-nano` | OpenAI model used with the Responses API |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible API base URL |
| `LOCAL_LLM_URL` | empty | Reserved for a later local LLM fallback |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_TLS_MODE` | empty / defaults | SMTP delivery configuration |

## Run

```bash
cd deploy/compose
docker compose up workflow-api
```

For local unit tests:

```bash
cd services/workflow-api
pytest tests -q
```

## DoD

| # | Check | Status |
| --- | --- | --- |
| 1 | `GET /health` returns 200 | implemented |
| 2 | service can build as a Docker image | implemented |
| 3 | compose wires service to Postgres and Vexa gateway | implemented |
| 4 | DB ping helper exists and can be enabled on startup | implemented |
| 5 | OAuth/calendar/task workflows | implemented |
| 6 | SMTP workflows | pending later phases |
