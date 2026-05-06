# Task Plan: Cloudflare-First Vexa Meeting Assistant

## Goal

Implement the saved architecture in `cloudflare-vexa-meeting-assistant-plan.md`: a Cloudflare-fronted, self-hosted Vexa meeting assistant with workflow APIs for Google/Outlook calendar meeting creation, transcription-driven task extraction, and SMTP email delivery.

## Current Status

- Overall status: implementation_started
- Architecture plan: complete
- Implementation task list: in progress
- Code implementation: started
- GitHub implementation repo: `xpcover/Krafts-Meetings`

## Phases

### Phase 0: Repo and Runtime Baseline

Status: in_progress

Tasks:

- Confirm whether implementation should happen in the cloned `vexa-review` tree or a clean fork/worktree. Done: implementation target is the `xpcover/Krafts-Meetings` fork, currently checked out locally at `vexa-review`.
- Decide package layout for new `workflow-api` service and Cloudflare Worker.
- Verify current Vexa compose stack assumptions: Postgres, Redis, MinIO, API Gateway, Meeting API, Runtime API. Done: compose includes those services and `workflow-api` is wired to Postgres/API Gateway.
- Identify existing shared model/database utilities that can be reused safely. Done: workflow-api uses its own config/database layer to avoid import-time env validation from Vexa DB modules.
- Produce initial `.env.example` additions for workflow, OAuth, SMTP, LLM, and Cloudflare tunnel settings. Done.

Acceptance:

- Workspace target is explicit.
- New service layout is chosen.
- Required environment variables are listed.

### Phase 1: Workflow API Skeleton

Status: in_progress

Tasks:

- Add `services/workflow-api` as a FastAPI service. Done.
- Add health endpoint: `GET /health`. Done.
- Add config loading and validation. Done.
- Add async DB connection using the same Postgres instance as Vexa. Done.
- Add initial Dockerfile and compose service entry. Done.
- Add minimal tests for app startup, health, and config validation. Done.

Acceptance:

- `workflow-api` starts locally.
- `GET /health` returns `200`.
- Service can connect to Postgres in compose.

### Phase 2: Workflow Data Model

Status: in_progress

Tasks:

- Add tables:
  - `integration_accounts` Done.
  - `workflow_calendar_events` Done. Note: namespaced because Vexa already owns `calendar_events`.
  - `meeting_outputs` Done.
  - `tasks` Done.
  - `email_deliveries` Done.
- Add idempotency keys for provider events and Vexa webhook processing. Done via uniqueness constraints on integration accounts, provider events, and meeting outputs.
- Add encrypted token storage for OAuth refresh/access tokens. Done via `TokenCipher`; endpoint usage comes in Phase 3.
- Add schema initialization or migration path consistent with the repo's current DB approach. Done via `schema_sync.ensure_schema`.
- Add tests for model creation, uniqueness, and encrypted token round trips. Done.

Acceptance:

- Tables are created without touching Vexa bot code.
- Tokens are never stored plaintext.
- Duplicate provider events and duplicate Vexa webhooks are handled idempotently.

### Phase 3: Calendar Integrations

Status: in_progress

Tasks:

- Implement Google OAuth callback handling and token refresh. Callback handling done; refresh helper done; automatic refresh during provider calls pending.
- Implement Microsoft Graph OAuth callback handling and token refresh. Callback handling done; refresh helper done; automatic refresh during provider calls pending.
- Implement `POST /workflow/meetings`. Done for connected-account access-token flow; automatic refresh integration remains pending.
- Implement `GET /workflow/meetings`. Done.
- Create calendar events with video conferencing:
  - Google Calendar / Google Meet Done.
  - Outlook Calendar / Teams Done.
- Store provider event IDs, meeting URLs, attendees, status, and timestamps. Done.
- Add mocked tests for Google Calendar and Microsoft Graph APIs. Done.
- Add OAuth state, authorization URL, and token exchange tests. Done.

Acceptance:

- A user can create a Google calendar meeting through the workflow API.
- A user can create an Outlook calendar meeting through the workflow API.
- Created meetings are persisted and listable.

### Phase 4: Vexa Bot and Transcript Integration

Status: in_progress

Tasks:

- Add Vexa API client in `workflow-api`. Done.
- Schedule a Vexa bot when a meeting is created with `auto_join=true`. Done when `VEXA_API_KEY` is configured.
- Store Vexa meeting/bot IDs on `calendar_events`. Done for native meeting IDs on `workflow_calendar_events`; Vexa response is stored in metadata.
- Implement transcript retrieval from Vexa API Gateway. Done.
- Implement `POST /workflow/webhooks/vexa/meeting-completed`. Done.
- Add signature/shared-secret validation for Vexa webhook requests. Done.
- Add mocked tests for Vexa `/bots` and `/transcripts`. Done.

Acceptance:

- Creating a meeting with `auto_join=true` calls Vexa `/bots`.
- Meeting completion webhook fetches transcript exactly once per Vexa meeting.
- Duplicate webhooks do not duplicate outputs, tasks, or emails.

### Phase 5: OpenAI Task Extraction

Status: in_progress

Tasks:

- Add configurable OpenAI Responses API client. Done.
- Define extraction output shape: summary, decisions, tasks. Done.
- Add transcript-to-task prompt/template with strict JSON schema response. Done.
- Add deterministic parser and validation for model output. Done.
- Store summaries in `meeting_outputs`. Done.
- Store action items in `tasks`. Done.
- Add fixture tests for transcript parsing and malformed model responses. Done.
- Defer local LLM endpoint fallback until after fast-launch OpenAI path is stable.

Acceptance:

- A completed meeting produces one summary and zero or more tasks.
- Malformed LLM responses fail safely and are recorded for retry/debugging.
- Transcript text is sent to OpenAI only when `LLM_PROVIDER=openai` and `OPENAI_API_KEY` are configured.

### Phase 6: SMTP Delivery

Status: in_progress

Tasks:

- Add SMTP config: host, port, username, password, TLS mode, sender. Done.
- Implement `POST /workflow/mail/test`. Done.
- Add summary email template. Done.
- Add task assignment email template. Done.
- Add delivery logging in `email_deliveries`. Done.
- Add retry classification for temporary vs permanent SMTP failures. Done.
- Add tests using a mocked/local SMTP server. Done with mocked SMTP client tests.

Acceptance:

- SMTP config can be verified without sending meeting data. Done.
- Summary and task emails are queued/sent after post-meeting processing. Done for synchronous v1 sends.
- Delivery status and SMTP response are persisted. Done.

### Phase 7: Cloudflare Control Plane

Status: in_progress

Tasks:

- Add Cloudflare Worker project for public entrypoints. Done.
- Route OAuth callbacks, Vexa webhooks, and workflow API traffic through the Worker. Done for `/workflow/*` forwarding.
- Use Cloudflare Queue/Workflow payloads containing IDs only, not transcript text.
- Add Cloudflare Tunnel configuration docs for reaching `workflow-api`. Done at Worker package level; full VM runbook pending.
- Add Wrangler config and secret inventory. Done.
- Add Worker smoke tests for route validation and forwarding. Done.

Acceptance:

- Worker can reach `workflow-api` through Tunnel. Pending live Cloudflare/Tunnel credentials.
- Public webhook routes validate source/secrets before forwarding. Done with Worker shared-secret header plus Vexa webhook signature preservation for `workflow-api`.
- Queue payloads contain only IDs and metadata, never transcript body text. Pending queue implementation; no Cloudflare queue persistence exists yet.

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
- Fast launch uses OpenAI API for summary/task extraction; local LLM fallback is deferred.
- Google Calendar and Microsoft Graph are external trust boundaries by design.
- SMTP must be configurable and testable without leaking transcript contents.

## Errors Encountered

| Date | Error | Attempt | Resolution |
| --- | --- | --- | --- |
| 2026-05-05 | `python` command not found | Ran focused workflow-api tests with `python -m pytest` | Retried with available pytest binary |
| 2026-05-05 | `python3 -m pytest` had no pytest installed | Ran focused workflow-api tests with `python3 -m pytest` | Used `/Library/Frameworks/Python.framework/Versions/3.13/bin/pytest`; tests passed |
| 2026-05-05 | `docker compose` plugin unavailable (`unknown shorthand flag: 'f'`) | Tried compose config validation | Docker compose validation pending until compose plugin or legacy binary is installed |
| 2026-05-05 | `pytest.mark.asyncio` unsupported | Wrote async provider tests with pytest asyncio marker | Reworked tests to use `asyncio.run`; tests passed |
