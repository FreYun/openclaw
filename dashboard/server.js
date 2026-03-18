#!/usr/bin/env node
// Agent Message Dashboard Server
// Usage: node server.js [port]  (default: 18888)

const http = require("http");
const fs = require("fs");
const path = require("path");
const { execSync, execFile } = require("child_process");

const PORT = parseInt(process.argv[2] || "18888");
const PUBLISH_QUEUE = "/home/rooot/.openclaw/publish-queue";
const AGENTS_DIR = "/home/rooot/.openclaw/agents";
const CRON_DIR = "/home/rooot/.openclaw/cron";
const OPENCLAW_JSON = "/home/rooot/.openclaw/openclaw.json";

// Server-side cache: refresh at most every 10s
let cachedData = null;
let cacheTime = 0;
const CACHE_TTL = 10000;

function redis(cmd) {
  try {
    return execSync(`redis-cli ${cmd}`, { encoding: "utf8", timeout: 3000 }).trim();
  } catch { return ""; }
}

function getMessages(limit = 200) {
  // Get all message IDs from all inboxes
  const inboxKeys = redis('KEYS "agentmsg:inbox:*"').split("\n").filter(Boolean);
  const msgIds = new Set();

  for (const key of inboxKeys) {
    const entries = redis(`XREVRANGE ${key} + - COUNT ${limit}`).split("\n").filter(Boolean);
    for (let i = 0; i < entries.length; i++) {
      if (entries[i] === "message_id" && entries[i + 1]) {
        msgIds.add(entries[i + 1]);
      }
    }
  }

  // Also from outboxes
  const outboxKeys = redis('KEYS "agentmsg:outbox:*"').split("\n").filter(Boolean);
  for (const key of outboxKeys) {
    const entries = redis(`XREVRANGE ${key} + - COUNT ${limit}`).split("\n").filter(Boolean);
    for (let i = 0; i < entries.length; i++) {
      if (entries[i] === "message_id" && entries[i + 1]) {
        msgIds.add(entries[i + 1]);
      }
    }
  }

  // Fetch all message details in one Redis call using Lua script
  const fields = ["message_id", "from", "to", "type", "status", "content", "created_at", "reply_to_message_id", "trace", "metadata"];
  const messages = [];
  const idList = [...msgIds];

  // Lua script: batch HMGET and return JSON array of arrays
  const luaScript = `
    local r={}
    for i,id in ipairs(ARGV) do
      local d=redis.call("HMGET","agentmsg:detail:"..id,${fields.map(f => `"${f}"`).join(",")})
      r[#r+1]=cjson.encode(d)
    end
    return cjson.encode(r)
  `.replace(/\n/g, " ");

  try {
    const args = idList.join(" ");
    const raw = execSync(`redis-cli --json EVAL '${luaScript}' 0 ${args}`, {
      encoding: "utf8", timeout: 10000, maxBuffer: 10 * 1024 * 1024
    }).trim();
    const outer = JSON.parse(JSON.parse(raw));
    for (const item of outer) {
      const vals = typeof item === "string" ? JSON.parse(item) : item;
      const msg = {};
      for (let i = 0; i < fields.length; i++) {
        if (vals[i] !== null && vals[i] !== false) msg[fields[i]] = vals[i];
      }
      if (msg.message_id) {
        try { msg.trace = JSON.parse(msg.trace || "[]"); } catch { msg.trace = []; }
        try { msg.metadata = JSON.parse(msg.metadata || "{}"); } catch { msg.metadata = {}; }
        messages.push(msg);
      }
    }
  } catch (e) {
    // Fallback: fetch one by one with --json
    for (const id of idList) {
      try {
        const raw = execSync(`redis-cli --json HMGET agentmsg:detail:${id} ${fields.join(" ")}`, {
          encoding: "utf8", timeout: 3000
        }).trim();
        const vals = JSON.parse(raw);
        const msg = {};
        for (let i = 0; i < fields.length; i++) {
          if (vals[i] !== null) msg[fields[i]] = vals[i];
        }
        if (msg.message_id) {
          try { msg.trace = JSON.parse(msg.trace || "[]"); } catch { msg.trace = []; }
          try { msg.metadata = JSON.parse(msg.metadata || "{}"); } catch { msg.metadata = {}; }
          messages.push(msg);
        }
      } catch {}
    }
  }

  // Sort by created_at desc
  messages.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  return messages;
}

function getKnownAgentIds() {
  try {
    return fs.readdirSync(AGENTS_DIR).filter(d => {
      try { return fs.statSync(path.join(AGENTS_DIR, d)).isDirectory(); } catch { return false; }
    });
  } catch { return []; }
}

