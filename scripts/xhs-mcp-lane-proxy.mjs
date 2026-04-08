#!/usr/bin/env node

import http from "node:http";

const LISTEN_HOST = process.env.XHS_MCP_PROXY_HOST || "127.0.0.1";
const LISTEN_PORT = Number(process.env.XHS_MCP_PROXY_PORT || "18061");
const UPSTREAM_BASE = process.env.XHS_MCP_UPSTREAM || "http://127.0.0.1:18060";
const REQUEST_TIMEOUT_MS = Number(process.env.XHS_MCP_PROXY_TIMEOUT_MS || "300000");

const lanes = new Map();
const laneStats = new Map();

function nowIso() {
  return new Date().toISOString();
}

function log(message, extra) {
  if (extra === undefined) {
    console.log(`[xhs-mcp-lane-proxy] ${nowIso()} ${message}`);
    return;
  }
  console.log(`[xhs-mcp-lane-proxy] ${nowIso()} ${message}`, extra);
}

function isHopByHopHeader(name) {
  const lower = name.toLowerCase();
  return (
    lower === "connection" ||
    lower === "keep-alive" ||
    lower === "proxy-authenticate" ||
    lower === "proxy-authorization" ||
    lower === "te" ||
    lower === "trailers" ||
    lower === "transfer-encoding" ||
    lower === "upgrade" ||
    lower === "host" ||
    lower === "content-length"
  );
}

function readRequestBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
    req.on("aborted", () => reject(new Error("client aborted request")));
  });
}

function normalizeRequestHeaders(headers) {
  const out = {};
  for (const [key, value] of Object.entries(headers)) {
    if (value == null || isHopByHopHeader(key)) {
      continue;
    }
    if (Array.isArray(value)) {
      out[key] = value.map((item) => String(item));
      continue;
    }
    out[key] = String(value);
  }
  return out;
}

function writeResponseHeaders(res, upstreamHeaders) {
  for (const [key, value] of Object.entries(upstreamHeaders)) {
    if (isHopByHopHeader(key)) {
      continue;
    }
    if (value == null) {
      continue;
    }
    res.setHeader(key, value);
  }
}

function extractLaneKey(urlPath) {
  const parts = String(urlPath || "")
    .split("/")
    .filter(Boolean);
  if (parts[0] !== "mcp" || !parts[1]) {
    return null;
  }
  return decodeURIComponent(parts[1]);
}

function parseJsonBody(rawBody, headers) {
  if (!rawBody.length) {
    return null;
  }
  const contentType = String(headers["content-type"] || "");
  if (!contentType.includes("application/json")) {
    return null;
  }
  try {
    return JSON.parse(rawBody.toString("utf8"));
  } catch {
    return null;
  }
}

function shouldSerializeToolCall(req, laneKey, parsedBody) {
  if (!laneKey) {
    return false;
  }
  if ((req.method || "GET").toUpperCase() !== "POST") {
    return false;
  }
  if (!parsedBody) {
    return false;
  }

  const messages = Array.isArray(parsedBody) ? parsedBody : [parsedBody];
  if (!messages.length) {
    return false;
  }

  // Only serialize actual MCP tool invocations. Transport/session traffic such as
  // initialize, notifications, stream setup, and polling must stay concurrent.
  return messages.some((message) => {
    if (!message || typeof message !== "object") {
      return false;
    }
    return message.method === "tools/call";
  });
}

function getLaneState(key) {
  let state = laneStats.get(key);
  if (!state) {
    state = { pending: 0, active: false };
    laneStats.set(key, state);
  }
  return state;
}

async function runInLane(key, job) {
  const previous = lanes.get(key) || Promise.resolve();
  const state = getLaneState(key);
  state.pending += 1;

  const current = previous
    .catch(() => {})
    .then(async () => {
      state.pending -= 1;
      state.active = true;
      try {
        return await job();
      } finally {
        state.active = false;
        if (!state.pending) {
          laneStats.delete(key);
        }
      }
    });

  lanes.set(key, current);

  try {
    return await current;
  } finally {
    if (lanes.get(key) === current) {
      lanes.delete(key);
    }
  }
}

async function forwardRequest(req, res, laneKey) {
  const rawBody = await readRequestBody(req);
  const parsedBody = parseJsonBody(rawBody, req.headers);
  const useLane = shouldSerializeToolCall(req, laneKey, parsedBody);
  const targetUrl = new URL(req.url || "/", UPSTREAM_BASE);
  const headers = normalizeRequestHeaders(req.headers);

  const job = async () => {
    await new Promise((resolve, reject) => {
      let settled = false;
      const finish = (err) => {
        if (settled) {
          return;
        }
        settled = true;
        if (err) {
          reject(err);
          return;
        }
        resolve();
      };

      const upstreamReq = http.request(
        targetUrl,
        {
          method: req.method || "GET",
          headers,
        },
        (upstreamRes) => {
          res.statusCode = upstreamRes.statusCode || 502;
          res.statusMessage = upstreamRes.statusMessage || "";
          writeResponseHeaders(res, upstreamRes.headers);

          upstreamRes.on("error", finish);
          res.on("error", finish);
          res.on("close", () => {
            upstreamRes.destroy();
            finish();
          });
          upstreamRes.on("end", () => finish());
          upstreamRes.pipe(res);
        },
      );

      upstreamReq.on("error", finish);
      upstreamReq.setTimeout(REQUEST_TIMEOUT_MS, () => {
        upstreamReq.destroy(new Error(`upstream request timeout after ${REQUEST_TIMEOUT_MS}ms`));
      });

      req.on("aborted", () => {
        upstreamReq.destroy(new Error("client aborted request"));
      });

      if (
        (req.method || "GET").toUpperCase() === "GET" ||
        (req.method || "GET").toUpperCase() === "HEAD" ||
        rawBody.length === 0
      ) {
        upstreamReq.end();
        return;
      }

      upstreamReq.end(rawBody);
    });
  };

  if (useLane) {
    log(`serialize tools/call lane=${laneKey}`);
    await runInLane(laneKey, job);
    return;
  }
  await job();
}

const server = http.createServer(async (req, res) => {
  if (!req.url) {
    res.writeHead(400, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "missing request url" }));
    return;
  }

  if (req.url === "/_proxy/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        ok: true,
        upstream: UPSTREAM_BASE,
        lanes: Array.from(laneStats.entries()).map(([key, value]) => ({
          key,
          pending: value.pending,
          active: value.active,
        })),
      }),
    );
    return;
  }

  const laneKey = extractLaneKey(req.url);
  try {
    await forwardRequest(req, res, laneKey);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    log(`request failed${laneKey ? ` lane=${laneKey}` : ""}: ${message}`);
    if (!res.headersSent) {
      res.writeHead(502, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: message }));
      return;
    }
    res.destroy(err instanceof Error ? err : new Error(message));
  }
});

server.listen(LISTEN_PORT, LISTEN_HOST, () => {
  log(`listening on http://${LISTEN_HOST}:${LISTEN_PORT} -> ${UPSTREAM_BASE}`);
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    log(`received ${signal}, shutting down`);
    server.close(() => process.exit(0));
  });
}
