#!/usr/bin/env node
/**
 * Tunnel Client — runs on the office machine, connects to the cloud
 * commercial server via HTTP long-polling.
 *
 * 1. GET /tunnel/poll  — long-poll for RPC requests from the cloud
 * 2. Execute locally (exec/fetch/readFile/tailFile)
 * 3. POST /tunnel/result — send results back
 *
 * Usage:
 *   TUNNEL_URL=http://118.196.119.223:18080 TUNNEL_TOKEN=xxx node index.js
 */
import { spawn } from "child_process";
import fs from "fs";

const TUNNEL_URL = (process.env.TUNNEL_URL || "http://localhost:18080").replace(/\/+$/, "");
const TUNNEL_TOKEN = process.env.TUNNEL_TOKEN || "";
const POLL_RETRY_BASE_MS = 1000;
const POLL_RETRY_MAX_MS = 15000;

/** @type {Map<string, () => void>} active tail watchers — reqId → stopFn */
const activeTails = new Map();

let pollRetryDelay = POLL_RETRY_BASE_MS;

function log(...args) {
  console.log(`[tunnel-client ${new Date().toISOString()}]`, ...args);
}

// ---- HTTP helpers ----------------------------------------------------------

const headers = {
  "Content-Type": "application/json",
  ...(TUNNEL_TOKEN ? { "X-Tunnel-Token": TUNNEL_TOKEN } : {}),
};

async function postResults(results) {
  try {
    const res = await fetch(`${TUNNEL_URL}/tunnel/result`, {
      method: "POST",
      headers,
      body: JSON.stringify(results),
    });
    if (!res.ok) {
      log("postResults error:", res.status, await res.text().catch(() => ""));
    }
  } catch (err) {
    log("postResults failed:", err.message);
  }
}

async function sendResult(msg) {
  await postResults(msg);
}

// ---- Poll loop -------------------------------------------------------------

async function pollLoop() {
  log("Starting poll loop to", TUNNEL_URL);

  while (true) {
    try {
      const res = await fetch(`${TUNNEL_URL}/tunnel/poll`, {
        headers,
        signal: AbortSignal.timeout(30_000),
      });

      if (!res.ok) {
        const body = await res.text().catch(() => "");
        log("Poll error:", res.status, body.slice(0, 200));
        await sleep(pollRetryDelay);
        pollRetryDelay = Math.min(pollRetryDelay * 2, POLL_RETRY_MAX_MS);
        continue;
      }

      pollRetryDelay = POLL_RETRY_BASE_MS; // reset on success

      const data = await res.json();
      const requests = data.requests || [];

      if (requests.length > 0) {
        log(`Received ${requests.length} request(s)`);
      }

      for (const req of requests) {
        // Handle each request concurrently (don't block the poll loop)
        handleRequest(req);
      }
    } catch (err) {
      if (err.name === "TimeoutError" || err.name === "AbortError") {
        // Normal — poll timed out, just retry
        continue;
      }
      log("Poll error:", err.message);
      await sleep(pollRetryDelay);
      pollRetryDelay = Math.min(pollRetryDelay * 2, POLL_RETRY_MAX_MS);
    }
  }
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// ---- Request handler -------------------------------------------------------

function handleRequest(msg) {
  if (msg.type === "stopTail") {
    const stop = activeTails.get(msg.reqId);
    if (stop) { stop(); activeTails.delete(msg.reqId); }
    return;
  }

  switch (msg.type) {
    case "exec":
      handleExec(msg);
      break;
    case "fetch":
      handleFetch(msg);
      break;
    case "readFile":
      handleReadFile(msg);
      break;
    case "tailFile":
      handleTailFile(msg);
      break;
    default:
      log("Unknown request type:", msg.type);
  }
}

// ---- exec handler ----------------------------------------------------------

function handleExec(msg) {
  const { reqId, command, args, timeout } = msg;
  const timeoutMs = timeout || 300_000;

  log(`exec: ${command} ${(args || []).slice(0, 3).join(" ")}...`);

  const child = spawn(command, args || [], {
    stdio: ["ignore", "pipe", "pipe"],
    detached: true,
  });

  let stdout = "";
  let stderr = "";

  child.stdout.on("data", (d) => {
    const chunk = d.toString();
    stdout += chunk;
    sendResult({ reqId, chunk, stream: "stdout" });
  });

  child.stderr.on("data", (d) => {
    const chunk = d.toString();
    stderr += chunk;
    sendResult({ reqId, chunk, stream: "stderr" });
  });

  let done = false;
  const finish = (result) => {
    if (done) return;
    done = true;
    clearTimeout(timer);
    sendResult({ reqId, done: true, ...result });
  };

  const timer = setTimeout(() => {
    try { process.kill(-child.pid, "SIGKILL"); } catch {}
    finish({ error: "timeout", code: -1, stdout: stdout.slice(-2000), stderr: stderr.slice(-500) });
  }, timeoutMs);

  child.on("close", (code) => {
    finish({ code, stdout, stderr });
  });

  child.on("error", (err) => {
    finish({ error: err.message, code: -1, stdout, stderr });
  });

  child.unref();
}

// ---- fetch handler ---------------------------------------------------------

async function handleFetch(msg) {
  const { reqId, url, method, headers: reqHeaders, body } = msg;
  log(`fetch: ${method || "GET"} ${url}`);

  try {
    const res = await fetch(url, {
      method: method || "GET",
      headers: reqHeaders || {},
      body: body || undefined,
    });

    const resBody = await res.text();
    const resHeaders = {};
    for (const [k, v] of res.headers.entries()) {
      resHeaders[k] = v;
    }

    sendResult({ reqId, status: res.status, headers: resHeaders, body: resBody });
  } catch (err) {
    sendResult({ reqId, error: err.message });
  }
}

// ---- readFile handler ------------------------------------------------------

function handleReadFile(msg) {
  const { reqId, path: filePath } = msg;
  try {
    const content = fs.readFileSync(filePath, "utf8");
    sendResult({ reqId, content });
  } catch (err) {
    sendResult({ reqId, error: err.message });
  }
}

// ---- tailFile handler ------------------------------------------------------

function handleTailFile(msg) {
  const { reqId, path: filePath } = msg;
  let lastSize = 0;
  try { lastSize = fs.statSync(filePath).size; } catch { lastSize = 0; }
  let buffer = "";
  let stopped = false;

  const drainOnce = () => {
    let stat;
    try { stat = fs.statSync(filePath); } catch { return; }
    if (stat.size <= lastSize) return;
    let fd;
    try {
      fd = fs.openSync(filePath, "r");
      const len = stat.size - lastSize;
      const buf = Buffer.alloc(len);
      fs.readSync(fd, buf, 0, len, lastSize);
      lastSize = stat.size;
      buffer += buf.toString("utf8");
    } catch { return; }
    finally { if (fd !== undefined) try { fs.closeSync(fd); } catch {} }

    let idx;
    while ((idx = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 1);
      if (line) {
        sendResult({ reqId, type: "tailLine", line });
      }
    }
  };

  const interval = setInterval(() => {
    if (stopped) return;
    drainOnce();
  }, 200);

  const stop = () => {
    stopped = true;
    clearInterval(interval);
    drainOnce();
    sendResult({ reqId, type: "tailEnd" });
  };

  activeTails.set(reqId, stop);
}

// ---- Start -----------------------------------------------------------------

pollLoop();

process.on("SIGINT", () => { log("Shutting down..."); process.exit(0); });
process.on("SIGTERM", () => { log("Shutting down..."); process.exit(0); });
