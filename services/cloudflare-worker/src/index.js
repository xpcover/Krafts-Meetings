const FORWARDED_PREFIX = "/workflow";

function jsonResponse(status, payload) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
    },
  });
}

function corsHeaders(env) {
  if (!env.CORS_ALLOW_ORIGIN) {
    return {};
  }
  return {
    "access-control-allow-origin": env.CORS_ALLOW_ORIGIN,
    "access-control-allow-methods": "GET,POST,PATCH,OPTIONS",
    "access-control-allow-headers": "authorization,content-type,x-webhook-signature,x-webhook-timestamp",
    "access-control-max-age": "86400",
  };
}

function withCors(response, env) {
  const headers = new Headers(response.headers);
  for (const [key, value] of Object.entries(corsHeaders(env))) {
    headers.set(key, value);
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

function requireEnv(env) {
  if (!env.WORKFLOW_API_URL) {
    return "WORKFLOW_API_URL is not configured";
  }
  if (!env.WORKER_SHARED_SECRET) {
    return "WORKER_SHARED_SECRET is not configured";
  }
  return null;
}

function forwardedHeaders(request, env) {
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  const authorization = request.headers.get("authorization");
  const webhookSignature = request.headers.get("x-webhook-signature");
  const webhookTimestamp = request.headers.get("x-webhook-timestamp");

  if (contentType) {
    headers.set("content-type", contentType);
  }
  if (authorization) {
    headers.set("authorization", authorization);
  }
  if (webhookSignature) {
    headers.set("x-webhook-signature", webhookSignature);
  }
  if (webhookTimestamp) {
    headers.set("x-webhook-timestamp", webhookTimestamp);
  }
  headers.set("x-krafts-edge-secret", env.WORKER_SHARED_SECRET);
  headers.set("x-forwarded-host", new URL(request.url).host);
  headers.set("x-forwarded-proto", "https");
  return headers;
}

export function buildUpstreamRequest(request, env) {
  const url = new URL(request.url);
  const upstream = new URL(env.WORKFLOW_API_URL);
  upstream.pathname = `${upstream.pathname.replace(/\/$/, "")}${url.pathname}`;
  upstream.search = url.search;

  const init = {
    method: request.method,
    headers: forwardedHeaders(request, env),
    redirect: "manual",
  };
  if (!["GET", "HEAD"].includes(request.method)) {
    init.body = request.body;
    init.duplex = "half";
  }
  return new Request(upstream, init);
}

function validateRoute(request) {
  const url = new URL(request.url);
  if (!url.pathname.startsWith(FORWARDED_PREFIX)) {
    return jsonResponse(404, { error: "Not found" });
  }
  if (url.pathname === "/workflow/webhooks/vexa/meeting-completed" && request.method !== "POST") {
    return jsonResponse(405, { error: "Method not allowed" });
  }
  if (url.pathname.startsWith("/workflow/oauth/") && !["GET", "OPTIONS"].includes(request.method)) {
    return jsonResponse(405, { error: "Method not allowed" });
  }
  return null;
}

export async function handleRequest(request, env) {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders(env) });
  }

  const missing = requireEnv(env);
  if (missing) {
    return jsonResponse(500, { error: missing });
  }

  const routeError = validateRoute(request);
  if (routeError) {
    return withCors(routeError, env);
  }

  try {
    const upstreamResponse = await fetch(buildUpstreamRequest(request, env));
    return withCors(upstreamResponse, env);
  } catch (error) {
    console.error(JSON.stringify({ message: "workflow_forward_failed", error: String(error) }));
    return withCors(jsonResponse(502, { error: "Workflow API unavailable" }), env);
  }
}

export default {
  fetch(request, env) {
    return handleRequest(request, env);
  },
};
