# Krafts Meetings Cloudflare Worker

Edge entrypoint for the Cloudflare-first control plane. The Worker forwards public `/workflow/*` traffic to the self-hosted `workflow-api` through the hostname exposed by Cloudflare Tunnel.

## Routes

The Worker forwards:

- `GET /workflow/oauth/{provider}/callback`
- `GET /workflow/oauth/{provider}/start`
- `POST /workflow/meetings`
- `GET /workflow/meetings`
- `POST /workflow/webhooks/vexa/meeting-completed`
- `POST /workflow/mail/test`

Webhook bodies are streamed to `workflow-api`; the Worker does not persist transcript text or queue payloads.

## Configuration

Non-secret vars live in `wrangler.jsonc`:

- `WORKFLOW_API_URL`: Tunnel-backed URL for `workflow-api`
- `CORS_ALLOW_ORIGIN`: optional dashboard origin

Secrets must be set with Wrangler:

```bash
wrangler secret put WORKER_SHARED_SECRET
```

Set the same value on the VM as `WORKFLOW_EDGE_SHARED_SECRET`. When that env var is configured, `workflow-api` rejects `/workflow/*` requests that do not include the Worker header.

## Local Checks

```bash
npm test
```

Deploy after setting the real Tunnel hostname and secret:

```bash
wrangler deploy
```
