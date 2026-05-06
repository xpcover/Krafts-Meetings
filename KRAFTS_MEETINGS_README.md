# Krafts Meetings Implementation README

This fork adds a Cloudflare-fronted meeting assistant layer on top of Vexa. The goal is to keep Vexa focused on meeting bot execution and transcription while a new workflow service owns calendars, summaries, tasks, email, and edge routing.

Repository fork: `https://github.com/xpcover/Krafts-Meetings`

## What Has Been Added

### Planning and Architecture

- Saved the architecture plan in `cloudflare-vexa-meeting-assistant-plan.md`.
- Added implementation tracking files:
  - `task_plan.md`
  - `progress.md`
  - `findings.md`
- v1 decision: use Cloudflare for edge/control-plane and a self-managed VM for Vexa runtime, Postgres, Redis, MinIO, workflow state, transcription, and SMTP.
- v1 fast-launch decision: use OpenAI API for post-meeting summary and task extraction. Local LLM is deferred.

### Workflow API

Added `services/workflow-api`, a FastAPI service that runs beside the Vexa stack.

Implemented:

- `GET /health`
- `POST /workflow/meetings`
- `GET /workflow/meetings`
- `GET /workflow/oauth/{provider}/start`
- `GET /workflow/oauth/{provider}/callback`
- `POST /workflow/webhooks/vexa/meeting-completed`
- `POST /workflow/mail/test`

The service is wired into `deploy/compose/docker-compose.yml` as `workflow-api` on port `8060`.

### Database Tables

Added workflow-owned tables:

- `integration_accounts`
- `workflow_calendar_events`
- `meeting_outputs`
- `tasks`
- `email_deliveries`

OAuth tokens are encrypted with Fernet before storage.

### Calendar Integration

Implemented provider-neutral calendar flow for:

- Google Calendar / Google Meet
- Microsoft Graph / Outlook Calendar / Teams

The API can:

- generate OAuth authorization URLs
- handle OAuth callbacks
- store encrypted access and refresh tokens
- create calendar events with conferencing links
- persist provider event IDs and meeting URLs

### Vexa Integration

Implemented Vexa API Gateway integration:

- schedules Vexa bots when `auto_join=true`
- stores Vexa meeting references on workflow calendar events
- receives Vexa `meeting.completed` webhooks
- verifies Vexa webhook signatures
- fetches transcripts from Vexa
- handles duplicate webhook delivery idempotently at the meeting output level

### OpenAI Extraction

Added OpenAI-backed extraction in `services/workflow-api/app/llm_client.py`.

Implemented:

- transcript segment formatting into speaker lines
- OpenAI Responses API call
- strict JSON schema response shape
- Pydantic validation for:
  - meeting summary
  - decisions
  - assigned tasks
- task rows inserted into `tasks`
- summary/decisions stored in `meeting_outputs`

Default model:

```env
OPENAI_MODEL=gpt-5-nano
```

### SMTP Delivery

Added SMTP client in `services/workflow-api/app/smtp_client.py`.

Implemented:

- `POST /workflow/mail/test` for SMTP connect/auth verification without sending meeting data
- plain-text meeting summary emails
- plain-text task assignment emails
- delivery logging in `email_deliveries`
- retryable vs permanent SMTP failure classification where SMTP status codes expose it
- duplicate webhook protection to avoid sending repeated emails once delivery rows exist

### Cloudflare Worker

Added `services/cloudflare-worker`.

Implemented:

- Worker entrypoint for public `/workflow/*` routes
- forwarding to Tunnel-backed `WORKFLOW_API_URL`
- Vexa webhook signature header preservation
- optional CORS config
- shared-secret header injection for calls into `workflow-api`
- `wrangler.jsonc`
- Worker unit tests

The VM-side workflow API can require this header with:

```env
WORKFLOW_EDGE_SHARED_SECRET=<same value as Worker secret>
```