function getAgentStats() {
  const knownAgents = new Set(getKnownAgentIds());
  const inboxKeys = redis('KEYS "agentmsg:inbox:*"').split("\n").filter(Boolean);
  const outboxKeys = redis('KEYS "agentmsg:outbox:*"').split("\n").filter(Boolean);

  const stats = {};
  for (const key of inboxKeys) {
    const agent = key.replace("agentmsg:inbox:", "");
    if (!knownAgents.has(agent)) continue; // skip unknown agents
    if (!stats[agent]) stats[agent] = { inbox: 0, outbox: 0 };
    stats[agent].inbox = parseInt(redis(`XLEN ${key}`)) || 0;
  }
  for (const key of outboxKeys) {
    const agent = key.replace("agentmsg:outbox:", "");
    if (!knownAgents.has(agent)) continue; // skip unknown agents
    if (!stats[agent]) stats[agent] = { inbox: 0, outbox: 0 };
    stats[agent].outbox = parseInt(redis(`XLEN ${key}`)) || 0;
  }
  return stats;
}

function readPostMeta(filePath) {
  try {
    const content = fs.readFileSync(filePath, "utf8");
    const titleMatch = content.match(/^title:\s*"?(.+?)"?\s*$/m);
    const contentMatch = content.match(/^content:\s*"(.+?)"/m);
    return {
      title: titleMatch ? titleMatch[1] : "",
      summary: contentMatch ? contentMatch[1].slice(0, 60) : ""
    };
  } catch { return { title: "", summary: "" }; }
}

function getPublishQueue() {
  const result = { pending: [], publishing: [], published: [] };
  for (const status of Object.keys(result)) {
    const dir = path.join(PUBLISH_QUEUE, status);
    try {
      const entries = fs.readdirSync(dir)
        .filter(f => !f.startsWith("."))
        .sort()
        .reverse();
      result[status] = entries.map(f => {
        const fullPath = path.join(dir, f);
        const stat = fs.statSync(fullPath);
        let meta = { title: "", summary: "" };
        if (stat.isDirectory()) {
          const postMd = path.join(fullPath, "post.md");
          if (fs.existsSync(postMd)) meta = readPostMeta(postMd);
        } else if (f.endsWith(".md")) {
          meta = readPostMeta(fullPath);
        }
        return { name: f, ...meta };
      });
    } catch {}
  }
  return result;
}

function getCronJobs() {
  try {
    const data = fs.readFileSync(path.join(CRON_DIR, "jobs.json"), "utf8");
    return JSON.parse(data);
  } catch { return []; }
}

function getRecentCronRuns(limit = 30) {
  const runsDir = path.join(CRON_DIR, "runs");
  const runs = [];
  try {
    const files = fs.readdirSync(runsDir).filter(f => f.endsWith(".jsonl")).sort().reverse().slice(0, 5);
    for (const file of files) {
      const lines = fs.readFileSync(path.join(runsDir, file), "utf8").split("\n").filter(Boolean);
      for (const line of lines.slice(-limit)) {
        try { runs.push(JSON.parse(line)); } catch {}
      }
    }
  } catch {}
  runs.sort((a, b) => new Date(b.ts) - new Date(a.ts));
  return runs.slice(0, limit);
}

function getAgentSessions() {
  const agents = {};
  try {
    const dirs = fs.readdirSync(AGENTS_DIR);
    for (const dir of dirs) {
      const sessFile = path.join(AGENTS_DIR, dir, "sessions", "sessions.json");
      try {
        const data = JSON.parse(fs.readFileSync(sessFile, "utf8"));
        const sessions = Array.isArray(data) ? data : Object.values(data);
        const latest = sessions
          .filter(s => s.updatedAt)
          .sort((a, b) => b.updatedAt - a.updatedAt)[0];
        agents[dir] = {
          sessionCount: sessions.length,
          lastActive: latest ? new Date(latest.updatedAt).toISOString() : null,
          activeSession: latest?.sessionId || null
        };
      } catch {}
    }
  } catch {}
  return agents;
}

function getHeartbeatAgents() {
  try {
    const conf = JSON.parse(fs.readFileSync("/home/rooot/.openclaw/openclaw.json", "utf8"));
    const agents = new Set();
    for (const a of (conf.agents?.list || [])) {
      if (a.heartbeat) agents.add(a.id);
    }
    return agents;
  } catch { return new Set(); }
}

