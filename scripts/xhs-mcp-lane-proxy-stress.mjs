#!/usr/bin/env node

import http from "node:http";
import { spawn } from "node:child_process";
import { once } from "node:events";

function startServer(handler) {
  return new Promise((resolve, reject) => {
    const server = http.createServer(handler);
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      resolve({ server, port: address.port });
    });
  });
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (chunk) => {
      raw += chunk;
    });
    req.on("end", () => {
      try {
        resolve(raw ? JSON.parse(raw) : {});
      } catch (err) {
        reject(err);
      }
    });
    req.on("error", reject);
  });
}

async function waitForLog(stream, pattern, timeoutMs = 5000) {
  let buffer = "";
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const remaining = Math.max(1, deadline - Date.now());
    const chunk = await Promise.race([
      once(stream, "data").then(([data]) => String(data)),
      new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), remaining)),
    ]);
    buffer += chunk;
    if (buffer.includes(pattern)) {
      return buffer;
    }
  }
  throw new Error(`did not observe pattern "${pattern}"`);
}

async function main() {
  const upstreamStats = new Map();

  const upstream = await startServer(async (req, res) => {
    const payload = await readJson(req);
    const bot = String(req.url || "").split("/").filter(Boolean).at(-1) || "unknown";
    const label = String(payload.label || "unnamed");
    const delayMs = Number(payload.delayMs || 150);
    const state = upstreamStats.get(bot) || { active: 0, maxActive: 0, starts: [] };

    state.active += 1;
    state.maxActive = Math.max(state.maxActive, state.active);
    state.starts.push({ label, at: Date.now() });
    upstreamStats.set(bot, state);

    await new Promise((resolve) => setTimeout(resolve, delayMs));

    state.active -= 1;
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true, bot, label }));
  });

  const proxyPort = upstream.port + 1;
  const child = spawn(process.execPath, ["/home/rooot/.openclaw/scripts/xhs-mcp-lane-proxy.mjs"], {
    env: {
      ...process.env,
      XHS_MCP_PROXY_HOST: "127.0.0.1",
      XHS_MCP_PROXY_PORT: String(proxyPort),
      XHS_MCP_UPSTREAM: `http://127.0.0.1:${upstream.port}`,
      XHS_MCP_PROXY_TIMEOUT_MS: "10000",
    },
    stdio: ["ignore", "pipe", "pipe"],
  });

  try {
    await waitForLog(child.stdout, "listening on");

    const requests = [];

    for (let i = 0; i < 20; i += 1) {
      requests.push(
        fetch(`http://127.0.0.1:${proxyPort}/mcp/bot3`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ label: `bot3-${i}`, delayMs: 120 }),
        }).then((r) => r.json()),
      );
    }

    for (let i = 0; i < 20; i += 1) {
      const bot = `bot${(i % 5) + 10}`;
      requests.push(
        fetch(`http://127.0.0.1:${proxyPort}/mcp/${bot}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ label: `${bot}-${i}`, delayMs: 120 }),
        }).then((r) => r.json()),
      );
    }

    await Promise.all(requests);

    const bot3 = upstreamStats.get("bot3") || { maxActive: 0 };
    const crossBotMax = Math.max(
      ...Array.from(upstreamStats.entries())
        .filter(([bot]) => bot !== "bot3")
        .map(([, state]) => state.maxActive),
      0,
    );
    const totalBotsSeen = upstreamStats.size;

    const result = {
      bot3MaxActive: bot3.maxActive,
      crossBotMaxActive: crossBotMax,
      totalBotsSeen,
      ok: bot3.maxActive === 1 && totalBotsSeen >= 6,
    };

    console.log(JSON.stringify(result, null, 2));

    if (!result.ok) {
      process.exitCode = 1;
    }
  } finally {
    child.kill("SIGTERM");
    upstream.server.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
