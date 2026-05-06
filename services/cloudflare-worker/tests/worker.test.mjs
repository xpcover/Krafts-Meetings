import assert from "node:assert/strict";
import test from "node:test";

import { buildUpstreamRequest, handleRequest } from "../src/index.js";

const env = {
  WORKFLOW_API_URL: "https://workflow.internal.example.com",
  WORKER_SHARED_SECRET: "edge-secret",
  CORS_ALLOW_ORIGIN: "https://app.example.com",
};

test("buildUpstreamRequest forwards workflow path and shared secret", async () => {
  const request = new Request("https://meetings.example.com/workflow/meetings?user_id=1", {
    method: "GET",
    headers: { authorization: "Bearer user-token" },
  });

  const upstream = buildUpstreamRequest(request, env);

  assert.equal(upstream.url, "https://workflow.internal.example.com/workflow/meetings?user_id=1");
  assert.equal(upstream.headers.get("authorization"), "Bearer user-token");
  assert.equal(upstream.headers.get("x-krafts-edge-secret"), "edge-secret");
});

test("handleRequest rejects unsupported paths before forwarding", async () => {
  const response = await handleRequest(new Request("https://meetings.example.com/nope"), env);

  assert.equal(response.status, 404);
  assert.equal(response.headers.get("access-control-allow-origin"), "https://app.example.com");
});

test("handleRequest forwards Vexa webhook signature headers", async (t) => {
  const previousFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = previousFetch;
  });

  let forwarded;
  globalThis.fetch = async (request) => {
    forwarded = request;
    return new Response("ok", { status: 200 });
  };

  const response = await handleRequest(
    new Request("https://meetings.example.com/workflow/webhooks/vexa/meeting-completed", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-webhook-signature": "sig",
        "x-webhook-timestamp": "123",
      },
      body: JSON.stringify({ event_type: "meeting.completed" }),
    }),
    env,
  );

  assert.equal(response.status, 200);
  assert.equal(forwarded.headers.get("x-webhook-signature"), "sig");
  assert.equal(forwarded.headers.get("x-webhook-timestamp"), "123");
  assert.equal(forwarded.headers.get("x-krafts-edge-secret"), "edge-secret");
});
