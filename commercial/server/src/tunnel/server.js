/**
 * Tunnel Server — HTTP long-polling transport.
 *
 * The office machine's tunnel-client polls GET /tunnel/poll to receive RPC
 * requests, and posts results back via POST /tunnel/result. No WebSocket
 * needed — works through any HTTP-only SLB/proxy.
 *
 * Public API (used by business code):
 *   isConnected()                  — true if client is polling
 *   exec(cmd, args, opts)          — run a command on the office machine
 *   tunnelFetch(url, fetchOpts)    — forward an HTTP request
 *   readFile(path)                 — read a file
 *   tailFile(path, onLine)         — tail a file, returns stop()
 *   attachToExpress(app)           — mount /tunnel/* routes
 */
import crypto from "crypto";

const TUNNEL_TOKEN = process.env.TUNNEL_TOKEN || "";
const POLL_TIMEOUT_MS = 25_000; // long-poll hang time (< SLB idle timeout)
const CLIENT_ALIVE_MS = 35_000; // consider disconnected after this silence

let lastPollTime = 0;

/** Queued requests waiting to be delivered to the client via poll */
const outbox = [];

/** Waiting poll response — at most one at a time */
let pendingPollRes = null;

/** @type {Map<string, { resolve, reject, onChunk?, timeout }>} */
const pending = new Map();

/** @type {Map<string, (line: string) => void>} */
const tailCallbacks = new Map();

export function isConnected() {
  return Date.now() - lastPollTime < CLIENT_ALIVE_MS;
}

function nextReqId() {
  return crypto.randomBytes(8).toString("hex");
}

// ---- Enqueue a request for the client to pick up via poll ------------------

function enqueueForClient(msg) {
  outbox.push(msg);
  flushOutbox();
}

function flushOutbox() {
  if (!pendingPollRes || outbox.length === 0) return;
  const batch = outbox.splice(0);
  try {
    pendingPollRes.json({ requests: batch });
  } catch {}
  pendingPollRes = null;
}

// ---- RPC helpers (same public API as the old WebSocket version) ------------

function sendRequest(msg, timeoutMs = 300_000) {
  return new Promise((resolve, reject) => {
    if (!isConnected()) {
      return reject(new Error("隧道未连接 — 办公电脑的 tunnel-client 不在线"));
    }
    const reqId = nextReqId();
    msg.reqId = reqId;
    const timeout = setTimeout(() => {
      pending.delete(reqId);
      reject(new Error(`隧道请求超时 (${timeoutMs}ms)`));
    }, timeoutMs);
    pending.set(reqId, { resolve, reject, timeout });
    enqueueForClient(msg);
  });
}

export function exec(command, args, opts = {}) {
  const timeoutMs = opts.timeout || 300_000;
  return new Promise((resolve, reject) => {
    if (!isConnected()) {
      return reject(new Error("隧道未连接 — 办公电脑的 tunnel-client 不在线"));
    }
    const reqId = nextReqId();
    const timeout = setTimeout(() => {
      pending.delete(reqId);
      reject(new Error(`隧道 exec 超时 (${timeoutMs}ms)`));
    }, timeoutMs);
    pending.set(reqId, {
      resolve,
      reject,
      timeout,
      onChunk: opts.onChunk || null,
    });
    enqueueForClient({
      type: "exec",
      reqId,
      command,
      args,
      timeout: timeoutMs,
    });
  });
}

export function tunnelFetch(url, fetchOpts = {}) {
  return sendRequest({
    type: "fetch",
    url,
    method: fetchOpts.method || "GET",
    headers: fetchOpts.headers || {},
    body: fetchOpts.body || null,
  }, fetchOpts.timeout || 120_000);
}

export function readFile(filePath) {
  return sendRequest({ type: "readFile", path: filePath }, 30_000);
}

export function tailFile(filePath, onLine) {
  if (!isConnected()) {
    console.error("[tunnel] tailFile: not connected");
    return () => {};
  }
  const reqId = nextReqId();
  tailCallbacks.set(reqId, onLine);
  enqueueForClient({ type: "tailFile", reqId, path: filePath });
  return () => {
    tailCallbacks.delete(reqId);
    enqueueForClient({ type: "stopTail", reqId });
  };
}

// ---- Handle results posted back by the client ------------------------------

function handleResult(msg) {
  const reqId = msg.reqId;
  if (!reqId) return;

  // Tail line events
  if (msg.type === "tailLine") {
    const cb = tailCallbacks.get(reqId);
    if (cb) cb(msg.line);
    return;
  }
  if (msg.type === "tailEnd") {
    tailCallbacks.delete(reqId);
    return;
  }

  const entry = pending.get(reqId);
  if (!entry) return;

  // Streaming exec chunk (not final)
  if (msg.chunk !== undefined && !msg.done) {
    if (entry.onChunk) entry.onChunk(msg.stream, msg.chunk);
    return;
  }

  // Final response
  pending.delete(reqId);
  clearTimeout(entry.timeout);
  if (msg.error) {
    entry.reject(new Error(msg.error));
  } else {
    entry.resolve(msg);
  }
}

// ---- Express routes --------------------------------------------------------

function checkToken(req) {
  if (!TUNNEL_TOKEN) return true;
  const token = req.headers["x-tunnel-token"] || req.query?.token;
  return token === TUNNEL_TOKEN;
}

export function attachToExpress(app) {
  // Long-poll: client hangs here waiting for requests
  app.get("/tunnel/poll", (req, res) => {
    if (!checkToken(req)) {
      return res.status(401).json({ error: "Invalid token" });
    }

    lastPollTime = Date.now();

    // If there was a previous pending poll, release it with empty batch
    if (pendingPollRes) {
      try { pendingPollRes.json({ requests: [] }); } catch {}
      pendingPollRes = null;
    }

    // If there are queued requests, return immediately
    if (outbox.length > 0) {
      const batch = outbox.splice(0);
      return res.json({ requests: batch });
    }

    // Otherwise hang until a request arrives or timeout
    pendingPollRes = res;
    const timer = setTimeout(() => {
      if (pendingPollRes === res) {
        pendingPollRes = null;
        try { res.json({ requests: [] }); } catch {}
      }
    }, POLL_TIMEOUT_MS);

    res.on("close", () => {
      clearTimeout(timer);
      if (pendingPollRes === res) pendingPollRes = null;
    });
  });

  // Client posts results (may be a batch)
  app.post("/tunnel/result", (req, res) => {
    if (!checkToken(req)) {
      return res.status(401).json({ error: "Invalid token" });
    }

    lastPollTime = Date.now();

    const results = Array.isArray(req.body) ? req.body : [req.body];
    for (const msg of results) {
      handleResult(msg);
    }
    res.json({ ok: true });
  });

  // Health/status endpoint for tunnel
  app.get("/tunnel/status", (req, res) => {
    res.json({
      connected: isConnected(),
      lastPollAge: Date.now() - lastPollTime,
      pendingRequests: pending.size,
      outboxSize: outbox.length,
      activeTails: tailCallbacks.size,
    });
  });

  console.log("[tunnel] HTTP long-polling routes mounted on /tunnel/*");
}

// Keep backward compat: attachToServer still works but just calls attachToExpress
export function attachToServer(httpServer) {
  // No-op for HTTP mode — use attachToExpress(app) instead
  console.log("[tunnel] attachToServer called (no-op in HTTP polling mode)");
}
