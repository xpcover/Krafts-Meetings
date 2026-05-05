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
