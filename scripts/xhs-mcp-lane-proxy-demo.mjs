#!/usr/bin/env node

import http from "node:http";
import { URL } from "node:url";

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

function startServer(handler) {
  return new Promise((resolve, reject) => {
    const server = http.createServer(handler);
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      resolve({
        server,
        port: address.port,
      });
    });
  });
}

function makeLaneRunner() {
  const lanes = new Map();

  return async function runInLane(key, job) {
    const previous = lanes.get(key) || Promise.resolve();
    const current = previous
      .catch(() => {})
      .then(job);

    lanes.set(key, current);

    try {
      return await current;
    } finally {
      if (lanes.get(key) === current) {
        lanes.delete(key);
      }
    }
  };
}

async function main() {
  const upstreamEvents = [];
  const runInLane = makeLaneRunner();

  const upstream = await startServer(async (req, res) => {
    const payload = await readJson(req);
    const url = new URL(req.url, "http://127.0.0.1");
    const bot = url.pathname.split("/").pop() || "unknown";
    const label = String(payload.label || "unnamed");
    const delayMs = Number(payload.delayMs || 0);
    const startedAt = Date.now();

    upstreamEvents.push({
      type: "start",
      bot,
      label,
      at: startedAt,
    });

    await new Promise((resolve) => setTimeout(resolve, delayMs));

    const endedAt = Date.now();
    upstreamEvents.push({
      type: "end",
      bot,
      label,
      at: endedAt,
    });

    const body = JSON.stringify({
      ok: true,
      bot,
      label,
      startedAt,
      endedAt,
    });

    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(body);
  });

  const proxy = await startServer(async (req, res) => {
    const payload = await readJson(req);
    const url = new URL(req.url, "http://127.0.0.1");
    const parts = url.pathname.split("/").filter(Boolean);
    const bot = parts.at(-1) || "unknown";

    try {
      const response = await runInLane(bot, async () => {
        return await fetch(`http://127.0.0.1:${upstream.port}${url.pathname}`, {
          method: req.method || "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      });

      const text = await response.text();
      res.writeHead(response.status, {
        "Content-Type": response.headers.get("content-type") || "application/json",
      });
      res.end(text);
    } catch (err) {
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: String(err) }));
    }
  });

  const requests = [
    fetch(`http://127.0.0.1:${proxy.port}/mcp/bot3`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: "bot3-A", delayMs: 700 }),
    }).then((r) => r.json()),
    fetch(`http://127.0.0.1:${proxy.port}/mcp/bot3`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: "bot3-B", delayMs: 200 }),
    }).then((r) => r.json()),
    fetch(`http://127.0.0.1:${proxy.port}/mcp/bot7`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: "bot7-A", delayMs: 300 }),
    }).then((r) => r.json()),
  ];

  const [bot3A, bot3B, bot7A] = await Promise.all(requests);

  upstream.server.close();
  proxy.server.close();

  const starts = Object.fromEntries(
    upstreamEvents.filter((e) => e.type === "start").map((e) => [e.label, e.at]),
  );
  const ends = Object.fromEntries(
    upstreamEvents.filter((e) => e.type === "end").map((e) => [e.label, e.at]),
  );

  const sameBotSerialized = starts["bot3-B"] >= ends["bot3-A"];
  const crossBotParallel = starts["bot7-A"] < ends["bot3-A"];

  console.log("Proxy demo result");
  console.log(JSON.stringify(
    {
      sameBotSerialized,
      crossBotParallel,
      upstreamEvents,
      responses: [bot3A, bot3B, bot7A],
    },
    null,
    2,
  ));

  if (!sameBotSerialized || !crossBotParallel) {
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
