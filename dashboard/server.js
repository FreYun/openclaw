#!/usr/bin/env node
// Agent Message Dashboard Server
// Usage: node server.js [port]  (default: 18888)

const http = require("http");
const fs = require("fs");
const path = require("path");
const { execSync, execFile, spawn } = require("child_process");

const PORT = parseInt(process.argv[2] || "18888");

// Run openclaw agent with proper process-group cleanup.
// Uses detached:true so openclaw + its child openclaw-agent form a new process group,
// then kills the entire group (-pid) on completion/timeout to prevent orphan agents.
function runAgent(args, timeoutMs) {
  return new Promise(resolve => {
    const child = spawn("openclaw", args, {
      stdio: ["ignore", "pipe", "pipe"],
      detached: true
    });

    let stdout = "", stderr = "";
    child.stdout.on("data", d => stdout += d);
    child.stderr.on("data", d => stderr += d);

    let done = false;
    const finish = (result) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      try { process.kill(-child.pid, "SIGKILL"); } catch {}
      resolve(result);
    };

    const timer = setTimeout(() => {
      finish({ error: "timeout", stderr: stderr.slice(0, 200) });
    }, timeoutMs);

    child.on("close", (code) => {
      finish(code === 0
        ? { stdout }
        : { error: (stderr || `exit ${code}`).slice(0, 200) });
    });

    child.unref();
  });
}
const PUBLISH_QUEUE = "/home/rooot/.openclaw/publish-queue";
const AGENTS_DIR = "/home/rooot/.openclaw/agents";
const CRON_DIR = "/home/rooot/.openclaw/cron";
const OPENCLAW_JSON = "/home/rooot/.openclaw/openclaw.json";
const OPENCLAW_DIR = "/home/rooot/.openclaw";
const ARMORY_CONFIG_FILE = path.join(__dirname, "armory-config.json");
const BOT_EQUIPMENT_FILE = path.join(__dirname, "bot-equipment.json");
const GEM_REGISTRY_FILE = path.join(__dirname, "gem-registry.json");
const ADMIN_PASSWORD = "openclaw2026";
const DELETE_PASSWORD = "delete2026";
const SYSTEM_BOT_IDS = new Set(["mag1", "sys1", "sys2", "sys3"]);
const XHS_MCP_BIN = "/home/rooot/MCP/xiaohongshu-mcp/xiaohongshu-mcp";
const XHS_PROFILES_DIR = "/home/rooot/.xhs-profiles";

function getEditorialBots() {
  return getKnownAgentIds().filter(id => /^bot\d+$/.test(id)).sort((a, b) => {
    return parseInt(a.replace("bot", "")) - parseInt(b.replace("bot", ""));
  });
}
function getAllBots() {
  return [...getEditorialBots(), ...getKnownAgentIds().filter(id => !(/^bot\d+$/.test(id)))];
}

const FEISHU_ID_SKILL = path.join(OPENCLAW_DIR, "workspace/skills/contact-book/SKILL.md");

// Regenerate the Agent section in 通讯小本本 from openclaw.json
function regenerateContactDirectory() {
  try {
    const ocData = JSON.parse(fs.readFileSync(OPENCLAW_JSON, "utf8"));
    const agents = ocData.agents?.list || [];
    const content = fs.readFileSync(FEISHU_ID_SKILL, "utf8");

    // Build new agent table
    const rows = agents.map(a => `| ${a.id} | ${a.name || a.id} |`).join("\n");
    const newSection = `## Agent\n\n| Agent ID | 名字 |\n|----------|------|\n${rows}`;

    // Replace everything between "## Agent" and the next "---"
    const updated = content.replace(
      /## Agent[\s\S]*?(?=\n---)/,
      newSection + "\n"
    );

    // Update timestamp
    const dateStr = new Date().toISOString().slice(0, 10);
    const final = updated.replace(/最近更新：\d{4}-\d{2}-\d{2}/, `最近更新：${dateStr}`);

    fs.writeFileSync(FEISHU_ID_SKILL, final);
  } catch (e) {
    console.error("Failed to regenerate contact directory:", e.message);
  }
}

