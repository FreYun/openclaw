#!/usr/bin/env node
// Agent Message Dashboard Server
// Usage: node server.js [port]  (default: 18888)

const http = require("http");
const fs = require("fs");
const path = require("path");
const { execSync, execFile, spawn } = require("child_process");

const PORT = parseInt(process.argv[2] || "18888");
const PUBLISH_QUEUE = "/home/rooot/.openclaw/publish-queue";
const AGENTS_DIR = "/home/rooot/.openclaw/agents";
const CRON_DIR = "/home/rooot/.openclaw/cron";
const OPENCLAW_JSON = "/home/rooot/.openclaw/openclaw.json";
const OPENCLAW_DIR = "/home/rooot/.openclaw";
const ARMORY_CONFIG_FILE = path.join(__dirname, "armory-config.json");
const BOT_EQUIPMENT_FILE = path.join(__dirname, "bot-equipment.json");
const GEM_REGISTRY_FILE = path.join(__dirname, "gem-registry.json");
const EDITORIAL_BOTS = ["bot1","bot2","bot3","bot4","bot5","bot6","bot7","bot8","bot9","bot10","bot11"];
const ALL_BOTS = [...EDITORIAL_BOTS, "bot_main", "mcp_publisher", "coder"];

function botWorkspaceDir(botId) {
  const mapping = { bot_main: "workspace-main", mcp_publisher: "workspace-mcp-publisher", coder: "workspace-coder" };
  return mapping[botId] || `workspace-${botId}`;
}

