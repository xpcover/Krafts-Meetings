# Task Plan: Cloudflare-First Vexa Meeting Assistant

## Goal

Implement the saved architecture in `cloudflare-vexa-meeting-assistant-plan.md`: a Cloudflare-fronted, self-hosted Vexa meeting assistant with workflow APIs for Google/Outlook calendar meeting creation, transcription-driven task extraction, and SMTP email delivery.

## Current Status

- Overall status: planning
- Architecture plan: complete
- Implementation task list: in progress
- Code implementation: not started
- GitHub implementation repo: `xpcover/Krafts-Meetings`

## Phases

### Phase 0: Repo and Runtime Baseline

Status: in_progress

Tasks:

- Confirm whether implementation should happen in the cloned `vexa-review` tree or a clean fork/worktree. Done: implementation target is the `xpcover/Krafts-Meetings` fork, currently checked out locally at `vexa-review`.
- Decide package layout for new `workflow-api` service and Cloudflare Worker.
- Verify current Vexa compose stack assumptions: Postgres, Redis, MinIO, API Gateway, Meeting API, Runtime API.
- Identify existing shared model/database utilities that can be reused safely.
- Produce initial `.env.example` additions for workflow, OAuth, SMTP, LLM, and Cloudflare tunnel settings.

Acceptance:

- Workspace target is explicit.
- New service layout is chosen.
- Required environment variables are listed.

### Phase 1: Workflow API Skeleton

Status: pending

Tasks:

- Add `services/workflow-api` as a FastAPI service.
- Add health endpoint: `GET /health`.
- Add config loading and validation.
- Add async DB connection using the same Postgres instance as Vexa.
- Add initial Dockerfile and compose service entry.
- Add minimal tests for app startup, health, and config validation.

Acceptance:

- `workflow-api` starts locally.
- `GET /health` returns `200`.
- Service can connect to Postgres in compose.

### Phase 2: Workflow Data Model

Status: pending

Tasks:

- Add tables:
  - `integration_accounts`
  - `calendar_events`
  - `meeting_outputs`
  - `tasks`
  - `email_deliveries`
- Add idempotency keys for provider events and Vexa webhook processing.
- Add encrypted token storage for OAuth refresh/access tokens.
- Add schema initialization or migration path consistent with the repo's current DB approach.
- Add tests for model creation, uniqueness, and encrypted token round trips.

Acceptance:

- Tables are created without touching Vexa bot code.
- Tokens are never stored plaintext.
- Duplicate provider events and duplicate Vexa webhooks are handled idempotently.

### Phase 3: Calendar Integrations

Status: pending

Tasks:

- Implement Google OAuth callback handling and token refresh.
- Implement Microsoft Graph OAuth callback handling and token refresh.
- Implement `POST /workflow/meetings`.
- Implement `GET /workflow/meetings`.
- Create calendar events with video conferencing:
  - Google Calendar / Google Meet
  - Outlook Calendar / Teams
- Store provider event IDs, meeting URLs, attendees, status, and timestamps.
- Add mocked tests for Google Calendar and Microsoft Graph APIs.

Acceptance:

- A user can create a Google calendar meeting through the workflow API.
- A user can create an Outlook calendar meeting through the workflow API.
- Created meetings are persisted and listable.

### Phase 4: Vexa Bot and Transcript Integration

Status: pending

Tasks:

- Add Vexa API client in `workflow-api`.
- Schedule a Vexa bot when a meeting is created with `auto_join=true`.
- Store Vexa meeting/bot IDs on `calendar_events`.
- Implement transcript retrieval from Vexa API Gateway.
- Implement `POST /workflow/webhooks/vexa/meeting-completed`.
- Add signature/shared-secret validation for Vexa webhook requests.
- Add mocked tests for Vexa `/bots` and `/transcripts`.

Acceptance:

- Creating a meeting with `auto_join=true` calls Vexa `/bots`.
- Meeting completion webhook fetches transcript exactly once per Vexa meeting.
- Duplicate webhooks do not duplicate outputs, tasks, or emails.

### Phase 5: Local LLM Task Extraction

Status: pending

Tasks:

- Add configurable local LLM endpoint client.
- Define extraction output shape: summary, decisions, tasks.
- Add transcript-to-task prompt/template with strict JSON response.
- Add deterministic parser and validation for LLM output.
- Store summaries in `meeting_outputs`.
- Store action items in `tasks`.
- Add fixture tests for transcript parsing and malformed LLM responses.

Acceptance:

- A completed meeting produces one summary and zero or more tasks.
- Malformed LLM responses fail safely and are recorded for retry/debugging.
- No transcript text is sent outside the self-managed execution plane.

### Phase 6: SMTP Delivery

Status: pending

Tasks:

- Add SMTP config: host, port, username, password, TLS mode, sender.
- Implement `POST /workflow/mail/test`.
- Add summary email template.
- Add task assignment email template.
- Add delivery logging in `email_deliveries`.
- Add retry classification for temporary vs permanent SMTP failures.
- Add tests using a mocked/local SMTP server.

Acceptance:

- SMTP config can be verified without sending meeting data.
- Summary and task emails are queued/sent after post-meeting processing.
- Delivery status and SMTP response are persisted.

### Phase 7: Cloudflare Control Plane

Status: pending

Tasks:

- Add Cloudflare Worker project for public entrypoints.
- Route OAuth callbacks, Vexa webhooks, and workflow API traffic through the Worker.
- Use Cloudflare Queue/Workflow payloads containing IDs only, not transcript text.
- Add Cloudflare Tunnel configuration docs for reaching `workflow-api`.
- Add Wrangler config and secret inventory.
- Add Worker smoke tests for route validation and forwarding.

Acceptance:

- Worker can reach `workflow-api` through Tunnel.
- Public webhook routes validate source/secrets before forwarding.
- Queue payloads contain only IDs and metadata, never transcript body text.

### Phase 8: Dashboard/API Consumption

Status: pending

Tasks:

- Decide whether to extend Vexa dashboard or create a separate minimal workflow dashboard.
- Add UI/API calls for connecting Google and Outlook accounts.
- Add UI/API calls for creating meetings.
- Add meetings list with transcript/task/email status.
- Add task list and task status update flow.
- Add SMTP test/settings UI if dashboard work is in scope.

Acceptance:

- User can connect calendar, create a meeting, view outputs, and update tasks from a UI or documented API flow.

### Phase 9: End-to-End Verification

Status: pending

Tasks:

- Run compose stack with Vexa and `workflow-api`.
- Run mocked integration test: meeting create -> Vexa bot schedule -> webhook -> transcript -> LLM extraction -> SMTP delivery.
- Run Cloudflare Worker smoke tests.
- Verify health checks for Vexa, workflow-api, Postgres, Redis, MinIO, transcription, and LLM.
- Document deployment runbook and rollback steps.

Acceptance:

- End-to-end test passes.
- Deployment checklist is documented.
- Known limitations and remaining production gaps are recorded.

## Dependencies and Constraints

- Supabase is excluded from v1.
- Cloudflare Containers are not the Vexa runtime target in v1.
- Vexa bot code should not be modified for calendar, task, or email logic.
- Durable transcript/task/token data must stay on the self-managed VM.
- Google Calendar and Microsoft Graph are external trust boundaries by design.
- SMTP must be configurable and testable without leaking transcript contents.

## Errors Encountered

| Date | Error | Attempt | Resolution |
| --- | --- | --- | --- |
| 2026-05-05 | None yet | N/A | N/A |