The Worker secret is:

```bash
wrangler secret put WORKER_SHARED_SECRET
```

## Important Environment Variables

Core workflow config:

```env
WORKFLOW_API_PORT=8060
WORKFLOW_ENCRYPTION_KEY=
WORKFLOW_OAUTH_STATE_SECRET=
WORKFLOW_PUBLIC_BASE_URL=http://localhost:8060
WORKFLOW_VEXA_WEBHOOK_SECRET=
WORKFLOW_EDGE_SHARED_SECRET=
```

Vexa API Gateway:

```env
VEXA_API_URL=http://api-gateway:8000
VEXA_API_KEY=
```

Google:

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

Microsoft:

```env
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
MICROSOFT_TENANT_ID=common
```

OpenAI:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-nano
OPENAI_BASE_URL=https://api.openai.com/v1
```

SMTP:

```env
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_TLS_MODE=starttls
```

Cloudflare:

```env
CLOUDFLARE_TUNNEL_TOKEN=
CLOUDFLARE_WORKER_SHARED_SECRET=
```

## How To Test

Workflow API tests:

```bash
cd /Users/apple/Documents/Github/aimeeting/vexa-review
/Library/Frameworks/Python.framework/Versions/3.13/bin/pytest services/workflow-api/tests -q
```

Current result:

```text
35 passed
```

Python compile check:

```bash
cd /Users/apple/Documents/Github/aimeeting/vexa-review
/opt/homebrew/bin/python3.13 -m compileall -q services/workflow-api/app
```

Cloudflare Worker tests:

```bash
cd /Users/apple/Documents/Github/aimeeting/vexa-review/services/cloudflare-worker
npm test
```

Current result:

```text
3 passed
```

Worker dry run:

```bash
cd /Users/apple/Documents/Github/aimeeting/vexa-review/services/cloudflare-worker
npx wrangler@latest deploy --dry-run
```

Current result: passed.

## Current Limitations

- Docker Compose validation could not be run on this local machine because the Docker CLI here does not have a working Compose plugin.
- Google and Microsoft OAuth are implemented, but real provider credentials still need to be configured.
- Token refresh helpers exist, but automatic refresh during provider API calls still needs a production hardening pass.
- Cloudflare Worker is implemented and dry-run validated, but not deployed to a real Cloudflare account from this environment.
- Cloudflare Queues/Workflows are not implemented yet.
- Dashboard UI changes are not implemented yet.
- SMTP delivery is synchronous in v1; queue-backed retry processing is still pending.

## Pushed Implementation Commits

- `c0ba0df` Add Krafts Meetings implementation plan
- `4c31e24` Record Krafts Meetings fork setup
- `f6dff46` Scaffold workflow API service
- `0fc39af` Add workflow data models and token encryption
- `75b6aeb` Add workflow calendar meeting APIs
- `de80cd1` Add workflow OAuth connection endpoints
- `6ce82b2` Schedule Vexa bots from workflow meetings
- `3f694fc` Handle Vexa completion webhooks
- `6ce704b` Add OpenAI meeting extraction
- `c2f51f8` Add SMTP workflow delivery
- `8c61721` Add Cloudflare workflow edge worker

## Recommended Next Steps

1. Deploy Vexa plus `workflow-api` on a VM with Docker Compose.
2. Configure Cloudflare Tunnel to expose only `workflow-api`.
3. Deploy `services/cloudflare-worker` with real `WORKFLOW_API_URL`.
4. Configure Google and Microsoft OAuth apps with Worker callback URLs.
5. Run a real end-to-end test:
   - connect calendar
   - create meeting
   - schedule Vexa bot
   - receive completion webhook
   - fetch transcript
   - extract summary/tasks with OpenAI
   - send SMTP emails
6. Add Cloudflare Queues/Workflows for async retries.
7. Add dashboard screens for connecting accounts, creating meetings, viewing tasks, and testing SMTP.