function getAllSessions() {
  const sessions = [];
  const hbAgents = getHeartbeatAgents();
  try {
    const dirs = fs.readdirSync(AGENTS_DIR);
    for (const dir of dirs) {
      const sessFile = path.join(AGENTS_DIR, dir, "sessions", "sessions.json");
      try {
        const data = JSON.parse(fs.readFileSync(sessFile, "utf8"));
        for (const [key, sess] of Object.entries(data)) {
          // Skip parent cron keys (keep only :run: entries to avoid duplicates)
          if (key.includes(":cron:") && !key.includes(":run:")) continue;

          // Parse source from key
          let source = "unknown";
          if (key.includes(":feishu:")) source = "feishu";
          else if (key.includes(":cron:")) source = "cron";
          else if (key.endsWith(":main")) {
            source = hbAgents.has(dir) ? "heartbeat" : "local";
          }
          else if (key.includes(":agent:")) source = "agent";

          // Parse chat type
          let chatType = sess.chatType || "";
          if (key.includes(":group:")) chatType = "group";
          else if (key.includes(":direct:")) chatType = "direct";

          sessions.push({
            agent: dir,
            sessionId: sess.sessionId || "",
            key,
            source,
            chatType,
            updatedAt: sess.updatedAt || 0,
            updatedAtISO: sess.updatedAt ? new Date(sess.updatedAt).toISOString() : null,
            channel: sess.lastChannel || "",
            accountId: sess.lastAccountId || dir,
          });
        }
      } catch {}
    }
  } catch {}
  sessions.sort((a, b) => b.updatedAt - a.updatedAt);
  return sessions;
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);

  if (url.pathname === "/api/data") {
    res.writeHead(200, {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*"
    });
    const now = Date.now();
    if (!cachedData || now - cacheTime > CACHE_TTL) {
      cachedData = JSON.stringify({
        timestamp: new Date().toISOString(),
        messages: getMessages(100),
        agentStats: getAgentStats(),
        publishQueue: getPublishQueue(),
        cronJobs: getCronJobs(),
        cronRuns: getRecentCronRuns(30),
        agentSessions: getAgentSessions(),
        allSessions: getAllSessions()
      });
      cacheTime = now;
    }
    res.end(cachedData);
    return;
  }

  // POST /api/agent/:id/new — send /new to all sessions of an agent (parallel)
  const newMatch = url.pathname.match(/^\/api\/agent\/([^/]+)\/new$/);
  if (newMatch && req.method === "POST") {
    const agentId = newMatch[1];
    const sessFile = path.join(AGENTS_DIR, agentId, "sessions", "sessions.json");
    try {
      const data = JSON.parse(fs.readFileSync(sessFile, "utf8"));
      const tasks = [];
      for (const [key, sess] of Object.entries(data)) {
        const sid = sess.sessionId;
        if (!sid) continue;
        tasks.push({ key, sid });
      }
      // Run all sessions in parallel
      const results = await Promise.all(tasks.map(({ key, sid }) =>
        new Promise(resolve => {
          execFile("openclaw", [
            "agent", "--agent", agentId, "--session-id", sid,
            "--message", "/new", "--thinking", "off", "--timeout", "30"
          ], { encoding: "utf8", timeout: 35000 }, (err) => {
            if (err) {
              resolve({ sessionId: sid, key, status: "error", error: (err.stderr || err.message || "").slice(0, 200) });
            } else {
              resolve({ sessionId: sid, key, status: "ok" });
            }
          });
        })
      ));
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ agent: agentId, sessions: results }));
    } catch (e) {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ agent: agentId, error: e.message }));
    }
    return;
  }

  // POST /api/session/new — send /new to a single session
  const sessNewMatch = url.pathname.match(/^\/api\/session\/new$/);
  if (sessNewMatch && req.method === "POST") {
    const body = await new Promise(resolve => {
      let data = "";
      req.on("data", c => data += c);
      req.on("end", () => { try { resolve(JSON.parse(data)); } catch { resolve({}); } });
    });
    const { agentId, sessionId } = body;
    if (!agentId || !sessionId) {
      res.writeHead(400, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ error: "agentId and sessionId required" }));
      return;
    }
    try {
      await new Promise((resolve, reject) => {
        execFile("openclaw", [
          "agent", "--agent", agentId, "--session-id", sessionId,
          "--message", "/new", "--thinking", "off", "--timeout", "30"
        ], { encoding: "utf8", timeout: 35000 }, (err) => {
          if (err) reject(err); else resolve();
        });
      });
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ status: "ok", agentId, sessionId }));
    } catch (e) {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ status: "error", agentId, sessionId, error: (e.stderr || e.message || "").slice(0, 200) }));
    }
    return;
  }

  // POST /api/session/delete — delete a session from sessions.json and its .jsonl file
  if (url.pathname === "/api/session/delete" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let data = "";
      req.on("data", c => data += c);
      req.on("end", () => { try { resolve(JSON.parse(data)); } catch { resolve({}); } });
    });
    const { agentId, sessionId, key } = body;
    if (!agentId || !key) {
      res.writeHead(400, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ error: "agentId and key required" }));
      return;
    }
    try {
      const sessFile = path.join(AGENTS_DIR, agentId, "sessions", "sessions.json");
      const data = JSON.parse(fs.readFileSync(sessFile, "utf8"));
      if (data[key]) {
        const sid = data[key].sessionId;
        delete data[key];
        fs.writeFileSync(sessFile, JSON.stringify(data, null, 2));
        // Delete the .jsonl file if it exists
        if (sid) {
          const jsonlFile = path.join(AGENTS_DIR, agentId, "sessions", `${sid}.jsonl`);
          try { fs.unlinkSync(jsonlFile); } catch {}
        }
      }
      cachedData = null; // Invalidate cache
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ status: "ok", agentId, key }));
    } catch (e) {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // POST /api/session/bulk — bulk /new or delete for multiple sessions
  if (url.pathname === "/api/session/bulk" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let data = "";
      req.on("data", c => data += c);
      req.on("end", () => { try { resolve(JSON.parse(data)); } catch { resolve({}); } });
    });
    const { action, sessions: targets } = body; // action: "new" | "delete", sessions: [{agentId, sessionId, key}]
    if (!action || !Array.isArray(targets) || !targets.length) {
      res.writeHead(400, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ error: "action and sessions[] required" }));
      return;
    }

    if (action === "new") {
      const results = await Promise.all(targets.map(t =>
        new Promise(resolve => {
          execFile("openclaw", [
            "agent", "--agent", t.agentId, "--session-id", t.sessionId,
            "--message", "/new", "--thinking", "off", "--timeout", "30"
          ], { encoding: "utf8", timeout: 35000 }, (err) => {
            resolve({ ...t, status: err ? "error" : "ok" });
          });
        })
      ));
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ action, results }));
    } else if (action === "delete") {
      const results = [];
      for (const t of targets) {
        try {
          const sessFile = path.join(AGENTS_DIR, t.agentId, "sessions", "sessions.json");
          const data = JSON.parse(fs.readFileSync(sessFile, "utf8"));
          if (data[t.key]) {
            const sid = data[t.key].sessionId;
            delete data[t.key];
            fs.writeFileSync(sessFile, JSON.stringify(data, null, 2));
            if (sid) {
              const jsonlFile = path.join(AGENTS_DIR, t.agentId, "sessions", `${sid}.jsonl`);
              try { fs.unlinkSync(jsonlFile); } catch {}
            }
          }
          results.push({ ...t, status: "ok" });
        } catch (e) {
          results.push({ ...t, status: "error", error: e.message });
        }
      }
      cachedData = null;
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ action, results }));
    } else {
      res.writeHead(400, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ error: "unknown action" }));
    }
    return;
  }

  // GET /api/models — get all agents' current model + available models
  if (url.pathname === "/api/models" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      const ocData = JSON.parse(fs.readFileSync(OPENCLAW_JSON, "utf8"));
      const agents = ocData.agents?.list || [];
      const result = {};
      for (const a of agents) {
        const primary = a.model?.primary || null;
        // Read available models from agent's models.json
        let available = [];
        const modelsFile = path.join(AGENTS_DIR, a.id, "agent", "models.json");
        try {
          const mData = JSON.parse(fs.readFileSync(modelsFile, "utf8"));
          for (const [provName, prov] of Object.entries(mData.providers || {})) {
            for (const m of (prov.models || [])) {
              available.push({ provider: provName, modelId: m.id, name: m.name || m.id, reasoning: m.reasoning || false });
            }
          }
        } catch {}
        result[a.id] = { primary, available };
      }
      res.end(JSON.stringify(result));
    } catch (e) {
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // POST /api/models/set — set an agent's primary model
  if (url.pathname === "/api/models/set" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let data = "";
      req.on("data", c => data += c);
      req.on("end", () => { try { resolve(JSON.parse(data)); } catch { resolve({}); } });
    });
    const { agentId, model } = body; // model: "provider/modelId"
    if (!agentId || !model) {
      res.writeHead(400, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ error: "agentId and model required" }));
      return;
    }
    try {
      const ocData = JSON.parse(fs.readFileSync(OPENCLAW_JSON, "utf8"));
      const agents = ocData.agents?.list || [];
      const agent = agents.find(a => a.id === agentId);
      if (!agent) throw new Error(`Agent ${agentId} not found`);
      if (!agent.model) agent.model = {};
      agent.model.primary = model;
      fs.writeFileSync(OPENCLAW_JSON, JSON.stringify(ocData, null, 2));
      cachedData = null;
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ status: "ok", agentId, model }));
    } catch (e) {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // CORS preflight for POST endpoints
  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type"
    });
    res.end();
    return;
  }

  if (url.pathname === "/" || url.pathname === "/index.html") {
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(fs.readFileSync(path.join(__dirname, "index.html"), "utf8"));
    return;
  }

  res.writeHead(404);
  res.end("Not Found");
});

server.listen(PORT, () => {
  console.log(`📮 Agent Message Dashboard: http://localhost:${PORT}`);
});
