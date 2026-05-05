# Findings: Cloudflare-First Vexa Meeting Assistant

## Source Documents

- Architecture plan: `cloudflare-vexa-meeting-assistant-plan.md`
- Vexa review clone: `vexa-review`

## Repo Findings

- The workspace root originally contained only `AGENTS.md` and the saved architecture plan.
- Vexa was cloned into `vexa-review` for review.
- GitHub org fork created: `https://github.com/xpcover/Krafts-Meetings`.
- Local `vexa-review` remote `origin` now points to `https://github.com/xpcover/Krafts-Meetings.git`; `upstream` points to `https://github.com/Vexa-ai/vexa.git`.
- Vexa includes an experimental `services/calendar-service`, but the architecture calls for a provider-neutral `workflow-api`.
- Vexa compose documentation states that bots spawn as Docker containers and the stack uses Postgres, Redis, and MinIO.
- Vexa has API Gateway routes for bots and transcripts that `workflow-api` can call.
- Vexa has post-meeting/webhook infrastructure that can trigger workflow processing.
- Added `services/workflow-api` as the new service root for Krafts Meetings orchestration.
- `workflow-api` uses an isolated config/database layer instead of importing `meeting_api.database` or `admin_models.database` because those modules validate DB env at import time.
- Vexa already owns a `calendar_events` table, so workflow calendar state uses `workflow_calendar_events`.
- Workflow schema convergence uses the repo's `libs/schema-sync` package.
- Phase 3 uses explicit `user_id` in workflow requests for now; Cloudflare/Vexa identity header mapping is deferred.
- Google Calendar event creation uses `conferenceData.createRequest` for Google Meet.
- Microsoft Graph event creation uses `isOnlineMeeting=true` and `onlineMeetingProvider=teamsForBusiness`.
- Official Google docs confirm web-server OAuth uses `https://accounts.google.com/o/oauth2/v2/auth`, offline access requires `access_type=offline`, and token exchange uses `https://oauth2.googleapis.com/token`.
- Official Google Calendar docs confirm `conferenceData.createRequest` with `conferenceDataVersion=1` for conference creation.
- Official Microsoft docs confirm v2 authorize/token endpoints under `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/*` and `offline_access` for refresh tokens.
- OAuth state is signed with HMAC instead of persisted in a DB table.
- `workflow-api` now schedules Vexa bots through API Gateway `/bots` when `auto_join=true` and `VEXA_API_KEY` is configured.
- If `auto_join=true` but `VEXA_API_KEY` is missing, meeting creation still succeeds with sync status `created_bot_not_configured`.
- Local shell has Docker CLI `29.4.0`, but `docker compose` plugin and `docker-compose` binary are unavailable.

## Architecture Findings

- Cloudflare should be used as control/edge plane, not the primary Vexa runtime.
- Durable data remains on the self-managed VM.
- Cloudflare Queue/Workflow payloads should contain IDs only, not transcript body text.
- Supabase is explicitly excluded from v1.
- Local LLM and self-hosted transcription are preferred for transcript privacy.

## Open Questions

- Should the local directory be renamed from `vexa-review` to `Krafts-Meetings` for clarity?
- Should the dashboard be extended in Vexa, or should v1 expose workflow APIs only?
- Which local LLM API shape should be targeted first: OpenAI-compatible, Ollama, or another internal endpoint?
- Which SMTP provider/server will be used for first real verification?
- Should Docker Compose plugin installation be handled on this machine, or should compose validation run on the target VM?
- OAuth start/callback endpoints now exist; automatic access-token refresh before provider calls is still pending.
- Transcript retrieval and Vexa completion webhook processing are still pending.