function botWorkspaceDir(botId) {
  const mapping = { mag1: "workspace-main", sys1: "workspace-mcp-publisher", sys3: "workspace-coder" };
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
      // Read agent names + feishu config status from openclaw.json
      let feishuStatus = {};
      let botNames = {};
      try {
        const ocData = JSON.parse(fs.readFileSync(OPENCLAW_JSON, "utf8"));
        for (const a of (ocData.agents?.list || [])) {
          if (a.name) botNames[a.id] = a.name;
        }
        const accounts = ocData.channels?.feishu?.accounts || {};
        for (const [id, acct] of Object.entries(accounts)) {
          if (id === "default") continue;
          feishuStatus[id] = { hasAppId: !!acct.appId, enabled: acct.enabled !== false };
        }
      } catch {}
      cachedData = JSON.stringify({
        timestamp: new Date().toISOString(),
        messages: getMessages(100),
        agentStats: getAgentStats(),
        publishQueue: getPublishQueue(),
        cronJobs: getCronJobs(),
        cronRuns: getRecentCronRuns(30),
        agentSessions: getAgentSessions(),
        allSessions: getAllSessions(),
        feishuStatus,
        editorialBots: getEditorialBots(),
        botNames
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
        runAgent([
          "agent", "--agent", agentId, "--session-id", sid,
          "--message", "/new", "--thinking", "off", "--timeout", "120"
        ], 125000).then(r => ({
          sessionId: sid, key,
          status: r.error ? "error" : "ok",
          ...(r.error ? { error: r.error } : {})
        }))
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
      const r = await runAgent([
        "agent", "--agent", agentId, "--session-id", sessionId,
        "--message", "/new", "--thinking", "off", "--timeout", "30"
      ], 35000);
      if (r.error) throw new Error(r.error);
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ status: "ok", agentId, sessionId }));
    } catch (e) {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ status: "error", agentId, sessionId, error: (e.message || "").slice(0, 200) }));
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
        runAgent([
          "agent", "--agent", t.agentId, "--session-id", t.sessionId,
          "--message", "/new", "--thinking", "off", "--timeout", "120"
        ], 125000).then(r => ({
          ...t, status: r.error ? "error" : "ok"
        }))
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
    for (const botId of getAllBots()) {
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

  function getScheduledSlotCount(botId) {
    const equipment = readBotEquipment();
    const helmSkill = equipment.bots?.[botId]?.slots?.["helm-1"];
    return helmSkill === "management" ? 20 : 6;
  }

  function makeEmptySlots(scheduledCount = 0) {
    const slots = { "helm-1": null,
             "armor-1": null,
             "accessory-1": null, "accessory-2": null,
             "utility-1": null, "utility-2": null, "utility-3": null, "utility-4": null,
             "research-1": null, "research-2": null, "research-3": null, "research-4": null, "research-5": null, "research-6": null,
             "boots-1": null };
    for (let i = 1; i <= scheduledCount; i++) {
      slots[`scheduled-${i}`] = null;
    }
    return slots;
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
      if (slotId.startsWith("scheduled-")) continue; // scheduled skills managed via cron modal
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
      for (const botId of getAllBots()) {
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
      for (const botId of getAllBots()) {
        const onDisk = getBotSkillsOnDisk(botId);
        const equippable = new Set(onDisk.filter(s => !registry.baseLayer.includes(s) && registry.skills[s] && !registry.skills[s].infrastructure && registry.skills[s].slot));

        // Determine scheduled slot count from existing helm
        const prevHelm = existing.bots?.[botId]?.slots?.["helm-1"];
        const schedCount = prevHelm === "management" ? 20 : 6;

        // Start from existing slots, remove skills no longer on disk/equippable
        const prev = existing.bots?.[botId]?.slots || {};
        const slots = makeEmptySlots(schedCount);
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
      for (const botId of getAllBots()) {
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
      if (!getAllBots().includes(botId)) throw new Error("Invalid botId");
      const skill = registry.skills[skillId];
      if (!skill) throw new Error("Unknown skill: " + skillId);
      if (skill.infrastructure) throw new Error("Cannot equip infrastructure skill");
      // Validate slot type
      const slotType = slot.replace(/-\d+$/, "");
      if (skill.slot !== slotType) throw new Error(`Skill type "${skill.slot}" cannot go in "${slotType}" slot`);
      // Block: scheduled skills can only go in scheduled slots
      if (skill.slot === "scheduled" && slotType !== "scheduled") throw new Error("定时任务技能只能装备到定时插槽");
      if (slotType === "scheduled" && skill.slot !== "scheduled") throw new Error("定时插槽只能装备定时任务技能");
      // Permission: research slots require frontline helm
      if (slotType === "research") {
        const curEquip = readBotEquipment();
        const helmSkill = curEquip.bots?.[botId]?.slots?.["helm-1"];
        if (helmSkill !== "frontline") throw new Error("研究插槽需要装备「前台」工种才能解锁");
      }
      // Dependency: requiresSkills — check dependent skills exist in bot workspace
      if (skill.requiresSkills && skill.requiresSkills.length > 0) {
        const botSkillDir = path.join(OPENCLAW_DIR, botWorkspaceDir(botId), "skills");
        const missing = skill.requiresSkills.filter(dep => {
          try { fs.statSync(path.join(botSkillDir, dep)); return false; } catch { return true; }
        });
        if (missing.length > 0) {
          const names = missing.map(id => registry.skills[id]?.name || id).join("、");
          throw new Error(`缺少依赖技能：${names}`);
        }
      }
      const schedCount = getScheduledSlotCount(botId);
      const validSlots = makeEmptySlots(schedCount);
      if (!validSlots.hasOwnProperty(slot)) throw new Error("Invalid slot: " + slot);

      const equipment = readBotEquipment();
      if (!equipment.bots[botId]) equipment.bots[botId] = { slots: makeEmptySlots(schedCount) };

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
      if (!getAllBots().includes(botId)) throw new Error("Invalid botId");
      const equipment = readBotEquipment();
      if (!equipment.bots[botId]) throw new Error("Bot not initialized");
      const skillId = equipment.bots[botId].slots[slot];
      if (!skillId) throw new Error("Slot is empty");
      const registry = scanAllSkills();
      if (registry.skills[skillId]?.infrastructure) throw new Error("Cannot unequip infrastructure skill");

      // Block unequip if other equipped skills depend on this one via requiresSkills
      const botSlots = equipment.bots[botId].slots;
      const dependents = [];
      for (const [s, equippedId] of Object.entries(botSlots)) {
        if (!equippedId || equippedId === skillId) continue;
        const equippedSkill = registry.skills[equippedId];
        if (equippedSkill?.requiresSkills?.includes(skillId)) {
          dependents.push(equippedSkill.name || equippedId);
        }
      }
      if (dependents.length > 0) {
        throw new Error(`不能卸装：${dependents.join("、")} 依赖此技能`);
      }

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
      if (!getAllBots().includes(botId)) throw new Error("Invalid botId");
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
        for (const botId of getAllBots()) {
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
    if (!botId || !getAllBots().includes(botId)) {
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
      for (const botId of getAllBots()) {
        bindings[botId] = getBotGemBindings(botId, registry);
      }
      const skillRegistry = scanAllSkills();
      const skillGemDeps = {};
      for (const [skillId, skill] of Object.entries(skillRegistry.skills)) {
        if (skill.requiresMcp && skill.requiresMcp.length > 0) {
          skillGemDeps[skillId] = skill.requiresMcp;
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
      if (!getAllBots().includes(botId)) throw new Error("Invalid botId");
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
        } else if (gem.healthUrl) {
          // Remote URL health check (no local port)
          checks.push(new Promise(resolve => {
            const method = gem.healthMethod === "mcp-initialize" ? [
              "-s", "-o", "/dev/null", "-w", "%{http_code}",
              "-X", "POST", gem.healthUrl,
              "-H", "Content-Type: application/json",
              "-H", "Accept: application/json, text/event-stream",
              "-d", '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"dashboard","version":"1.0"}}}',
              "--max-time", "5"
            ] : [
              "-s", "-o", "/dev/null", "-w", "%{http_code}",
              gem.healthUrl, "--max-time", "5"
            ];
            execFile("curl", method, { encoding: "utf8", timeout: 8000 }, (err, stdout) => {
              health[gemId] = { status: (!err && stdout.trim() === "200") ? "healthy" : "down", pid: null };
              resolve();
            });
          }));
        } else {
          health[gemId] = { status: "unknown", reason: "no-port" };
        }
      }
      await Promise.all(checks);
      // Compute aggregate health for specialBots with multi entries
      for (const [gemId, gem] of Object.entries(registry.gems)) {
        if (!gem.specialBots || !gem.portMap) continue;
        for (const [botId, special] of Object.entries(gem.specialBots)) {
          if (!special.multi || !special.entries) continue;
          const entryPorts = new Set(Object.values(special.entries).map(u => {
            const m = u.match(/:(\d+)\//); return m ? parseInt(m[1]) : null;
          }).filter(Boolean));
          const relevantBots = Object.entries(gem.portMap)
            .filter(([, p]) => entryPorts.has(p)).map(([bid]) => bid);
          const statuses = relevantBots.map(bid => health[gemId]?.[bid]?.status || "unknown");
          let agg = "unknown";
          if (statuses.length > 0) {
            if (statuses.every(s => s === "healthy")) agg = "healthy";
            else if (statuses.every(s => s === "down")) agg = "down";
            else if (statuses.some(s => s === "healthy")) agg = "unhealthy";
          }
          health[gemId][botId] = { status: agg, entries: statuses.length };
        }
      }
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
      if (!getAllBots().includes(botId)) throw new Error("Invalid botId");
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
      if (!getAllBots().includes(botId)) throw new Error("Invalid botId");
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
          if (skill?.requiresMcp?.includes(gemId)) {
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

  // ── Cron Job CRUD APIs ──────────────────────────────────────

  function readCronJobs() {
    try {
      const data = JSON.parse(fs.readFileSync(path.join(CRON_DIR, "jobs.json"), "utf8"));
      return data;
    } catch { return { version: 1, jobs: [] }; }
  }

  function writeCronJobs(data) {
    fs.writeFileSync(path.join(CRON_DIR, "jobs.json"), JSON.stringify(data, null, 2));
    cachedData = null; // invalidate cache
  }

  // POST /api/cron/toggle — enable/disable a cron job
  if (url.pathname === "/api/cron/toggle" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let d = ""; req.on("data", c => d += c);
      req.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve({}); } });
    });
    const { jobId, enabled } = body;
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      if (!jobId) throw new Error("jobId required");
      const data = readCronJobs();
      const job = data.jobs.find(j => j.id === jobId);
      if (!job) throw new Error("Job not found: " + jobId);
      job.enabled = !!enabled;
      job.updatedAtMs = Date.now();
      writeCronJobs(data);
      res.end(JSON.stringify({ status: "ok", jobId, enabled: job.enabled }));
    } catch (e) {
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // POST /api/cron/delete — delete a cron job
  if (url.pathname === "/api/cron/delete" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let d = ""; req.on("data", c => d += c);
      req.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve({}); } });
    });
    const { jobId } = body;
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      if (!jobId) throw new Error("jobId required");
      const data = readCronJobs();
      const idx = data.jobs.findIndex(j => j.id === jobId);
      if (idx === -1) throw new Error("Job not found: " + jobId);
      const removed = data.jobs.splice(idx, 1)[0];
      writeCronJobs(data);
      res.end(JSON.stringify({ status: "ok", jobId, removed: removed.name }));
    } catch (e) {
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // POST /api/cron/create — create a new cron job
  if (url.pathname === "/api/cron/create" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let d = ""; req.on("data", c => d += c);
      req.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve({}); } });
    });
    const { agentId, skillId, cronExpr, startDate, endDate, deliveryChannel, deliveryTo } = body;
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      if (!agentId || !skillId || !cronExpr) throw new Error("agentId, skillId, cronExpr required");
      if (!getAllBots().includes(agentId)) throw new Error("Invalid agentId");
      const registry = scanAllSkills();
      const skill = registry.skills[skillId];
      if (!skill) throw new Error("Unknown skill: " + skillId);

      const crypto = require("crypto");
      const jobId = crypto.randomUUID();
      const now = Date.now();

      const job = {
        id: jobId,
        agentId,
        name: `${agentId}-${skillId}`,
        description: `定时执行 ${skill.name || skillId}`,
        enabled: true,
        createdAtMs: now,
        updatedAtMs: now,
        schedule: {
          kind: "cron",
          expr: cronExpr,
          tz: "Asia/Shanghai"
        },
        sessionTarget: "isolated",
        wakeMode: "now",
        payload: {
          kind: "agentTurn",
          message: `Read skills/${skillId}/SKILL.md 加载完整流程，然后按流程执行。`
        },
        delivery: deliveryChannel ? {
          mode: "announce",
          channel: deliveryChannel,
          to: deliveryTo || "",
          bestEffort: true
        } : { mode: "none" },
        state: { consecutiveErrors: 0 }
      };

      if (startDate) job.startDate = startDate;
      if (endDate) job.endDate = endDate;

      const data = readCronJobs();
      data.jobs.push(job);
      writeCronJobs(data);
      res.end(JSON.stringify({ status: "ok", job }));
    } catch (e) {
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // POST /api/cron/update — update cron job fields
  if (url.pathname === "/api/cron/update" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let d = ""; req.on("data", c => d += c);
      req.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve({}); } });
    });
    const { jobId, cronExpr, startDate, endDate } = body;
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      if (!jobId) throw new Error("jobId required");
      const data = readCronJobs();
      const job = data.jobs.find(j => j.id === jobId);
      if (!job) throw new Error("Job not found: " + jobId);
      if (cronExpr) job.schedule.expr = cronExpr;
      if (startDate !== undefined) job.startDate = startDate || undefined;
      if (endDate !== undefined) job.endDate = endDate || undefined;
      job.updatedAtMs = Date.now();
      writeCronJobs(data);
      res.end(JSON.stringify({ status: "ok", jobId }));
    } catch (e) {
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // POST /api/agent/rename — rename an agent
  if (url.pathname === "/api/agent/rename" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let d = ""; req.on("data", c => d += c);
      req.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve({}); } });
    });
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      const { botId, name } = body;
      if (!botId || !name?.trim()) throw new Error("botId and name required");
      const newName = name.trim();

      const ocData = JSON.parse(fs.readFileSync(OPENCLAW_JSON, "utf8"));

      // Update agents.list
      const agent = (ocData.agents?.list || []).find(a => a.id === botId);
      if (!agent) throw new Error(`Agent ${botId} not found`);
      agent.name = newName;

      // Update feishu account name if exists
      if (ocData.channels?.feishu?.accounts?.[botId]) {
        ocData.channels.feishu.accounts[botId].name = newName;
      }

      fs.writeFileSync(OPENCLAW_JSON, JSON.stringify(ocData, null, 2));
      regenerateContactDirectory();
      cachedData = null;
      res.end(JSON.stringify({ status: "ok", botId, name: newName }));
    } catch (e) {
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // GET /api/agent/next-id — compute next available bot number
  if (url.pathname === "/api/agent/next-id" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    const existing = getEditorialBots().map(id => parseInt(id.replace("bot", ""))).filter(n => !isNaN(n));
    let next = 1;
    while (existing.includes(next)) next++;
    res.end(JSON.stringify({ nextId: `bot${next}`, nextNum: next }));
    return;
  }

  // POST /api/agent/create — create a new editorial bot
  if (url.pathname === "/api/agent/create" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let d = ""; req.on("data", c => d += c);
      req.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve({}); } });
    });
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      // 1. Password check
      if (body.password !== ADMIN_PASSWORD) throw new Error("密码错误");

      // 2. Determine botId
      const existing = getEditorialBots().map(id => parseInt(id.replace("bot", ""))).filter(n => !isNaN(n));
      let botNum = 1;
      while (existing.includes(botNum)) botNum++;
      const botId = `bot${botNum}`;
      const botName = body.name || botId;

      // 3. Port allocation
      const mcpPort = 18060 + botNum;
      const cdpPort = 18800 + botNum;

      // 4. Create agents/botN/ directory structure
      const agentDir = path.join(AGENTS_DIR, botId);
      const agentAgentDir = path.join(agentDir, "agent");
      const sessionsDir = path.join(agentDir, "sessions");
      fs.mkdirSync(agentAgentDir, { recursive: true });
      fs.mkdirSync(sessionsDir, { recursive: true });

      // Copy models.json from bot1 as template
      const templateModels = path.join(AGENTS_DIR, "bot1", "agent", "models.json");
      if (fs.existsSync(templateModels)) {
        fs.copyFileSync(templateModels, path.join(agentAgentDir, "models.json"));
      }
      fs.writeFileSync(path.join(agentAgentDir, "auth-profiles.json"), "{}");
      fs.writeFileSync(path.join(sessionsDir, "sessions.json"), "{}");

      // 5. Create workspace-botN/ directory structure
      const wsDir = path.join(OPENCLAW_DIR, `workspace-${botId}`);
      fs.mkdirSync(path.join(wsDir, "skills"), { recursive: true });
      fs.mkdirSync(path.join(wsDir, "memory"), { recursive: true });
      fs.mkdirSync(path.join(wsDir, "config"), { recursive: true });

      // Create empty MD files
      for (const f of ["SOUL.md", "IDENTITY.md", "USER.md", "MEMORY.md", "HEARTBEAT.md"]) {
        fs.writeFileSync(path.join(wsDir, f), "");
      }

      // Create AGENTS.md with basic template
      fs.writeFileSync(path.join(wsDir, "AGENTS.md"), `# ${botName} 工作手册\n\n> 首次启动，请与研究部确认人设。\n`);

      // Create TOOLS.md referencing common tools
      fs.writeFileSync(path.join(wsDir, "TOOLS.md"), `> 首先 Read ../workspace/TOOLS_COMMON.md 获取统一工具规范\n\n## Bot 专属配置\n- account_id: ${botId}\n- 小红书 MCP 端口: ${mcpPort}\n`);

      // Create EQUIPPED_SKILLS.md (empty)
      fs.writeFileSync(path.join(wsDir, "EQUIPPED_SKILLS.md"), "# 已装备技能\n\n（暂无装备）\n");

      // Create mcporter.json
      fs.writeFileSync(path.join(wsDir, "config", "mcporter.json"), JSON.stringify({
        mcpServers: {
          "xiaohongshu-mcp": { baseUrl: `http://localhost:${mcpPort}/mcp` },
          "research-mcp": { url: "http://research-mcp.jijinmima.cn/mcp" },
          "image-gen-mcp": { url: "http://localhost:18085/mcp" }
        },
        imports: []
      }, null, 4));

      // Symlink universal skills
      const universalSkillsDir = path.join(OPENCLAW_DIR, "workspace", "skills");
      const defaultSkills = ["frontline", "xhs-op", "browser-base", "report-incident", "research-mcp"];
      for (const skill of defaultSkills) {
        const target = path.join(universalSkillsDir, skill);
        const link = path.join(wsDir, "skills", skill);
        if (fs.existsSync(target) && !fs.existsSync(link)) {
          fs.symlinkSync(`../../workspace/skills/${skill}`, link);
        }
      }

      // 6. Update openclaw.json
      const ocData = JSON.parse(fs.readFileSync(OPENCLAW_JSON, "utf8"));

      // Add to agents.list
      const models = body.models || [];
      const primaryModel = models[0] || ocData.agents?.defaults?.model?.primary || "legacylands/claude-opus-4-6";
      const agentEntry = {
        id: botId,
        name: botName,
        workspace: path.join(OPENCLAW_DIR, `workspace-${botId}`),
        agentDir: agentAgentDir,
        model: { primary: primaryModel }
      };
      if (models.length > 1) {
        agentEntry.model.fallbacks = models.slice(1);
      }
      // Add tools.alsoAllow (same as other bots)
      agentEntry.tools = { alsoAllow: [
        "tushare_stock_list", "tushare_stock_daily", "tushare_stock_weekly",
        "tushare_stock_monthly", "tushare_adj_factor", "tushare_daily_basic",
        "tushare_income", "tushare_index_basic", "tushare_index_daily",
        "tushare_index_weight", "tushare_index_monthly", "tushare_fund_basic",
        "tushare_fund_nav", "tushare_fund_portfolio"
      ]};

      // Insert before the last non-editorial entries (skills/coder)
      if (!ocData.agents) ocData.agents = { list: [] };
      if (!ocData.agents.list) ocData.agents.list = [];
      ocData.agents.list.push(agentEntry);

      // Add binding
      if (!ocData.bindings) ocData.bindings = [];
      ocData.bindings.push({
        agentId: botId,
        match: { channel: "feishu", accountId: botId }
      });

      // Add feishu account if provided
      if (body.feishuAppId && body.feishuAppSecret) {
        if (!ocData.channels) ocData.channels = {};
        if (!ocData.channels.feishu) ocData.channels.feishu = { accounts: {} };
        if (!ocData.channels.feishu.accounts) ocData.channels.feishu.accounts = {};
        ocData.channels.feishu.accounts[botId] = {
          enabled: true,
          appId: body.feishuAppId,
          appSecret: body.feishuAppSecret,
          name: botName,
          domain: "feishu",
          connectionMode: "websocket",
          dmPolicy: "open",
          groupPolicy: "open",
          allowFrom: ["*"]
        };
      }

      // Add browser profile
      if (!ocData.browser) ocData.browser = { profiles: {} };
      if (!ocData.browser.profiles) ocData.browser.profiles = {};
      ocData.browser.profiles[botId] = { cdpPort: cdpPort, color: "#888888" };

      fs.writeFileSync(OPENCLAW_JSON, JSON.stringify(ocData, null, 2));

      // 7. Update bot-equipment.json
      const equipData = JSON.parse(fs.readFileSync(BOT_EQUIPMENT_FILE, "utf8"));
      if (!equipData.bots) equipData.bots = {};
      equipData.bots[botId] = {
        slots: {
          "helm-1": "frontline",
          "armor-1": null,
          "accessory-1": null,
          "accessory-2": null,
          "utility-1": null,
          "utility-2": null,
          "utility-3": null,
          "utility-4": null,
          "research-1": null,
          "research-2": null,
          "research-3": null,
          "research-4": null,
          "research-5": null,
          "research-6": null,
          "boots-1": null,
          "scheduled-1": null,
          "scheduled-2": null,
          "scheduled-3": null,
          "scheduled-4": null,
          "scheduled-5": null,
          "scheduled-6": null
        },
        overflow: []
      };
      fs.writeFileSync(BOT_EQUIPMENT_FILE, JSON.stringify(equipData, null, 2));

      // 8. Start xiaohongshu-mcp instance
      let mcpStarted = false;
      if (fs.existsSync(XHS_MCP_BIN)) {
        try {
          const { spawn: spawnProc } = require("child_process");
          const logFile = `/tmp/xhs-mcp-${botId}.log`;
          const mcpProc = spawnProc(XHS_MCP_BIN, [`-headless=true`, `-port=:${mcpPort}`], {
            env: { ...process.env, DISPLAY: ":99", XHS_PROFILES_DIR },
            stdio: ["ignore", fs.openSync(logFile, "a"), fs.openSync(logFile, "a")],
            detached: true
          });
          mcpProc.unref();
          mcpStarted = true;
        } catch (e) {
          console.error(`Failed to start MCP for ${botId}:`, e.message);
        }
      }

      // Regenerate contact directory & clear cache
      regenerateContactDirectory();
      cachedData = null;

      res.end(JSON.stringify({
        status: "ok",
        botId,
        botName,
        mcpPort,
        cdpPort,
        workspace: wsDir,
        mcpStarted,
        note: mcpStarted ? "MCP 已启动，需手动登录小红书 cookie" : "MCP 二进制不存在，需手动启动"
      }));
    } catch (e) {
      res.end(JSON.stringify({ status: "error", error: e.message }));
    }
    return;
  }

  // POST /api/agent/delete — delete an editorial bot (backup workspace, remove configs)
  if (url.pathname === "/api/agent/delete" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let d = ""; req.on("data", c => d += c);
      req.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve({}); } });
    });
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      // 1. Password check (different from create password)
      if (body.password !== DELETE_PASSWORD) throw new Error("删除密码错误");

      const botId = body.botId;
      if (!botId || !/^bot\d+$/.test(botId)) throw new Error("无效的 botId");

      // Prevent deleting non-existent agents
      const agentDir = path.join(AGENTS_DIR, botId);
      if (!fs.existsSync(agentDir)) throw new Error(`Agent ${botId} 不存在`);

      const botNum = parseInt(botId.replace("bot", ""));
      const mcpPort = 18060 + botNum;
      const wsDir = path.join(OPENCLAW_DIR, `workspace-${botId}`);
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);

      // 2. Kill MCP instance on its port
      try {
        const pid = execSync(`lsof -ti:${mcpPort} 2>/dev/null || true`, { encoding: "utf8" }).trim();
        if (pid) {
          execSync(`kill ${pid} 2>/dev/null || true`);
        }
      } catch {}

      // 3. Rename workspace to backup (keeps data, frees botId)
      if (fs.existsSync(wsDir)) {
        const backupName = `workspace-${botId}-deleted-${timestamp}`;
        fs.renameSync(wsDir, path.join(OPENCLAW_DIR, backupName));
      }

      // 4. Remove agents/botN/ directory entirely
      fs.rmSync(agentDir, { recursive: true, force: true });

      // 5. Update openclaw.json — remove from agents.list, bindings, feishu accounts, browser profiles
      const ocData = JSON.parse(fs.readFileSync(OPENCLAW_JSON, "utf8"));

      if (ocData.agents?.list) {
        ocData.agents.list = ocData.agents.list.filter(a => a.id !== botId);
      }
      if (ocData.bindings) {
        ocData.bindings = ocData.bindings.filter(b => b.agentId !== botId);
      }
      if (ocData.channels?.feishu?.accounts?.[botId]) {
        delete ocData.channels.feishu.accounts[botId];
      }
      if (ocData.browser?.profiles?.[botId]) {
        delete ocData.browser.profiles[botId];
      }

      fs.writeFileSync(OPENCLAW_JSON, JSON.stringify(ocData, null, 2));

      // 6. Remove from bot-equipment.json
      const equipData = JSON.parse(fs.readFileSync(BOT_EQUIPMENT_FILE, "utf8"));
      if (equipData.bots?.[botId]) {
        delete equipData.bots[botId];
        fs.writeFileSync(BOT_EQUIPMENT_FILE, JSON.stringify(equipData, null, 2));
      }

      // 7. Regenerate contact directory & clear cache
      regenerateContactDirectory();
      cachedData = null;

      res.end(JSON.stringify({
        status: "ok",
        botId,
        backupWorkspace: fs.existsSync(path.join(OPENCLAW_DIR, `workspace-${botId}-deleted-${timestamp}`))
          ? `workspace-${botId}-deleted-${timestamp}` : null,
        note: "Agent 已删除，workspace 已备份重命名"
      }));
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

  // --- Avatar API ---
  const IMG_EXTS = [".png", ".jpg", ".jpeg", ".webp"];
  const MIME_MAP = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp" };

  if (url.pathname === "/api/bot/avatar" && req.method === "GET") {
    const botId = url.searchParams.get("botId");
    if (!botId) { res.writeHead(400); res.end("Missing botId"); return; }
    const wsDir = path.join(OPENCLAW_DIR, botWorkspaceDir(botId));
    let found = null;
    for (const ext of IMG_EXTS) {
      const p = path.join(wsDir, "avatar" + ext);
      if (fs.existsSync(p)) { found = p; break; }
    }
    if (!found) { res.writeHead(404); res.end("No avatar"); return; }
    const ext = path.extname(found).toLowerCase();
    res.writeHead(200, { "Content-Type": MIME_MAP[ext] || "application/octet-stream", "Cache-Control": "no-cache" });
    fs.createReadStream(found).pipe(res);
    return;
  }

  if (url.pathname === "/api/bot/images" && req.method === "GET") {
    const botId = url.searchParams.get("botId");
    if (!botId) { res.writeHead(400); res.end("Missing botId"); return; }
    const wsDir = path.join(OPENCLAW_DIR, botWorkspaceDir(botId));
    const images = [];
    function walk(dir, rel) {
      let entries;
      try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
      for (const e of entries) {
        if (e.name.startsWith(".")) continue;
        const full = path.join(dir, e.name);
        const r = rel ? rel + "/" + e.name : e.name;
        if (e.isDirectory()) { walk(full, r); }
        else if (IMG_EXTS.includes(path.extname(e.name).toLowerCase())) { images.push(r); }
      }
    }
    walk(wsDir, "");
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(images));
    return;
  }

  if (url.pathname === "/api/bot/avatar" && req.method === "POST") {
    const botId = url.searchParams.get("botId");
    if (!botId) { res.writeHead(400); res.end("Missing botId"); return; }
    let body = "";
    req.on("data", c => body += c);
    req.on("end", () => {
      try {
        const { path: imgPath } = JSON.parse(body);
        const wsDir = path.join(OPENCLAW_DIR, botWorkspaceDir(botId));
        const src = path.join(wsDir, imgPath);
        if (!fs.existsSync(src)) { res.writeHead(404); res.end("Image not found"); return; }
        // Ensure src is inside wsDir
        if (!fs.realpathSync(src).startsWith(fs.realpathSync(wsDir))) { res.writeHead(403); res.end("Forbidden"); return; }
        const ext = path.extname(imgPath).toLowerCase();
        // Remove old avatars
        for (const e of IMG_EXTS) {
          const old = path.join(wsDir, "avatar" + e);
          if (fs.existsSync(old)) fs.unlinkSync(old);
        }
        const dest = path.join(wsDir, "avatar" + ext);
        fs.copyFileSync(src, dest);
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true, avatar: "avatar" + ext }));
      } catch (e) {
        res.writeHead(500); res.end(e.message);
      }
    });
    return;
  }

  // Serve workspace images (for avatar picker thumbnails)
  if (url.pathname.startsWith("/api/bot/image/") && req.method === "GET") {
    const botId = url.searchParams.get("botId");
    const imgPath = decodeURIComponent(url.pathname.slice("/api/bot/image/".length));
    if (!botId || !imgPath) { res.writeHead(400); res.end("Missing params"); return; }
    const wsDir = path.join(OPENCLAW_DIR, botWorkspaceDir(botId));
    const full = path.join(wsDir, imgPath);
    if (!fs.existsSync(full)) { res.writeHead(404); res.end("Not found"); return; }
    try {
      if (!fs.realpathSync(full).startsWith(fs.realpathSync(wsDir))) { res.writeHead(403); res.end("Forbidden"); return; }
    } catch { res.writeHead(404); res.end("Not found"); return; }
    const ext = path.extname(full).toLowerCase();
    res.writeHead(200, { "Content-Type": MIME_MAP[ext] || "application/octet-stream", "Cache-Control": "max-age=3600" });
    fs.createReadStream(full).pipe(res);
    return;
  }

  res.writeHead(404);
  res.end("Not Found");
});

server.listen(PORT, () => {
  console.log(`📮 Agent Message Dashboard: http://localhost:${PORT}`);
});