function parseCronLine(line) {
  // Match: min hour dom month dow command
  const m = line.match(/^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)$/);
  if (!m) return null;
  const [, min, hour, dom, month, dow, command] = m;
  // Extract a short name from the command
  let name = command;
  const pyMatch = command.match(/([\w-]+\.py)/g);
  if (pyMatch) name = pyMatch[pyMatch.length - 1]; // last .py file in chain
  else {
    const cmdParts = command.split("&&").pop().trim().split(/\s+/);
    name = path.basename(cmdParts[0]);
  }
  return { schedule: `${min} ${hour} ${dom} ${month} ${dow}`, command, name };
}

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

  // GET /api/crontab — list system crontab entries
  if (url.pathname === "/api/crontab" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      const raw = execSync("crontab -l 2>/dev/null || true", { encoding: "utf8", timeout: 3000 });
      const entries = [];
      const lines = raw.split("\n");
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();
        if (!trimmed) continue;

        // Check if this is a disabled entry (commented out cron line)
        const disabledMatch = trimmed.match(/^#\s*DISABLED:\s*(.+)$/);
        if (disabledMatch) {
          const cronLine = disabledMatch[1];
          const parsed = parseCronLine(cronLine);
          if (parsed) {
            // Check if previous line is a comment (description)
            let description = "";
            if (i > 0) {
              const prevLine = lines[i - 1].trim();
              if (prevLine.startsWith("#") && !prevLine.startsWith("# DISABLED:")) {
                description = prevLine.replace(/^#\s*/, "");
              }
            }
            entries.push({ ...parsed, enabled: false, lineIndex: i, description });
          }
          continue;
        }

        // Skip regular comments
        if (trimmed.startsWith("#")) continue;

        // Parse active cron line
        const parsed = parseCronLine(trimmed);
        if (parsed) {
          // Check if previous line is a comment (description)
          let description = "";
          if (i > 0) {
            const prevLine = lines[i - 1].trim();
            if (prevLine.startsWith("#") && !prevLine.startsWith("# DISABLED:")) {
              description = prevLine.replace(/^#\s*/, "");
            }
          }
          entries.push({ ...parsed, enabled: true, lineIndex: i, description });
        }
      }
      // Enrich entries with last-run info from log files or process checks
      for (const entry of entries) {
        entry.healthy = null; // unknown by default
        entry.lastRun = null;
        try {
          // Check common log patterns for each cron job
          if (entry.command.includes("daily_update.py")) {
            const log = "/home/rooot/.openclaw/portfolio-service/data/cron.log";
            const stat = fs.statSync(log);
            entry.lastRun = stat.mtime.toISOString();
            // If log was modified within 26 hours on weekdays, healthy
            const ageH = (Date.now() - stat.mtime.getTime()) / 3600000;
            const dow = new Date().getDay();
            entry.healthy = (dow >= 1 && dow <= 5) ? ageH < 26 : true; // weekday check
          } else if (entry.command.includes("update-monitor.py")) {
            const monDir = "/home/rooot/.openclaw/workspace-main/monitor";
            const idx = path.join(monDir, "INDEX.md");
            if (fs.existsSync(idx)) {
              const stat = fs.statSync(idx);
              entry.lastRun = stat.mtime.toISOString();
              const ageH = (Date.now() - stat.mtime.getTime()) / 3600000;
              entry.healthy = ageH < 2; // should run every hour
            }
          } else if (entry.command.includes("healthcheck.sh")) {
            const log = "/tmp/image-gen-mcp.log";
            if (fs.existsSync(log)) {
              const stat = fs.statSync(log);
              entry.lastRun = stat.mtime.toISOString();
              const ageH = (Date.now() - stat.mtime.getTime()) / 3600000;
              entry.healthy = ageH < 3; // every 2 hours
            }
          }
        } catch {}
      }
      res.end(JSON.stringify({ entries, raw }));
    } catch (e) {
      res.end(JSON.stringify({ entries: [], error: e.message }));
    }
    return;
  }

  // POST /api/crontab/toggle — enable/disable a crontab entry
  if (url.pathname === "/api/crontab/toggle" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let data = "";
      req.on("data", c => data += c);
      req.on("end", () => { try { resolve(JSON.parse(data)); } catch { resolve({}); } });
    });
    const { lineIndex, enable } = body;
    if (typeof lineIndex !== "number") {
      res.writeHead(400, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ error: "lineIndex required" }));
      return;
    }
    try {
      const raw = execSync("crontab -l 2>/dev/null || true", { encoding: "utf8", timeout: 3000 });
      const lines = raw.split("\n");
      if (lineIndex < 0 || lineIndex >= lines.length) throw new Error("Invalid lineIndex");

      const line = lines[lineIndex].trim();
      if (enable) {
        // Re-enable: remove "# DISABLED: " prefix
        if (line.startsWith("# DISABLED:")) {
          lines[lineIndex] = line.replace(/^#\s*DISABLED:\s*/, "");
        }
      } else {
        // Disable: add "# DISABLED: " prefix
        if (!line.startsWith("#")) {
          lines[lineIndex] = "# DISABLED: " + line;
        }
      }

      // Write back via crontab
      const newCrontab = lines.join("\n");
      execSync("crontab -", { input: newCrontab, encoding: "utf8", timeout: 3000 });

      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ status: "ok", enable }));
    } catch (e) {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // GET /api/config — expose gateway token for chat URL construction
  if (url.pathname === "/api/config" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      const conf = JSON.parse(fs.readFileSync(OPENCLAW_JSON, "utf8"));
      const token = conf?.gateway?.auth?.token || "";
      res.end(JSON.stringify({ gatewayToken: token }));
    } catch (e) {
      res.end(JSON.stringify({ gatewayToken: "" }));
    }
    return;
  }

  // GET /api/services — get MCP service status + health
  if (url.pathname === "/api/services" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    const services = [
      { id: "image-gen-mcp", name: "image-gen-mcp", port: 18085, cmd: "python3 server.py --transport streamable-http --port 18085", cwd: "/home/rooot/MCP/image-gen-mcp" },
      { id: "compliance-mcp", name: "compliance-mcp", port: 18090, cmd: "./compliance-mcp -port=:18090", cwd: "/home/rooot/MCP/compliance-mcp" },
    ];
    const results = await Promise.all(services.map(svc => {
      return new Promise(resolve => {
        let running = false;
        let pid = null;
        try {
          pid = execSync(`lsof -ti:${svc.port} 2>/dev/null`, { encoding: "utf8", timeout: 3000 }).trim();
          running = !!pid;
        } catch {}
        if (!running) {
          resolve({ ...svc, running, pid: null, healthy: false });
          return;
        }
        // Health probe: MCP initialize handshake
        execFile("curl", [
          "-s", "-o", "/dev/null", "-w", "%{http_code}",
          "-X", "POST", `http://localhost:${svc.port}/mcp`,
          "-H", "Content-Type: application/json",
          "-H", "Accept: application/json, text/event-stream",
          "-d", '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"dashboard","version":"1.0"}}}',
          "--max-time", "5"
        ], { encoding: "utf8", timeout: 8000 }, (err, stdout) => {
          const healthy = !err && stdout.trim() === "200";
          resolve({ ...svc, running, pid: pid || null, healthy });
        });
      });
    }));
    res.end(JSON.stringify(results));
    return;
  }

  // POST /api/services/toggle — start or stop an MCP service
  if (url.pathname === "/api/services/toggle" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let data = "";
      req.on("data", c => data += c);
      req.on("end", () => { try { resolve(JSON.parse(data)); } catch { resolve({}); } });
    });
    const { id, action } = body; // action: "start" | "stop"
    const services = {
      "image-gen-mcp": { port: 18085, cmd: "python3 server.py --transport streamable-http --port 18085", cwd: "/home/rooot/MCP/image-gen-mcp" },
      "compliance-mcp": { port: 18090, cmd: "./compliance-mcp -port=:18090", cwd: "/home/rooot/MCP/compliance-mcp" },
    };
    const svc = services[id];
    if (!svc) {
      res.writeHead(400, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ error: "Unknown service" }));
      return;
    }
    try {
      if (action === "stop") {
        execSync(`lsof -ti:${svc.port} | xargs kill 2>/dev/null || true`, { encoding: "utf8", timeout: 5000 });
        res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
        res.end(JSON.stringify({ status: "ok", action: "stopped" }));
      } else {
        // Kill existing first
        execSync(`lsof -ti:${svc.port} | xargs kill 2>/dev/null || true`, { encoding: "utf8", timeout: 5000 });
        // Start
        execSync(`cd ${svc.cwd} && nohup ${svc.cmd} >> /tmp/${id}.log 2>&1 &`, {
          encoding: "utf8", timeout: 5000, shell: "/bin/bash"
        });
        // Wait a moment and check
        await new Promise(r => setTimeout(r, 2000));
        let pid = null;
        try { pid = execSync(`lsof -ti:${svc.port} 2>/dev/null`, { encoding: "utf8", timeout: 3000 }).trim(); } catch {}
        res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
        res.end(JSON.stringify({ status: pid ? "ok" : "error", action: "started", pid }));
      }
    } catch (e) {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // GET /api/start-all-status — start-all.sh 上次运行结果
  if (url.pathname === "/api/start-all-status" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      const raw = fs.readFileSync("/home/rooot/.openclaw/logs/start-all-status.json", "utf8");
      res.end(raw);
    } catch {
      res.end(JSON.stringify({ status: "never" }));
    }
    return;
  }

  // ── Skill Armory APIs ──────────────────────────────────────────

  function readArmoryConfig() {
    return JSON.parse(fs.readFileSync(ARMORY_CONFIG_FILE, "utf8"));
  }

  function readBotEquipment() {
    try { return JSON.parse(fs.readFileSync(BOT_EQUIPMENT_FILE, "utf8")); }
    catch { return { bots: {} }; }
  }

  function writeBotEquipment(data) {
    fs.writeFileSync(BOT_EQUIPMENT_FILE, JSON.stringify(data, null, 2));
  }

  function getBotSkillsOnDisk(botId) {
    const dir = path.join(OPENCLAW_DIR, botWorkspaceDir(botId), "skills");
    try { return fs.readdirSync(dir).filter(f => !f.startsWith(".")); }
    catch { return []; }
  }

  // Scan all skill.json files from disk to build unified registry
  let _skillCache = null;
  function scanAllSkills(force) {
    if (_skillCache && !force) return _skillCache;

    const config = readArmoryConfig();
    const skills = {};
    const baseLayer = [];

    // 1. Scan universal skills: workspace/skills/*/skill.json
    const universalDir = path.join(OPENCLAW_DIR, "workspace", "skills");
    try {
      for (const name of fs.readdirSync(universalDir)) {
        const jsonPath = path.join(universalDir, name, "skill.json");
        try {
          const meta = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
          skills[name] = { ...meta, source: "universal", id: name };
          if (meta.infrastructure) baseLayer.push(name);
        } catch {}
      }
    } catch {}

    // 2. Scan bot-specific skills: workspace-*/skills/*/skill.json (real dirs only)
    for (const botId of ALL_BOTS) {
      const botSkillDir = path.join(OPENCLAW_DIR, botWorkspaceDir(botId), "skills");
      try {
        for (const name of fs.readdirSync(botSkillDir)) {
          if (skills[name]) continue; // universal already registered
          const skillPath = path.join(botSkillDir, name);
          try {
            const stat = fs.lstatSync(skillPath);
            if (stat.isSymbolicLink()) continue; // skip symlinks
            const jsonPath = path.join(skillPath, "skill.json");
            const meta = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
            skills[name] = { ...meta, source: "bot-specific", owner: botId, id: name };
            if (meta.infrastructure) baseLayer.push(name);
          } catch {}
        }
      } catch {}
    }

    _skillCache = { slotTypes: config.slotTypes, baseLayer, skills };
    return _skillCache;
  }

  function clearSkillCache() { _skillCache = null; }

  function makeEmptySlots() {
    return { "helm-1": null,
             "armor-1": null,
             "accessory-1": null, "accessory-2": null,
             "utility-1": null, "utility-2": null, "utility-3": null, "utility-4": null,
             "research-1": null, "research-2": null, "research-3": null, "research-4": null, "research-5": null, "research-6": null,
             "boots-1": null };
  }

  // Generate EQUIPPED_SKILLS.md for a bot — called after every equip/unequip/swap/sync
  function generateSkillsManifest(botId) {
    const registry = scanAllSkills();
    const equipment = readBotEquipment();
    const botData = equipment.bots?.[botId];
    if (!botData) return;

    const slots = botData.slots || {};
    const equipped = [];
    for (const [slotId, skillId] of Object.entries(slots)) {
      if (!skillId) continue;
      const skill = registry.skills[skillId];
      if (!skill) continue;
      const slotType = slotId.replace(/-\d+$/, "");
      const typeInfo = registry.slotTypes[slotType];
      equipped.push({ slotId, slotType, typeName: typeInfo?.name || slotType, skillId, skill });
    }

    // Group by slot type
    const groups = {};
    for (const e of equipped) {
      if (!groups[e.slotType]) groups[e.slotType] = { typeName: e.typeName, items: [] };
      groups[e.slotType].items.push(e);
    }

    let md = `# 已装备技能\n\n`;
    md += `> 本文件由装备系统自动生成，请勿手动编辑。\n`;
    md += `> 更新时间：${new Date().toISOString().replace("T", " ").slice(0, 19)}\n\n`;

    if (equipped.length === 0) {
      md += `当前无已装备技能。\n`;
    } else {
      // Ordered display
      const order = ["armor", "accessory", "utility", "research", "boots"]; // helm shown in SOUL.md, not here
      for (const type of order) {
        const g = groups[type];
        if (!g) continue;
        const typeInfo = registry.slotTypes[type];
        md += `## ${typeInfo?.icon || ""} ${g.typeName}\n\n`;
        for (const item of g.items) {
          const s = item.skill;
          md += `### ${s.icon} ${s.name}（${item.skillId}）\n\n`;
          if (s.desc) md += `${s.desc}\n\n`;
          md += `**详细文档**：Read \`skills/${item.skillId}/SKILL.md\`\n\n`;
          // List sub-skills if any
          if (s.subSkills && s.subSkills.length > 0) {
            md += `子模块：\n`;
            for (const sub of s.subSkills) {
              md += `- ${sub.icon} **${sub.name}**（\`skills/${item.skillId}/${sub.file}\`）`;
              if (sub.desc) md += ` — ${sub.desc}`;
              md += `\n`;
            }
            md += `\n`;
          }
        }
      }
    }

    const filePath = path.join(OPENCLAW_DIR, botWorkspaceDir(botId), "EQUIPPED_SKILLS.md");
    fs.writeFileSync(filePath, md, "utf8");
  }

  // Auto-insert helm/role info into SOUL.md between <!-- ROLE:START --> and <!-- ROLE:END --> markers
  function updateSoulRole(botId) {
    const equipment = readBotEquipment();
    const registry = scanAllSkills();
    const helmSkillId = equipment.bots?.[botId]?.slots?.["helm-1"];
    const helmSkill = helmSkillId ? registry.skills[helmSkillId] : null;

    const soulPath = path.join(OPENCLAW_DIR, botWorkspaceDir(botId), "SOUL.md");
    let soul;
    try { soul = fs.readFileSync(soulPath, "utf8"); } catch { return; }

    const roleBlock = helmSkill
      ? `<!-- ROLE:START -->\n> **工种：${helmSkill.name}** — ${helmSkill.desc}\n>\n> 详细职责定义：Read \`skills/${helmSkillId}/SKILL.md\`\n<!-- ROLE:END -->`
      : `<!-- ROLE:START -->\n<!-- ROLE:END -->`;

    if (soul.includes("<!-- ROLE:START -->")) {
      soul = soul.replace(/<!-- ROLE:START -->[\s\S]*?<!-- ROLE:END -->/, roleBlock);
    } else {
      soul = roleBlock + "\n\n" + soul;
    }
    fs.writeFileSync(soulPath, soul, "utf8");
  }

  // GET /api/skills — registry + equipment + disk state
  if (url.pathname === "/api/skills" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      const registry = scanAllSkills();
      const equipment = readBotEquipment();
      const diskState = {};
      const botBaseLayer = {};
      for (const botId of ALL_BOTS) {
        const onDisk = getBotSkillsOnDisk(botId);
        const isEquippable = (s) => registry.skills[s] && !registry.skills[s].infrastructure && registry.skills[s].slot;
        diskState[botId] = onDisk.filter(s => isEquippable(s));
        botBaseLayer[botId] = onDisk.filter(s => registry.skills[s]?.infrastructure || !registry.skills[s]);
      }
      res.end(JSON.stringify({ registry, equipment, diskState, botBaseLayer }));
    } catch (e) {
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // POST /api/skills/sync — scan disk and rebuild bot-equipment.json
  if (url.pathname === "/api/skills/sync" && req.method === "POST") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      clearSkillCache();
      const registry = scanAllSkills(true);
      const existing = readBotEquipment();
      const equipment = { bots: {} };
      for (const botId of ALL_BOTS) {
        const onDisk = getBotSkillsOnDisk(botId);
        const equippable = new Set(onDisk.filter(s => !registry.baseLayer.includes(s) && registry.skills[s] && !registry.skills[s].infrastructure && registry.skills[s].slot));

        // Start from existing slots, remove skills no longer on disk/equippable
        const prev = existing.bots?.[botId]?.slots || {};
        const slots = makeEmptySlots();
        const alreadyPlaced = new Set();
        for (const [slotKey, skillId] of Object.entries(prev)) {
          if (skillId && equippable.has(skillId) && slots.hasOwnProperty(slotKey)) {
            // Verify slot type still matches
            const skill = registry.skills[skillId];
            const slotType = slotKey.replace(/-\d+$/, "");
            if (skill && skill.slot === slotType) {
              slots[slotKey] = skillId;
              alreadyPlaced.add(skillId);
            }
          }
        }

        // Place new skills (on disk but not yet equipped) into empty slots
        const overflow = [];
        for (const skillId of equippable) {
          if (alreadyPlaced.has(skillId)) continue;
          const skill = registry.skills[skillId];
          if (!skill || !skill.slot) continue;
          const type = skill.slot;
          // Find first empty slot of matching type
          let placed = false;
          for (const [k, v] of Object.entries(slots)) {
            if (!v && k.startsWith(type + "-")) {
              slots[k] = skillId;
              placed = true;
              break;
            }
          }
          if (!placed) overflow.push(skillId);
        }

        equipment.bots[botId] = { slots, overflow: overflow.length ? overflow : undefined };
      }
      writeBotEquipment(equipment);
      for (const botId of ALL_BOTS) {
        generateSkillsManifest(botId);
        updateSoulRole(botId);
      }
      res.end(JSON.stringify({ status: "ok", equipment }));
    } catch (e) {
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // POST /api/skills/equip — equip a skill to a bot slot
  if (url.pathname === "/api/skills/equip" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let data = "";
      req.on("data", c => data += c);
      req.on("end", () => { try { resolve(JSON.parse(data)); } catch { resolve({}); } });
    });
    const { botId, slot, skillId } = body;
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      const registry = scanAllSkills();
      if (!ALL_BOTS.includes(botId)) throw new Error("Invalid botId");
      const skill = registry.skills[skillId];
      if (!skill) throw new Error("Unknown skill: " + skillId);
      if (skill.infrastructure) throw new Error("Cannot equip infrastructure skill");
      // Validate slot type
      const slotType = slot.replace(/-\d+$/, "");
      if (skill.slot !== slotType) throw new Error(`Skill type "${skill.slot}" cannot go in "${slotType}" slot`);
      // Permission: research slots require frontline helm
      if (slotType === "research") {
        const curEquip = readBotEquipment();
        const helmSkill = curEquip.bots?.[botId]?.slots?.["helm-1"];
        if (helmSkill !== "frontline") throw new Error("研究插槽需要装备「前台」工种才能解锁");
      }
      const slots = makeEmptySlots();
      if (!slots.hasOwnProperty(slot)) throw new Error("Invalid slot: " + slot);

      const equipment = readBotEquipment();
      if (!equipment.bots[botId]) equipment.bots[botId] = { slots: makeEmptySlots() };

      // If slot is occupied, unequip existing skill first
      const existing = equipment.bots[botId].slots[slot];
      if (existing && existing !== skillId) {
        const existingPath = path.join(OPENCLAW_DIR, botWorkspaceDir(botId), "skills", existing);
        try {
          const stat = fs.lstatSync(existingPath);
          if (stat.isSymbolicLink()) fs.unlinkSync(existingPath);
        } catch {}
      }

      // Check if skill is already equipped in another slot — remove from old slot
      for (const [s, v] of Object.entries(equipment.bots[botId].slots)) {
        if (v === skillId) equipment.bots[botId].slots[s] = null;
      }

      // Create symlink on disk
      const targetPath = path.join(OPENCLAW_DIR, botWorkspaceDir(botId), "skills", skillId);
      try { fs.lstatSync(targetPath); } catch {
        if (skill.source === "universal") {
          fs.symlinkSync(`../../workspace/skills/${skillId}`, targetPath);
        } else if (skill.owner !== botId) {
          const absSource = path.join(OPENCLAW_DIR, botWorkspaceDir(skill.owner), "skills", skillId);
          fs.symlinkSync(absSource, targetPath);
        }
      }

      equipment.bots[botId].slots[slot] = skillId;
      writeBotEquipment(equipment);
      clearSkillCache();
      generateSkillsManifest(botId);
      if (slot === "helm-1") updateSoulRole(botId);
      res.end(JSON.stringify({ status: "ok", botId, slot, skillId }));
    } catch (e) {
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // POST /api/skills/unequip — remove a skill from a bot slot
  if (url.pathname === "/api/skills/unequip" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let data = "";
      req.on("data", c => data += c);
      req.on("end", () => { try { resolve(JSON.parse(data)); } catch { resolve({}); } });
    });
    const { botId, slot } = body;
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      if (!ALL_BOTS.includes(botId)) throw new Error("Invalid botId");
      const equipment = readBotEquipment();
      if (!equipment.bots[botId]) throw new Error("Bot not initialized");
      const skillId = equipment.bots[botId].slots[slot];
      if (!skillId) throw new Error("Slot is empty");
      const registry = scanAllSkills();
      if (registry.skills[skillId]?.infrastructure) throw new Error("Cannot unequip infrastructure skill");

      // Remove from disk (only symlinks, never real directories)
      const targetPath = path.join(OPENCLAW_DIR, botWorkspaceDir(botId), "skills", skillId);
      try {
        const stat = fs.lstatSync(targetPath);
        if (stat.isSymbolicLink()) fs.unlinkSync(targetPath);
      } catch {}

      equipment.bots[botId].slots[slot] = null;
      writeBotEquipment(equipment);
      clearSkillCache();
      generateSkillsManifest(botId);
      if (slot === "helm-1") updateSoulRole(botId);
      res.end(JSON.stringify({ status: "ok", botId, slot, skillId }));
    } catch (e) {
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // POST /api/skills/swap — swap two slots for a bot
  if (url.pathname === "/api/skills/swap" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let data = "";
      req.on("data", c => data += c);
      req.on("end", () => { try { resolve(JSON.parse(data)); } catch { resolve({}); } });
    });
    const { botId, fromSlot, toSlot } = body;
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      if (!ALL_BOTS.includes(botId)) throw new Error("Invalid botId");
      // Validate same slot type
      const fromType = fromSlot.replace(/-\d+$/, "");
      const toType = toSlot.replace(/-\d+$/, "");
      if (fromType !== toType) throw new Error("Can only swap same-type slots");
      const equipment = readBotEquipment();
      if (!equipment.bots[botId]) throw new Error("Bot not initialized");
      const temp = equipment.bots[botId].slots[fromSlot];
      equipment.bots[botId].slots[fromSlot] = equipment.bots[botId].slots[toSlot];
      equipment.bots[botId].slots[toSlot] = temp;
      writeBotEquipment(equipment);
      generateSkillsManifest(botId);
      res.end(JSON.stringify({ status: "ok", botId, fromSlot, toSlot }));
    } catch (e) {
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // GET /api/skills/content?skill=xxx&file=yyy.md — read skill MD file content
  if (url.pathname === "/api/skills/content" && req.method === "GET") {
    const skillId = url.searchParams.get("skill");
    const file = url.searchParams.get("file") || "SKILL.md";
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    if (!skillId || /[\/\\]/.test(skillId) || /[\/\\]/.test(file)) {
      res.end(JSON.stringify({ error: "Invalid parameters" }));
      return;
    }
    try {
      // Try universal skill first, then bot-specific
      let filePath = path.join(OPENCLAW_DIR, "workspace", "skills", skillId, file);
      if (!fs.existsSync(filePath)) {
        for (const botId of ALL_BOTS) {
          const alt = path.join(OPENCLAW_DIR, botWorkspaceDir(botId), "skills", skillId, file);
          if (fs.existsSync(alt)) { filePath = alt; break; }
        }
      }
      if (!fs.existsSync(filePath)) {
        res.end(JSON.stringify({ error: "File not found" }));
        return;
      }
      const content = fs.readFileSync(filePath, "utf8");
      res.end(JSON.stringify({ skill: skillId, file, content }));
    } catch (e) {
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // GET /api/bot/soul?botId=xxx — read bot's SOUL.md
  if (url.pathname === "/api/bot/soul" && req.method === "GET") {
    const botId = url.searchParams.get("botId");
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    if (!botId || !ALL_BOTS.includes(botId)) {
      res.end(JSON.stringify({ error: "Invalid botId" }));
      return;
    }
    try {
      const filePath = path.join(OPENCLAW_DIR, botWorkspaceDir(botId), "SOUL.md");
      if (!fs.existsSync(filePath)) {
        res.end(JSON.stringify({ error: "SOUL.md not found" }));
        return;
      }
      const content = fs.readFileSync(filePath, "utf8");
      res.end(JSON.stringify({ botId, content }));
    } catch (e) {
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // GET /api/skills/registry — return full scanned skill list (debug/admin)
  if (url.pathname === "/api/skills/registry" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      clearSkillCache();
      const registry = scanAllSkills(true);
      res.end(JSON.stringify(registry, null, 2));
    } catch (e) {
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // ── Gem System (MCP hot-plug) ─────────────────────────────────

  function readGemRegistry() {
    return JSON.parse(fs.readFileSync(GEM_REGISTRY_FILE, "utf8"));
  }

  function readGemToolOverrides(filePath) {
    // If no path given, find from registry
    if (!filePath) {
      const registry = readGemRegistry();
      for (const gem of Object.values(registry.gems)) {
        if (gem.toolOverridesFile) { filePath = gem.toolOverridesFile; break; }
      }
    }
    if (!filePath) return {};
    try { return JSON.parse(fs.readFileSync(filePath, "utf8")); }
    catch { return {}; }
  }

  function readMcporter(botId) {
    const p = path.join(OPENCLAW_DIR, botWorkspaceDir(botId), "config", "mcporter.json");
    try { return JSON.parse(fs.readFileSync(p, "utf8")); }
    catch { return { mcpServers: {}, imports: [] }; }
  }

  function writeMcporter(botId, data) {
    const dir = path.join(OPENCLAW_DIR, botWorkspaceDir(botId), "config");
    try { fs.mkdirSync(dir, { recursive: true }); } catch {}
    fs.writeFileSync(path.join(dir, "mcporter.json"), JSON.stringify(data, null, 4));
  }

  function resolveGemUrl(gemId, botId, registry) {
    const gem = registry.gems[gemId];
    if (!gem) return null;
    const special = gem.specialBots?.[botId];
    if (special && !special.multi && special.url) return special.url;
    if (gem.perBot && gem.portMap) {
      const port = gem.portMap[botId];
      if (!port) return null;
      return gem.urlTemplate.replace("${port}", port);
    }
    if (gem.perBot && gem.urlTemplate?.includes("${botId}")) {
      return gem.urlTemplate.replace("${botId}", botId);
    }
    return gem.urlTemplate || null;
  }

  function getBotGemBindings(botId, registry) {
    const mcporter = readMcporter(botId);
    const bindings = {};
    for (const [gemId, gem] of Object.entries(registry.gems)) {
      const special = gem.specialBots?.[botId];
      if (special?.multi) {
        const expectedKeys = Object.keys(special.entries);
        const found = expectedKeys.filter(k => mcporter.mcpServers[k]);
        bindings[gemId] = { socketed: found.length > 0, entries: found.length, expectedEntries: expectedKeys.length };
      } else {
        const key = gemId;
        const entry = mcporter.mcpServers[key];
        bindings[gemId] = { socketed: !!entry, url: entry?.url || entry?.baseUrl || null };
      }
    }
    return bindings;
  }

  function checkGemHealth(port, gem) {
    return new Promise(resolve => {
      if (!port) { resolve({ status: "unknown", reason: "no-port" }); return; }
      try {
        const pid = execSync(`lsof -ti:${port} 2>/dev/null`, { encoding: "utf8", timeout: 3000 }).trim();
        if (!pid) { resolve({ status: "down", pid: null }); return; }
        if (!gem.healthMethod || gem.healthMethod === "port-check") {
          resolve({ status: "up", pid }); return;
        }
        if (gem.healthMethod === "mcp-initialize") {
          execFile("curl", [
            "-s", "-o", "/dev/null", "-w", "%{http_code}",
            "-X", "POST", `http://localhost:${port}${gem.healthEndpoint || "/mcp"}`,
            "-H", "Content-Type: application/json",
            "-H", "Accept: application/json, text/event-stream",
            "-d", '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"dashboard","version":"1.0"}}}',
            "--max-time", "5"
          ], { encoding: "utf8", timeout: 8000 }, (err, stdout) => {
            resolve({ status: (!err && stdout.trim() === "200") ? "healthy" : "unhealthy", pid });
          });
          return;
        }
        if (gem.healthMethod === "http-get") {
          execFile("curl", [
            "-s", "-o", "/dev/null", "-w", "%{http_code}",
            `http://localhost:${port}${gem.healthEndpoint || "/health"}`,
            "--max-time", "5"
          ], { encoding: "utf8", timeout: 8000 }, (err, stdout) => {
            resolve({ status: (!err && stdout.trim() === "200") ? "healthy" : "unhealthy", pid });
          });
          return;
        }
        resolve({ status: "up", pid });
      } catch {
        resolve({ status: "down", pid: null });
      }
    });
  }

  // GET /api/plugins — system plugin list
  if (url.pathname === "/api/plugins" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      const conf = JSON.parse(fs.readFileSync(OPENCLAW_JSON, "utf8"));
      const entries = conf.plugins?.entries || {};
      const meta = {
        "agent-messaging": { name: "Agent 通讯", icon: "📡", desc: "Agent 间消息传递与协调" },
        "feishu":           { name: "飞书通道",   icon: "💬", desc: "飞书群聊与私信通道" },
        "tushare-openclaw": { name: "Tushare 数据", icon: "📈", desc: "A股行情与财务数据" },
      };
      const result = Object.entries(entries).map(([id, e]) => ({
        id, name: meta[id]?.name || id, icon: meta[id]?.icon || "🔌", desc: meta[id]?.desc || "", enabled: !!e.enabled
      }));
      res.end(JSON.stringify(result));
    } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    return;
  }

  // GET /api/gems — registry + bindings + skill deps + tool selections
  if (url.pathname === "/api/gems" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      const registry = readGemRegistry();
      const bindings = {};
      for (const botId of ALL_BOTS) {
        bindings[botId] = getBotGemBindings(botId, registry);
      }
      const skillRegistry = scanAllSkills();
      const skillGemDeps = {};
      for (const [skillId, skill] of Object.entries(skillRegistry.skills)) {
        if (skill.requires && skill.requires.length > 0) {
          skillGemDeps[skillId] = skill.requires;
        }
      }
      // Per-bot tool selections for gems with subTools
      const toolSelections = readGemToolOverrides();
      res.end(JSON.stringify({ registry, bindings, skillGemDeps, toolSelections }));
    } catch (e) {
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // POST /api/gems/tools/select — set per-bot tool list for a gem with subTools
  if (url.pathname === "/api/gems/tools/select" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let d = ""; req.on("data", c => d += c);
      req.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve({}); } });
    });
    const { botId, gemId, toolIds } = body;
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      if (!ALL_BOTS.includes(botId)) throw new Error("Invalid botId");
      const registry = readGemRegistry();
      const gem = registry.gems[gemId];
      if (!gem || !gem.subTools) throw new Error("Gem has no subTools: " + gemId);
      if (!gem.toolOverridesFile) throw new Error("Gem has no toolOverridesFile configured");
      // Validate tool IDs
      const validIds = new Set(gem.subTools.map(t => t.id));
      const filtered = (toolIds || []).filter(id => validIds.has(id));
      // Write to overrides file
      const overrides = readGemToolOverrides(gem.toolOverridesFile);
      if (filtered.length === 0) {
        delete overrides[botId];
      } else {
        overrides[botId] = filtered;
      }
      fs.writeFileSync(gem.toolOverridesFile, JSON.stringify(overrides, null, 2));
      // Restart gateway
      if (gem.restartCmd) {
        try {
          execSync(gem.restartCmd, { timeout: 10000 });
        } catch (e) {
          // restart might exit non-zero but still work
        }
      }
      res.end(JSON.stringify({ status: "ok", botId, gemId, toolIds: filtered }));
    } catch (e) {
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // GET /api/gems/health — parallel health checks
  if (url.pathname === "/api/gems/health" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      const registry = readGemRegistry();
      const health = {};
      const checks = [];
      for (const [gemId, gem] of Object.entries(registry.gems)) {
        if (gem.perBot && gem.portMap) {
          health[gemId] = {};
          for (const [botId, port] of Object.entries(gem.portMap)) {
            checks.push(checkGemHealth(port, gem).then(r => { health[gemId][botId] = r; }));
          }
        } else if (gem.port) {
          checks.push(checkGemHealth(gem.port, gem).then(r => { health[gemId] = r; }));
        } else {
          health[gemId] = { status: "unknown", reason: "no-port" };
        }
      }
      await Promise.all(checks);
      res.end(JSON.stringify(health));
    } catch (e) {
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // POST /api/gems/socket — add MCP to bot's mcporter.json
  if (url.pathname === "/api/gems/socket" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let d = ""; req.on("data", c => d += c);
      req.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve({}); } });
    });
    const { botId, gemId } = body;
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      if (!ALL_BOTS.includes(botId)) throw new Error("Invalid botId");
      const registry = readGemRegistry();
      const gem = registry.gems[gemId];
      if (!gem) throw new Error("Unknown gem: " + gemId);
      const mcporter = readMcporter(botId);
      const special = gem.specialBots?.[botId];
      if (special?.multi) {
        for (const [key, url] of Object.entries(special.entries)) {
          mcporter.mcpServers[key] = { url };
        }
      } else {
        const url = resolveGemUrl(gemId, botId, registry);
        if (!url) throw new Error(`Cannot resolve URL for ${gemId} on ${botId}`);
        const urlKey = special?.urlKey || "url";
        mcporter.mcpServers[gemId] = { [urlKey]: url };
      }
      if (!mcporter.imports) mcporter.imports = [];
      writeMcporter(botId, mcporter);
      res.end(JSON.stringify({ status: "ok", botId, gemId }));
    } catch (e) {
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // POST /api/gems/unsocket — remove MCP from bot's mcporter.json
  if (url.pathname === "/api/gems/unsocket" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let d = ""; req.on("data", c => d += c);
      req.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve({}); } });
    });
    const { botId, gemId, force } = body;
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      if (!ALL_BOTS.includes(botId)) throw new Error("Invalid botId");
      const registry = readGemRegistry();
      const gem = registry.gems[gemId];
      if (!gem) throw new Error("Unknown gem: " + gemId);
      // Dependency check
      if (!force) {
        const equipment = readBotEquipment();
        const skillRegistry = scanAllSkills();
        const botSlots = equipment.bots?.[botId]?.slots || {};
        const dependentSkills = [];
        for (const skillId of Object.values(botSlots)) {
          if (!skillId) continue;
          const skill = skillRegistry.skills[skillId];
          if (skill?.requires?.includes(gemId)) {
            dependentSkills.push({ id: skillId, name: skill.name });
          }
        }
        if (dependentSkills.length > 0) {
          res.end(JSON.stringify({ status: "warning", message: "equipped-skills-depend", dependentSkills }));
          return;
        }
      }
      const mcporter = readMcporter(botId);
      const special = gem.specialBots?.[botId];
      if (special?.multi) {
        for (const key of Object.keys(special.entries)) {
          delete mcporter.mcpServers[key];
        }
      } else {
        delete mcporter.mcpServers[gemId];
      }
      writeMcporter(botId, mcporter);
      res.end(JSON.stringify({ status: "ok", botId, gemId }));
    } catch (e) {
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
