#!/usr/bin/env node
// Agent Message Dashboard Server
// Usage: node server.js [port]  (default: 18888)

const http = require("http");
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");
const { execSync, execFile, spawn } = require("child_process");
const sharp = require("sharp");
const ExcelJS = require("exceljs");

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
const PUBLISH_QUEUE = "/home/rooot/.openclaw/workspace-sys1/publish-queue";
const AGENTS_DIR = "/home/rooot/.openclaw/agents";
const CRON_DIR = "/home/rooot/.openclaw/cron";
const OPENCLAW_JSON = "/home/rooot/.openclaw/openclaw.json";
const OPENCLAW_DIR = "/home/rooot/.openclaw";
const COMMERCIAL_HOST = "127.0.0.1";
const COMMERCIAL_PORT = 18900;
const COMMERCIAL_RESEARCH_TOKEN_FILE = "/home/rooot/.openclaw/commercial/server/.research-approval-token";
const ARMORY_CONFIG_FILE = path.join(__dirname, "armory-config.json");
const BOT_EQUIPMENT_FILE = path.join(__dirname, "bot-equipment.json");
const GEM_REGISTRY_FILE = path.join(__dirname, "gem-registry.json");
const BOT_COLORS_FILE = path.join(__dirname, "bot-colors.json");
const ADMIN_PASSWORD = "openclaw2026";
const DELETE_PASSWORD = "delete2026";
const SYSTEM_BOT_IDS = new Set(["mag1", "sys1", "sys2", "sys3", "sys4"]);
const XHS_MCP_BIN = "/home/rooot/MCP/xiaohongshu-mcp/xiaohongshu-mcp";
const XHS_HEADED_BIN = "/home/rooot/MCP/xiaohongshu-mcp/headed-login";
const XHS_PROFILES_BASE = "/home/rooot/.xhs-profiles";

// --- XHS Live View (headed Chrome on VNC) ---
let xhsLiveProc = null; // { proc, botId }
function killXhsLive() {
  if (xhsLiveProc) {
    try { process.kill(-xhsLiveProc.proc.pid, "SIGTERM"); } catch {}
    xhsLiveProc = null;
  }
}
function startXhsLive(botId) {
  killXhsLive();
  const proc = spawn(XHS_HEADED_BIN, ["-bot", botId, "-profiles-base", XHS_PROFILES_BASE], {
    env: { ...process.env, DISPLAY: ":99" },
    detached: true,
    stdio: "ignore",
  });
  proc.unref();
  proc.on("exit", () => { if (xhsLiveProc?.proc === proc) xhsLiveProc = null; });
  xhsLiveProc = { proc, botId };
  return proc.pid;
}

// --- Avatar thumbnail cache ---
const AVATAR_CACHE_DIR = path.join(__dirname, "avatar-cache");
const THUMB_MAX_W = 280;
const THUMB_MAX_H = 360;
const AVATAR_MAX_SIZE = 2 * 1024 * 1024; // 2MB limit on originals
let avatarCache = {}; // { botId: "data:image/webp;base64,..." }

if (!fs.existsSync(AVATAR_CACHE_DIR)) fs.mkdirSync(AVATAR_CACHE_DIR, { recursive: true });

async function generateThumbnail(botId) {
  const wsDir = path.join(OPENCLAW_DIR, botWorkspaceDir(botId));
  let src = null;
  for (const ext of [".png", ".jpg", ".jpeg", ".webp"]) {
    const p = path.join(wsDir, "avatar" + ext);
    if (fs.existsSync(p)) { src = p; break; }
  }
  if (!src) {
    delete avatarCache[botId];
    const thumbPath = path.join(AVATAR_CACHE_DIR, botId + ".webp");
    if (fs.existsSync(thumbPath)) fs.unlinkSync(thumbPath);
    return null;
  }
  const thumbPath = path.join(AVATAR_CACHE_DIR, botId + ".webp");
  await sharp(src).resize(THUMB_MAX_W, THUMB_MAX_H, { fit: "cover" }).webp({ quality: 80 }).toFile(thumbPath);
  const b64 = fs.readFileSync(thumbPath, "base64");
  const dataUri = "data:image/webp;base64," + b64;
  avatarCache[botId] = dataUri;
  return dataUri;
}

async function buildAvatarCache() {
  const entries = fs.readdirSync(OPENCLAW_DIR, { withFileTypes: true });
  const promises = [];
  for (const e of entries) {
    if (!e.isDirectory() || !e.name.startsWith("workspace-")) continue;
    const botId = e.name.replace("workspace-", "");
    // Check if any avatar file exists
    let hasAvatar = false;
    for (const ext of [".png", ".jpg", ".jpeg", ".webp"]) {
      if (fs.existsSync(path.join(OPENCLAW_DIR, e.name, "avatar" + ext))) { hasAvatar = true; break; }
    }
    if (!hasAvatar) continue;
    // Check if thumb is up-to-date
    const thumbPath = path.join(AVATAR_CACHE_DIR, botId + ".webp");
    if (fs.existsSync(thumbPath)) {
      let srcPath = null;
      for (const ext of [".png", ".jpg", ".jpeg", ".webp"]) {
        const p = path.join(OPENCLAW_DIR, e.name, "avatar" + ext);
        if (fs.existsSync(p)) { srcPath = p; break; }
      }
      if (srcPath && fs.statSync(thumbPath).mtimeMs >= fs.statSync(srcPath).mtimeMs) {
        // Thumb is up-to-date, just load into memory
        const b64 = fs.readFileSync(thumbPath, "base64");
        avatarCache[botId] = "data:image/webp;base64," + b64;
        continue;
      }
    }
    promises.push(generateThumbnail(botId).catch(err => console.error(`Avatar thumb failed for ${botId}:`, err.message)));
  }
  await Promise.all(promises);
  console.log(`🖼️  Avatar cache built: ${Object.keys(avatarCache).length} thumbnails`);
}
const XHS_PROFILES_DIR = "/home/rooot/.xhs-profiles";

function getEditorialBots() {
  return getKnownAgentIds().filter(id => /^bot\d+$/.test(id)).sort((a, b) => {
    return parseInt(a.replace("bot", "")) - parseInt(b.replace("bot", ""));
  });
}
function getAllBots() {
  return [...getEditorialBots(), ...getKnownAgentIds().filter(id => !(/^bot\d+$/.test(id)))];
}

const FEISHU_ID_SKILL = path.join(OPENCLAW_DIR, "workspace/skills/utility/contact-book/SKILL.md");

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

// ── Contact Book: parse SKILL.md → { groups, users } with mtime cache ──
const CONTACT_BOOK_PATH = path.join(OPENCLAW_DIR, "workspace/skills/utility/contact-book/SKILL.md");
let _contactBookCache = null;
let _contactBookMtime = 0;

function getContactBook() {
  let mtime = 0;
  try { mtime = fs.statSync(CONTACT_BOOK_PATH).mtimeMs; } catch { return { groups: [], users: [] }; }
  if (_contactBookCache && mtime === _contactBookMtime) return _contactBookCache;

  const md = fs.readFileSync(CONTACT_BOOK_PATH, "utf8");
  const groups = [];
  const users = [];

  // Parse 群聊 table: | 群名称 | Chat ID |
  const groupSection = md.match(/## 群聊[\s\S]*?(?=\n---|\n## )/);
  if (groupSection) {
    for (const m of groupSection[0].matchAll(/\|\s*(.+?)\s*\|\s*`(oc_[a-f0-9]+)`\s*\|/g)) {
      groups.push({ label: m[1].trim(), chatId: m[2] });
    }
  }

  // Parse 用户 section: ### Name, then per-bot open_id tables
  const userSection = md.match(/## 用户[\s\S]*/);
  if (userSection) {
    const userBlocks = userSection[0].split(/\n### /).slice(1);
    for (const block of userBlocks) {
      const name = block.split("\n")[0].trim();
      const openIds = {};
      for (const m of block.matchAll(/\|\s*([^|]+?)\s*\|\s*`(ou_[a-f0-9]+)`\s*\|/g)) {
        // botId field may contain multiple bots: "bot2, bot5"
        for (const b of m[1].split(/[,，]\s*/)) {
          const botId = b.trim();
          if (botId) openIds[botId] = m[2];
        }
      }
      if (Object.keys(openIds).length) users.push({ name, openIds });
    }
  }

  _contactBookCache = { groups, users };
  _contactBookMtime = mtime;
  return _contactBookCache;
}

function botWorkspaceDir(botId) {
  const mapping = { mag1: "workspace-mag1", main: "workspace-mag1", sys1: "workspace-sys1", sys2: "workspace-sys2", sys3: "workspace-sys3", sys4: "workspace-sys4" };
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
  // Collect (streamId, message_id) from every inbox/outbox stream, then top-N merge
  // by stream ID (which is time-ordered, ms-seq). Only HMGET the global top-N details —
  // not every ID from every stream. This keeps the Lua EVAL payload bounded by `limit`
  // instead of scaling with total message volume.
  const streamKeys = [
    ...redis('KEYS "agentmsg:inbox:*"').split("\n").filter(Boolean),
    ...redis('KEYS "agentmsg:outbox:*"').split("\n").filter(Boolean),
  ];

  // Per-stream cap: small. Global top-N across N streams only needs a few from each.
  const perStream = Math.min(limit, 30);
  const seen = new Set();
  const candidates = []; // { streamId, msgId }

  for (const key of streamKeys) {
    const out = redis(`XREVRANGE ${key} + - COUNT ${perStream}`);
    if (!out) continue;
    const lines = out.split("\n").filter(Boolean);
    let curStreamId = null;
    for (let i = 0; i < lines.length; i++) {
      // Stream ID = "<epoch-ms>-<seq>", ms is 13 digits
      if (/^\d{13}-\d+$/.test(lines[i])) {
        curStreamId = lines[i];
        continue;
      }
      if (lines[i] === "message_id" && lines[i + 1] && curStreamId) {
        const msgId = lines[i + 1];
        if (!seen.has(msgId)) {
          seen.add(msgId);
          candidates.push({ streamId: curStreamId, msgId });
        }
      }
    }
  }

  // Top-N by stream ID desc (= newest first)
  const cmpStreamId = (a, b) => {
    const [am, as] = a.split("-").map(Number);
    const [bm, bs] = b.split("-").map(Number);
    return (bm - am) || (bs - as);
  };
  candidates.sort((a, b) => cmpStreamId(a.streamId, b.streamId));
  const idList = candidates.slice(0, limit).map(c => c.msgId);

  // Fetch only the top-N message details in one Redis call using Lua script
  const fields = ["message_id", "from", "to", "type", "status", "content", "created_at", "reply_to_message_id", "trace", "metadata"];
  const messages = [];
  if (idList.length === 0) return messages;

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
    const accountMatch = content.match(/^account_id:\s*(\S+)/m);
    return {
      title: titleMatch ? titleMatch[1] : "",
      summary: contentMatch ? contentMatch[1].slice(0, 60) : "",
      accountId: accountMatch ? accountMatch[1] : ""
    };
  } catch { return { title: "", summary: "", accountId: "" }; }
}

const HOLD_MINUTES = 5;
const releasedEntries = new Set();  // tracks pending entries already released to sys1

function readPostFull(filePath) {
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    const fmMatch = raw.match(/^---\n([\s\S]*?)\n---/);
    if (!fmMatch) return null;
    const fm = fmMatch[1];
    const body = raw.slice(fmMatch[0].length).trim();

    const get = (key) => {
      const m = fm.match(new RegExp(`^${key}:\\s*"([\\s\\S]*?)"\\s*$`, "m"));
      if (m) return m[1].replace(/\\"/g, '"');
      const m2 = fm.match(new RegExp(`^${key}:\\s*(.+)$`, "m"));
      return m2 ? m2[1].trim() : "";
    };
    const getArray = (key) => {
      const m = fm.match(new RegExp(`^${key}:\\s*\\[(.*)\\]`, "m"));
      if (!m) return [];
      return m[1].split(",").map(s => s.trim().replace(/^"|"$/g, "")).filter(Boolean).map(v => {
        if (key !== "tags") return v;
        return v.replace(/^#+|#+$/g, "").replace(/\[话题\]$/g, "").trim();
      }).filter(Boolean);
    };

    return {
      account_id: get("account_id"),
      publish_type: get("publish_type"),
      content_mode: get("content_mode"),
      title: get("title"),
      content: get("content"),
      text_image: get("text_image"),
      image_style: get("image_style"),
      visibility: get("visibility"),
      images: getArray("images"),
      tags: getArray("tags"),
      schedule_at: get("schedule_at"),
      is_original: get("is_original") === "true",
      submitted_by: get("submitted_by"),
      submitted_at: get("submitted_at"),
      reply_to: get("reply_to"),
      desc: get("desc"),
      video: get("video"),
      body: body
    };
  } catch { return null; }
}

// Track active worker processes for SSE streaming
const activeWorkers = new Map(); // folderName -> { lines: [], done: bool, exitCode: int|null }

function wakeSys1ForEntry(folderName, postMeta) {
  // 2026-04-16: 用 publish-worker.py 替代 sys1 Agent，流程化发布无需 LLM
  const globalLog = path.join(__dirname, "..", "workspace-sys1", "publish-queue", "worker.log");
  const globalFd = fs.openSync(globalLog, "a");
  const state = { lines: [], done: false, exitCode: null };
  activeWorkers.set(folderName, state);

  const child = spawn("python3", [
    "-u",
    path.join(__dirname, "..", "scripts", "publish-worker.py"),
    folderName
  ], { stdio: ["ignore", "pipe", "pipe"], detached: true });

  const handleData = (chunk) => {
    const text = chunk.toString();
    // Write to global log
    fs.writeSync(globalFd, text);
    // Buffer lines for SSE
    for (const line of text.split("\n")) {
      if (line !== "") state.lines.push(line);
    }
  };
  child.stdout.on("data", handleData);
  child.stderr.on("data", handleData);
  child.on("close", (code) => {
    state.done = true;
    state.exitCode = code;
    try { fs.closeSync(globalFd); } catch {}
    // Clean up after 5 minutes
    setTimeout(() => activeWorkers.delete(folderName), 300000);
  });
  child.unref();

  const accountId = postMeta?.account_id || (folderName.match(/_(\w+?)_/) || [])[1] || "?";
  console.log(`[hold-timer] publish-worker.py started for ${folderName} (${accountId})`);
}

const XHS_STATS_FILE = path.join(__dirname, "xhs-stats.json");

function getXhsStats() {
  try {
    return JSON.parse(fs.readFileSync(XHS_STATS_FILE, "utf8"));
  } catch { return null; }
}


function normalizeTitle(t) {
  return (t || "").trim().replace(/\s+/g, " ").replace(/^["']|["']$/g, "");
}

function matchXhsMetrics(publishedList, stats) {
  if (!stats || !stats.bots) return publishedList;
  // Build per-bot title→metrics map
  const lookup = {};
  for (const [bot, data] of Object.entries(stats.bots)) {
    if (!data.notes) continue;
    lookup[bot] = {};
    for (const note of data.notes) {
      const key = normalizeTitle(note.title);
      if (key) lookup[bot][key] = {
        publish_time: note.publish_time || "",
        impressions: note.impressions || "-",
        views: note.views || "0",
        click_rate: note.click_rate || "-",
        likes: note.likes || "0",
        comments: note.comments || "0",
        favorites: note.favorites || "0",
        new_followers: note.new_followers || "-",
        shares: note.shares || "0",
        avg_watch_time: note.avg_watch_time || "-",
        danmaku: note.danmaku || "-"
      };
    }
  }
  // Track which stats notes were matched by queue items
  const matched = {};  // bot -> Set of normalized titles
  // Match each published item
  const result = publishedList.map(item => {
    const bot = item.accountId || "";
    const title = normalizeTitle(item.title);
    const metrics = (lookup[bot] && lookup[bot][title]) || null;
    if (metrics) {
      if (!matched[bot]) matched[bot] = new Set();
      matched[bot].add(title);
    }
    return { ...item, metrics };
  });
  // Append unmatched notes from stats as discovered entries (not published via 印务局)
  for (const [bot, data] of Object.entries(stats.bots)) {
    if (!data.notes) continue;
    for (const note of data.notes) {
      const title = normalizeTitle(note.title);
      if (!title) continue;
      if (matched[bot] && matched[bot].has(title)) continue;
      // Build synthetic name for front-end compatibility: date_botId_discovered
      const pt = (note.publish_time || "").replace(/ /g, "T").replace(/:/g, "-");
      const name = `${pt || "unknown"}_${bot}_discovered`;
      result.push({
        name,
        title: note.title,
        summary: "",
        accountId: bot,
        metrics: lookup[bot][title],
      });
    }
  }
  return result;
}

function getPublishQueue() {
  const result = { pending: [], publishing: [], published: [], failed: [] };
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

        // Pending items: return full metadata for preview + hold countdown
        if (status === "pending") {
          let full = null;
          if (stat.isDirectory()) {
            const postMd = path.join(fullPath, "post.md");
            if (fs.existsSync(postMd)) full = readPostFull(postMd);
          } else if (f.endsWith(".md")) {
            full = readPostFull(fullPath);
          }
          if (!full) full = { title: "", content: "", account_id: "" };
          // Fallback accountId from filename
          if (!full.account_id) {
            const m = f.match(/_(\w+?)_/) || f.match(/-(bot\d+)-/);
            if (m) full.account_id = m[1];
          }
          const submittedMs = full.submitted_at ? new Date(full.submitted_at).getTime() : 0;
          const holdDeadline = submittedMs ? submittedMs + HOLD_MINUTES * 60000 : 0;
          const remainingSec = Math.max(0, Math.ceil((holdDeadline - Date.now()) / 1000));
          return { name: f, ...full, accountId: full.account_id, remainingSec, isHeld: remainingSec > 0 };
        }

        // Failed items: lightweight metadata + error reason
        if (status === "failed") {
          let meta = { title: "", summary: "" };
          let errorReason = "";
          if (stat.isDirectory()) {
            const postMd = path.join(fullPath, "post.md");
            if (fs.existsSync(postMd)) meta = readPostMeta(postMd);
            const errFile = path.join(fullPath, "error.txt");
            if (fs.existsSync(errFile)) {
              const lines = fs.readFileSync(errFile, "utf8").split("\n");
              for (const line of lines) {
                if (line.startsWith("reason:")) { errorReason = line.slice(7).trim(); break; }
              }
            }
          }
          if (!meta.accountId) {
            const m = f.match(/_(\w+?)_/) || f.match(/-(bot\d+)-/);
            if (m) meta.accountId = m[1];
          }
          return { name: f, ...meta, errorReason };
        }

        // Publishing / Published: lightweight metadata only
        let meta = { title: "", summary: "" };
        if (stat.isDirectory()) {
          const postMd = path.join(fullPath, "post.md");
          if (fs.existsSync(postMd)) meta = readPostMeta(postMd);
        } else if (f.endsWith(".md")) {
          meta = readPostMeta(fullPath);
        }
        if (!meta.accountId) {
          const m = f.match(/_(\w+?)_/) || f.match(/-(bot\d+)-/);
          if (m) meta.accountId = m[1];
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

// Chrome process pressure indicator
function getChromePressure() {
  try {
    const total = parseInt(execSync("pgrep -c chrome 2>/dev/null || echo 0", { encoding: "utf8", timeout: 3000 }).trim()) || 0;
    const rod = parseInt(execSync("pgrep -fa chrome 2>/dev/null | grep -c /tmp/rod/ || echo 0", { encoding: "utf8", timeout: 3000 }).trim()) || 0;
    const gateway = parseInt(execSync("pgrep -fa chrome 2>/dev/null | grep -c 'openclaw/browser/' || echo 0", { encoding: "utf8", timeout: 3000 }).trim()) || 0;
    const localhostConns = parseInt(execSync("ss -tn 2>/dev/null | grep -c '127.0.0.1' || echo 0", { encoding: "utf8", timeout: 3000 }).trim()) || 0;
    const other = Math.max(0, total - rod - gateway);
    const level = total <= 50 ? "ok" : total <= 70 ? "warn" : "danger";
    return { total, rod, gateway, other, localhostConns, level };
  } catch {
    return { total: -1, rod: 0, gateway: 0, other: 0, localhostConns: 0, level: "unknown" };
  }
}

// Gzip helper: compress response if client supports it
function sendCompressed(req, res, statusCode, headers, body) {
  const accept = req.headers["accept-encoding"] || "";
  if (accept.includes("gzip")) {
    zlib.gzip(body, (err, compressed) => {
      if (err) { res.writeHead(statusCode, headers); res.end(body); return; }
      headers["Content-Encoding"] = "gzip";
      headers["Content-Length"] = compressed.length;
      res.writeHead(statusCode, headers);
      res.end(compressed);
    });
  } else {
    res.writeHead(statusCode, headers);
    res.end(body);
  }
}

function readJsonBody(req) {
  return new Promise((resolve) => {
    let data = "";
    req.on("data", chunk => data += chunk);
    req.on("end", () => {
      try { resolve(JSON.parse(data || "{}")); } catch { resolve({}); }
    });
  });
}

function getCommercialResearchToken() {
  if (process.env.RESEARCH_APPROVAL_TOKEN) return process.env.RESEARCH_APPROVAL_TOKEN.trim();
  return fs.readFileSync(COMMERCIAL_RESEARCH_TOKEN_FILE, "utf8").trim();
}

function requestCommercial(pathname, method = "GET", body = null) {
  return new Promise((resolve, reject) => {
    let token;
    try {
      token = getCommercialResearchToken();
    } catch (err) {
      reject(new Error(`读取研究部审批令牌失败: ${err.message}`));
      return;
    }

    const payload = body ? JSON.stringify(body) : "";
    const req2 = http.request({
      hostname: COMMERCIAL_HOST,
      port: COMMERCIAL_PORT,
      path: pathname,
      method,
      headers: {
        "x-research-token": token,
        "Content-Type": "application/json",
        ...(payload ? { "Content-Length": Buffer.byteLength(payload) } : {}),
      },
    }, (resp) => {
      let raw = "";
      resp.on("data", chunk => raw += chunk);
      resp.on("end", () => {
        let parsed;
        try { parsed = raw ? JSON.parse(raw) : {}; } catch { parsed = { raw }; }
        resolve({ statusCode: resp.statusCode || 500, data: parsed });
      });
    });

    req2.on("error", reject);
    if (payload) req2.write(payload);
    req2.end();
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);

  if (url.pathname === "/api/data") {
    const headers = {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*"
    };
    const now = Date.now();
    if (!cachedData || now - cacheTime > CACHE_TTL) {
      // Read agent names + feishu config status from openclaw.json
      let feishuStatus = {};
      let botNames = {};
      let botColors = {};
      try {
        const ocData = JSON.parse(fs.readFileSync(OPENCLAW_JSON, "utf8"));
        for (const a of (ocData.agents?.list || [])) {
          if (a.name) botNames[a.id] = a.name;
        }
        try { Object.assign(botColors, JSON.parse(fs.readFileSync(BOT_COLORS_FILE, "utf8"))); } catch {}
        const accounts = ocData.channels?.feishu?.accounts || {};
        for (const [id, acct] of Object.entries(accounts)) {
          if (id === "default") continue;
          feishuStatus[id] = { hasAppId: !!acct.appId, enabled: acct.enabled !== false };
        }
      } catch {}
      const xhsStats = getXhsStats();
      const pq = getPublishQueue();
      if (xhsStats) pq.published = matchXhsMetrics(pq.published, xhsStats);
      cachedData = JSON.stringify({
        timestamp: new Date().toISOString(),
        messages: getMessages(100),
        agentStats: getAgentStats(),
        publishQueue: pq,
        cronJobs: getCronJobs(),
        cronRuns: getRecentCronRuns(30),
        agentSessions: getAgentSessions(),
        allSessions: getAllSessions(),
        feishuStatus,
        editorialBots: getEditorialBots(),
        botNames,
        botColors,
        xhsStatsUpdatedAt: xhsStats ? xhsStats.updated_at : null,
        xhsLoginStatus: xhsStats ? Object.fromEntries(
          Object.entries(xhsStats.bots || {}).map(([bot, data]) => [bot, data.loginStatus || null])
        ) : {},
        chromePressure: getChromePressure()
      });
      cacheTime = now;
    }
    sendCompressed(req, res, 200, headers, cachedData);
    return;
  }

  // POST /api/agent/:id/new — reset all sessions (file-based, instant)
  const newMatch = url.pathname.match(/^\/api\/agent\/([^/]+)\/new$/);
  if (newMatch && req.method === "POST") {
    const agentId = newMatch[1];
    const sessFile = path.join(AGENTS_DIR, agentId, "sessions", "sessions.json");
    try {
      const data = JSON.parse(fs.readFileSync(sessFile, "utf8"));
      const ts = new Date().toISOString().replace(/[:.]/g, "-");
      const results = [];
      for (const [key, sess] of Object.entries(data)) {
        const sid = sess.sessionId;
        if (!sid) continue;
        const jsonlPath = path.join(AGENTS_DIR, agentId, "sessions", sid + ".jsonl");
        try {
          if (fs.existsSync(jsonlPath)) {
            fs.renameSync(jsonlPath, jsonlPath + ".reset." + ts);
          }
          // Clear session metadata so agent fully re-initializes
          delete sess.systemSent;
          delete sess.skillsSnapshot;
          sess.compactionCount = 0;
          sess.abortedLastRun = false;
          results.push({ sessionId: sid, key, status: "ok" });
        } catch (e) {
          results.push({ sessionId: sid, key, status: "error", error: e.message });
        }
      }
      fs.writeFileSync(sessFile, JSON.stringify(data, null, 2));
      cachedData = null; cacheTime = 0;
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ agent: agentId, sessions: results }));
    } catch (e) {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ agent: agentId, error: e.message }));
    }
    return;
  }

  // POST /api/session/new — reset a single session (file-based, instant)
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
      const jsonlPath = path.join(AGENTS_DIR, agentId, "sessions", sessionId + ".jsonl");
      if (fs.existsSync(jsonlPath)) {
        const ts = new Date().toISOString().replace(/[:.]/g, "-");
        fs.renameSync(jsonlPath, jsonlPath + ".reset." + ts);
      }
      // Clear session metadata
      const sessFile = path.join(AGENTS_DIR, agentId, "sessions", "sessions.json");
      try {
        const sessData = JSON.parse(fs.readFileSync(sessFile, "utf8"));
        for (const [, sess] of Object.entries(sessData)) {
          if (sess.sessionId === sessionId) {
            delete sess.systemSent;
            delete sess.skillsSnapshot;
            sess.compactionCount = 0;
            sess.abortedLastRun = false;
            break;
          }
        }
        fs.writeFileSync(sessFile, JSON.stringify(sessData, null, 2));
      } catch {}
      cachedData = null; cacheTime = 0;
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
      const ts = new Date().toISOString().replace(/[:.]/g, "-");
      const results = targets.map(t => {
        try {
          const jsonlPath = path.join(AGENTS_DIR, t.agentId, "sessions", t.sessionId + ".jsonl");
          if (fs.existsSync(jsonlPath)) fs.renameSync(jsonlPath, jsonlPath + ".reset." + ts);
          return { ...t, status: "ok" };
        } catch (e) {
          return { ...t, status: "error", error: e.message };
        }
      });
      cachedData = null; cacheTime = 0;
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
        // Append CLI backend models (claude-cli built-in + configured cliBackends)
        available.push({ provider: "claude-cli", modelId: "opus", name: "CC Opus", reasoning: true });
        available.push({ provider: "claude-cli", modelId: "sonnet", name: "CC Sonnet", reasoning: true });
        const cliBackends = ocData.agents?.defaults?.cliBackends || {};
        for (const [backendName, _cfg] of Object.entries(cliBackends)) {
          // For custom CLI backends, add their known models
          if (backendName === "claude-cli-glm") {
            available.push({ provider: backendName, modelId: "glm-5-turbo", name: "CC GLM-5-Turbo", reasoning: false });
          }
        }
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
            const monDir = "/home/rooot/.openclaw/workspace-mag1/monitor";
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
  // Source of truth: gem-registry.json (manageable gems with local port + cmd + cwd).
  if (url.pathname === "/api/services" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    let services = [];
    try {
      const reg = JSON.parse(fs.readFileSync(GEM_REGISTRY_FILE, "utf8"));
      services = Object.entries(reg.gems || {})
        .filter(([, g]) => g.manageable && g.port && g.cmd && g.cwd)
        .map(([id, g]) => ({ id, name: id, displayName: g.name || id, port: g.port, cmd: g.cmd, cwd: g.cwd }));
    } catch (e) {
      // Fall through with empty list — frontend handles it.
    }
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
    // Source of truth: gem-registry.json (same list as /api/services).
    let svc = null;
    try {
      const reg = JSON.parse(fs.readFileSync(GEM_REGISTRY_FILE, "utf8"));
      const g = (reg.gems || {})[id];
      if (g && g.manageable && g.port && g.cmd && g.cwd) {
        svc = { port: g.port, cmd: g.cmd, cwd: g.cwd };
      }
    } catch {}
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

  // Skill category directories (maps to armory slot types)
  const SKILL_CATEGORIES = ["helm", "armor", "accessory", "utility", "research", "boots", "scheduled"];

  // Scan all skill.json files from disk to build unified registry
  let _skillCache = null;
  function scanAllSkills(force) {
    if (_skillCache && !force) return _skillCache;

    const config = readArmoryConfig();
    const skills = {};
    const baseLayer = [];

    // 1. Scan universal skills: workspace/skills/{category}/*/skill.json
    const universalDir = path.join(OPENCLAW_DIR, "workspace", "skills");
    for (const cat of SKILL_CATEGORIES) {
      const catDir = path.join(universalDir, cat);
      try {
        for (const name of fs.readdirSync(catDir)) {
          const jsonPath = path.join(catDir, name, "skill.json");
          try {
            const meta = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
            skills[name] = { ...meta, source: "universal", id: name, _category: cat };
            if (meta.infrastructure) baseLayer.push(name);
          } catch {}
        }
      } catch {}
    }
    // Also scan top-level for any uncategorized skills (backward compat)
    try {
      for (const name of fs.readdirSync(universalDir)) {
        if (SKILL_CATEGORIES.includes(name) || skills[name]) continue;
        const jsonPath = path.join(universalDir, name, "skill.json");
        try {
          const meta = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
          skills[name] = { ...meta, source: "universal", id: name, _category: null };
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

  // Resolve universal skill directory path (handles categorized layout)
  function resolveSkillDir(skillId) {
    const universalDir = path.join(OPENCLAW_DIR, "workspace", "skills");
    // Check registry first
    const registry = scanAllSkills();
    const skill = registry.skills[skillId];
    if (skill && skill._category) return path.join(universalDir, skill._category, skillId);
    // Fallback: scan category dirs
    for (const cat of SKILL_CATEGORIES) {
      const dir = path.join(universalDir, cat, skillId);
      if (fs.existsSync(dir)) return dir;
    }
    // Last fallback: top-level (uncategorized)
    return path.join(universalDir, skillId);
  }

  // Resolve symlink relative path for bot → skill
  function resolveSkillSymlink(skillId) {
    const registry = scanAllSkills();
    const skill = registry.skills[skillId];
    if (skill && skill._category) return `../../workspace/skills/${skill._category}/${skillId}`;
    // Fallback: scan category dirs
    const universalDir = path.join(OPENCLAW_DIR, "workspace", "skills");
    for (const cat of SKILL_CATEGORIES) {
      if (fs.existsSync(path.join(universalDir, cat, skillId))) return `../../workspace/skills/${cat}/${skillId}`;
    }
    return `../../workspace/skills/${skillId}`;
  }


  // Minimum slots per type (at least 1 each for base structure)
  const MIN_SLOTS = { "helm": 1, "armor": 1, "accessory": 2, "utility": 1, "research": 1, "boots": 1 };

  function makeEmptySlots(scheduledCount = 0, existingSlots = {}, isCoder = false) {
    const slots = {};
    // Count existing slots per type
    const typeCounts = {};
    for (const key of Object.keys(existingSlots)) {
      const type = key.replace(/-\d+$/, "");
      const num = parseInt(key.split("-").pop());
      typeCounts[type] = Math.max(typeCounts[type] || 0, num);
    }
    // Coder profession: all expandable slots unlimited (99)
    const CODER_SLOTS = { "helm": 99, "armor": 99, "accessory": 99, "utility": 99, "research": 99, "boots": 99 };
    const minSlots = isCoder ? CODER_SLOTS : MIN_SLOTS;
    // Create slots: max of minSlots and existing count
    for (const [type, min] of Object.entries(minSlots)) {
      const count = Math.max(min, typeCounts[type] || 0);
      for (let i = 1; i <= count; i++) slots[`${type}-${i}`] = null;
    }
    // Scheduled slots
    const schedMax = Math.max(scheduledCount, typeCounts["scheduled"] || 0);
    for (let i = 1; i <= schedMax; i++) slots[`scheduled-${i}`] = null;
    return slots;
  }

  // Find or create next available slot of a given type for a bot
  function nextSlotId(type, botSlots) {
    let i = 1;
    while (botSlots[`${type}-${i}`] !== undefined && botSlots[`${type}-${i}`] !== null) i++;
    return `${type}-${i}`;
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
      if (slotId.startsWith("scheduled-")) continue; // scheduled skills managed via cron
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
      // Ordered display — slim index, bot reads SKILL.md on demand
      const order = ["armor", "accessory", "utility", "research", "boots"]; // helm injected via updateSoulRole into SOUL.md
      for (const type of order) {
        const g = groups[type];
        if (!g) continue;
        md += `## ${g.typeName}\n\n`;
        for (const item of g.items) {
          const s = item.skill;
          md += `- ${s.name}（${item.skillId}） — \`skills/${item.skillId}/SKILL.md\`\n`;
        }
        md += `\n`;
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

    let roleContent = "";
    if (helmSkill) {
      const skillMdPath = path.join(OPENCLAW_DIR, botWorkspaceDir(botId), "skills", helmSkillId, "SKILL.md");
      try { roleContent = fs.readFileSync(skillMdPath, "utf8").trim(); } catch { roleContent = `> **工种：${helmSkill.name}** — ${helmSkill.desc}`; }
    }
    const roleBlock = helmSkill
      ? `<!-- ROLE:START -->\n${roleContent}\n<!-- ROLE:END -->`
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

        // Determine scheduled slot count from existing helm/armor
        const prevHelm = existing.bots?.[botId]?.slots?.["helm-1"];
        const prevArmor = existing.bots?.[botId]?.slots?.["armor-1"];
        const isCoder = prevArmor === "coder";
        const schedCount = (prevHelm === "management" || isCoder) ? 99 : 6;

        // Start from existing slots, keep valid ones
        const prev = existing.bots?.[botId]?.slots || {};
        const slots = {};
        const alreadyPlaced = new Set();
        for (const [slotKey, skillId] of Object.entries(prev)) {
          if (skillId && equippable.has(skillId)) {
            const skill = registry.skills[skillId];
            const slotType = slotKey.replace(/-\d+$/, "");
            if (skill && skill.slot === slotType) {
              slots[slotKey] = skillId;
              alreadyPlaced.add(skillId);
            }
          }
        }

        // Also migrate overflow skills into proper slots
        const prevOverflow = existing.bots?.[botId]?.overflow || [];
        for (const skillId of prevOverflow) {
          if (alreadyPlaced.has(skillId) || !equippable.has(skillId)) continue;
          const skill = registry.skills[skillId];
          if (!skill || !skill.slot) continue;
          const slotId = nextSlotId(skill.slot, slots);
          slots[slotId] = skillId;
          alreadyPlaced.add(skillId);
        }

        // Place new skills (on disk but not yet equipped) — no overflow, always create slot
        for (const skillId of equippable) {
          if (alreadyPlaced.has(skillId)) continue;
          const skill = registry.skills[skillId];
          if (!skill || !skill.slot) continue;
          const slotId = nextSlotId(skill.slot, slots);
          slots[slotId] = skillId;
        }

        // Ensure minimum empty slots exist
        const finalSlots = makeEmptySlots(schedCount, slots, isCoder);
        for (const [k, v] of Object.entries(slots)) finalSlots[k] = v;

        equipment.bots[botId] = { slots: finalSlots };
      }
      writeBotEquipment(equipment);
      syncScheduledSlots();
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
    const { botId, slot, skillId, password } = body;
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      const registry = scanAllSkills();
      if (!getAllBots().includes(botId)) throw new Error("Invalid botId");
      const skill = registry.skills[skillId];
      if (!skill) throw new Error("Unknown skill: " + skillId);
      if (skill.infrastructure) throw new Error("Cannot equip infrastructure skill");
      // Validate slot type
      const slotType = slot.replace(/-\d+$/, "");
      // Helm changes require admin password
      if (slotType === "helm") {
        if (password !== ADMIN_PASSWORD) throw new Error("工种变更需要管理员密码");
      }
      if (skill.slot !== slotType) throw new Error(`Skill type "${skill.slot}" cannot go in "${slotType}" slot`);
      // Block: scheduled skills can only go in scheduled slots
      if (skill.slot === "scheduled" && slotType !== "scheduled") throw new Error("定时任务技能只能装备到定时插槽");
      if (slotType === "scheduled" && skill.slot !== "scheduled") throw new Error("定时插槽只能装备定时任务技能");
      // Permission: research slots require frontline helm (unless coder profession)
      if (slotType === "research") {
        const curEquip = readBotEquipment();
        const helmSkill = curEquip.bots?.[botId]?.slots?.["helm-1"];
        const armorSkill = curEquip.bots?.[botId]?.slots?.["armor-1"];
        if (helmSkill !== "frontline" && armorSkill !== "coder") throw new Error("研究插槽需要装备「前台」工种或「coder」职业才能解锁");
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
      // Validate slot type matches skill type (no fixed count limit)
      if (!slot.startsWith(slotType + "-")) throw new Error("Invalid slot: " + slot);

      const equipment = readBotEquipment();
      if (!equipment.bots[botId]) equipment.bots[botId] = { slots: {} };

      // Single-slot types: helm, armor, boots can only have 1 skill (coder unlocks helm & boots)
      const armorSkill = equipment.bots[botId]?.slots?.["armor-1"];
      const singleSlotTypes = new Set(armorSkill === "coder" ? [] : ["helm", "armor", "boots"]);
      if (singleSlotTypes.has(slotType)) {
        for (const [s, v] of Object.entries(equipment.bots[botId].slots)) {
          if (v && s.startsWith(slotType + "-") && s !== slot) {
            equipment.bots[botId].slots[s] = null;
          }
        }
      }

      // Accessory subType exclusivity: only 1 content style + 1 image style
      if (slotType === "accessory" && skill.subType) {
        for (const [s, v] of Object.entries(equipment.bots[botId].slots)) {
          if (!v || !s.startsWith("accessory-") || s === slot) continue;
          const existSkill = registry.skills[v];
          if (existSkill && existSkill.subType === skill.subType) {
            equipment.bots[botId].slots[s] = null; // replace same subType
          }
        }
      }

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
          fs.symlinkSync(resolveSkillSymlink(skillId), targetPath);
        } else if (skill.owner !== botId) {
          const absSource = path.join(OPENCLAW_DIR, botWorkspaceDir(skill.owner), "skills", skillId);
          fs.symlinkSync(absSource, targetPath);
        }
      }

      equipment.bots[botId].slots[slot] = skillId;
      // DEBUG: check if coder survived
      const debugArmors = Object.entries(equipment.bots[botId].slots).filter(([k,v]) => k.startsWith("armor-") && v);
      console.log(`[DEBUG equip] armor slots before write:`, JSON.stringify(debugArmors));
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
      // Try universal skill first (categorized), then bot-specific
      let filePath = path.join(resolveSkillDir(skillId), file);
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

  // GET /api/contact-book — parse contact-book SKILL.md, return groups + users with per-bot open_ids
  if (url.pathname === "/api/contact-book" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      res.end(JSON.stringify(getContactBook()));
    } catch (e) {
      res.end(JSON.stringify({ groups: [], users: [], error: e.message }));
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

  // GET /api/bot/file?botId=xxx&file=AGENTS.md — read a bot workspace file
  if (url.pathname === "/api/bot/file" && req.method === "GET") {
    const botId = url.searchParams.get("botId");
    const file = url.searchParams.get("file");
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    if (!botId || !getAllBots().includes(botId) || !file) { res.end(JSON.stringify({ error: "Invalid params" })); return; }
    // Only allow .md files in bot workspace root
    if (!file.endsWith(".md") || file.includes("/") || file.includes("..")) { res.end(JSON.stringify({ error: "Not allowed" })); return; }
    try {
      const filePath = path.join(OPENCLAW_DIR, botWorkspaceDir(botId), file);
      if (!fs.existsSync(filePath)) { res.end(JSON.stringify({ error: "File not found" })); return; }
      const content = fs.readFileSync(filePath, "utf8");
      res.end(JSON.stringify({ botId, file, content }));
    } catch (e) { res.end(JSON.stringify({ error: e.message })); }
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
      if (special?.multi && special.entries) {
        const expectedKeys = Object.keys(special.entries);
        const found = expectedKeys.filter(k => mcporter.mcpServers[k]);
        bindings[gemId] = { socketed: found.length > 0, entries: found.length, expectedEntries: expectedKeys.length };
      } else if (special?.multi && !special.entries) {
        // multi without entries (urlTemplate mode) — check if gem key exists in mcporter
        const entry = mcporter.mcpServers[gemId];
        bindings[gemId] = { socketed: !!entry, url: entry?.url || entry?.baseUrl || null };
      } else {
        const key = gem.mcporterKey || gemId;
        const entry = mcporter.mcpServers[key];
        bindings[gemId] = { socketed: !!entry, url: entry?.url || entry?.baseUrl || entry?.command || null };
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

  // POST /api/xhs-live/:botId — launch headed Chrome on VNC for live viewing
  const xhsLiveMatch = url.pathname.match(/^\/api\/xhs-live\/([^/]+)$/);
  if (xhsLiveMatch && req.method === "POST") {
    const botId = xhsLiveMatch[1];
    if (!/^bot\d+$/.test(botId)) {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid bot id" }));
      return;
    }
    try {
      const pid = startXhsLive(botId);
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: true, botId, pid }));
    } catch (e) {
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // DELETE /api/xhs-live — kill headed Chrome
  if (url.pathname === "/api/xhs-live" && req.method === "DELETE") {
    killXhsLive();
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  // GET /api/xhs-live — current live view status
  if (url.pathname === "/api/xhs-live" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({
      active: !!xhsLiveProc,
      botId: xhsLiveProc?.botId || null,
      pid: xhsLiveProc?.proc?.pid || null,
    }));
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
        } else if (gem.command) {
          // stdio-based MCP — check if process is running
          checks.push(new Promise(resolve => {
            try {
              const pids = execSync(`pgrep -f "${path.basename(gem.command)}" 2>/dev/null`, { encoding: "utf8", timeout: 3000 }).trim();
              health[gemId] = { status: pids ? "up" : "down", pid: pids.split('\n')[0] || null };
            } catch {
              // pgrep exits 1 when no match — that's "not running but available on demand"
              health[gemId] = { status: "standby", pid: null };
            }
            resolve();
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
      if (special?.multi && special.entries) {
        for (const [key, url] of Object.entries(special.entries)) {
          mcporter.mcpServers[key] = { url };
        }
      } else if (gem.command) {
        // stdio-based MCP (e.g. openspace) — use command instead of url
        const key = gem.mcporterKey || gemId;
        mcporter.mcpServers[key] = { command: gem.command };
      } else {
        const url = resolveGemUrl(gemId, botId, registry);
        if (!url) throw new Error(`Cannot resolve URL for ${gemId} on ${botId}`);
        const urlKey = special?.urlKey || "url";
        mcporter.mcpServers[gemId] = { [urlKey]: url };
      }
      if (!mcporter.imports) mcporter.imports = [];
      writeMcporter(botId, mcporter);
      // xiaohongshu-mcp 需要独立的 Chrome profile 目录，避免和 openclaw browser 冲突
      if (gemId === "xiaohongshu-mcp") {
        const profileDir = path.join(XHS_PROFILES_DIR, botId);
        if (!fs.existsSync(profileDir)) {
          fs.mkdirSync(profileDir, { recursive: true });
          console.log(`📁 Auto-created xhs-profiles dir: ${profileDir}`);
        }
      }
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
      if (special?.multi && special.entries) {
        for (const key of Object.keys(special.entries)) {
          delete mcporter.mcpServers[key];
        }
      } else {
        const key = gem.mcporterKey || gemId;
        delete mcporter.mcpServers[key];
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

  // Sync cron jobs → bot-equipment.json scheduled slots
  function syncScheduledSlots() {
    try {
      const cronData = readCronJobs();
      const equipment = readBotEquipment();
      // Group jobs by agentId
      const jobsByAgent = {};
      for (const job of cronData.jobs) {
        if (!job.agentId) continue;
        if (!jobsByAgent[job.agentId]) jobsByAgent[job.agentId] = [];
        jobsByAgent[job.agentId].push(job);
      }
      // Update each bot's scheduled slots
      for (const botId of getAllBots()) {
        if (!equipment.bots[botId]) continue;
        const slots = equipment.bots[botId].slots || {};
        // Clear existing scheduled slots
        for (const k of Object.keys(slots)) {
          if (k.startsWith("scheduled-")) slots[k] = null;
        }
        // Fill from cron jobs — resolve skillId from multiple sources
        const jobs = jobsByAgent[botId] || [];
        let idx = 1;
        for (const job of jobs) {
          let sid = job.skillId;
          // Try extracting from payload: "Read skills/xxx/SKILL.md"
          if (!sid) {
            const m = job.payload?.message?.match(/skills\/([^/]+)\/SKILL\.md/);
            if (m) sid = m[1];
          }
          // Try stripping agentId- prefix from job name
          if (!sid && job.name?.startsWith(botId + "-")) {
            sid = job.name.slice(botId.length + 1);
          }
          // Fall back to job name
          if (!sid) sid = job.name;
          slots[`scheduled-${idx}`] = sid || null;
          idx++;
        }
        // Ensure minimum 6 scheduled slots
        const maxSched = Math.max(6, idx - 1);
        for (let i = idx; i <= maxSched; i++) {
          if (slots[`scheduled-${i}`] === undefined) slots[`scheduled-${i}`] = null;
        }
      }
      writeBotEquipment(equipment);
    } catch (e) {
      console.error("syncScheduledSlots error:", e.message);
    }
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
      syncScheduledSlots();
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
      syncScheduledSlots();
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
    const { agentId, skillId, prompt, jobName: customName, cronExpr, startDate, endDate, deliveryChannel, deliveryTo } = body;
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      if (!agentId || (!skillId && !prompt) || !cronExpr) throw new Error("agentId, skillId or prompt, cronExpr required");
      if (!getAllBots().includes(agentId)) throw new Error("Invalid agentId");

      let skill = null;
      if (skillId) {
        const registry = scanAllSkills();
        skill = registry.skills[skillId];
        if (!skill) throw new Error("Unknown skill: " + skillId);
      }

      const crypto = require("crypto");
      const jobId = crypto.randomUUID();
      const now = Date.now();

      const jobName = customName || (skillId ? `${agentId}-${skillId}` : `${agentId}-prompt`);
      const jobDesc = skillId ? `定时执行 ${skill.name || skillId}` : `自定义指令: ${prompt.slice(0, 50)}`;
      let jobMessage = skillId
        ? `Read skills/${skillId}/SKILL.md 加载完整流程，然后按流程执行。`
        : prompt;

      // 投递目标追加到 prompt，让 agent 直接用 message 工具发送
      if (deliveryChannel && deliveryTo) {
        const target = deliveryTo.startsWith("chat:") ? deliveryTo.slice(5) : deliveryTo;
        jobMessage += `\n\n完成后用 message 工具投递结果到飞书：\n- channel: feishu\n- to: ${target}\n- account: ${agentId}`;
      }

      const job = {
        id: jobId,
        agentId,
        name: jobName,
        description: jobDesc,
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
          message: jobMessage
        },
        delivery: { mode: "none" },
        state: { consecutiveErrors: 0 }
      };

      if (startDate) job.startDate = startDate;
      if (endDate) job.endDate = endDate;

      // Ensure the skill is symlinked into the bot's workspace
      if (skillId && skill) {
        const skillTarget = path.join(OPENCLAW_DIR, botWorkspaceDir(agentId), "skills", skillId);
        try { fs.lstatSync(skillTarget); } catch {
          const skillsDir = path.join(OPENCLAW_DIR, botWorkspaceDir(agentId), "skills");
          try { fs.mkdirSync(skillsDir, { recursive: true }); } catch {}
          if (skill.source === "universal") {
            fs.symlinkSync(resolveSkillSymlink(skillId), skillTarget);
          } else if (skill.owner !== agentId) {
            const absSource = path.join(OPENCLAW_DIR, botWorkspaceDir(skill.owner), "skills", skillId);
            fs.symlinkSync(absSource, skillTarget);
          }
        }
      }

      const data = readCronJobs();
      data.jobs.push(job);
      writeCronJobs(data);
      syncScheduledSlots();
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
      syncScheduledSlots();
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

  // POST /api/agent/color — change agent color
  if (url.pathname === "/api/agent/color" && req.method === "POST") {
    const body = await new Promise(resolve => {
      let d = ""; req.on("data", c => d += c);
      req.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve({}); } });
    });
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      const { botId, color } = body;
      if (!botId || !color) throw new Error("botId and color required");
      let colors = {};
      try { colors = JSON.parse(fs.readFileSync(BOT_COLORS_FILE, "utf8")); } catch {}
      colors[botId] = color;
      fs.writeFileSync(BOT_COLORS_FILE, JSON.stringify(colors, null, 2));
      cachedData = null;
      res.end(JSON.stringify({ status: "ok", botId, color }));
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
      const defaultSkills = ["frontline", "xhs-op", "browser-base", "report-incident", "research-mcp"];
      for (const skill of defaultSkills) {
        const skillDir = resolveSkillDir(skill);
        const link = path.join(wsDir, "skills", skill);
        if (fs.existsSync(skillDir) && !fs.existsSync(link)) {
          fs.symlinkSync(resolveSkillSymlink(skill), link);
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
    const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
    sendCompressed(req, res, 200, { "Content-Type": "text/html; charset=utf-8" }, html);
    return;
  }

  if (url.pathname === "/portfolio") {
    const html = fs.readFileSync(path.join(__dirname, "portfolio.html"), "utf8");
    sendCompressed(req, res, 200, { "Content-Type": "text/html; charset=utf-8" }, html);
    return;
  }

  if (url.pathname === "/api/portfolio/summary" && req.method === "GET") {
    try {
      const py = `
import sqlite3, json
conn = sqlite3.connect('/home/rooot/.openclaw/data/tougu.db')
conn.row_factory = sqlite3.Row
accounts = conn.execute('SELECT * FROM bot_accounts').fetchall()
result = []
for a in accounts:
    bot_id = a['bot_id']
    holdings = conn.execute(
        "SELECT h.product_id, h.amount_invested, h.market_value, h.weight, h.role, "
        "h.unrealized_pnl, h.unrealized_pnl_pct, h.latest_nav, h.entry_nav, "
        "i.strategy_name "
        "FROM bot_holdings h LEFT JOIN tougu_info i ON h.product_id = i.strategy_id "
        "WHERE h.bot_id = ? AND h.status = 'active' ORDER BY h.market_value DESC",
        (bot_id,)
    ).fetchall()
    snap = conn.execute(
        "SELECT * FROM bot_daily_snapshots WHERE bot_id = ? ORDER BY trade_date DESC LIMIT 1",
        (bot_id,)
    ).fetchone()
    result.append({
        'bot_id': bot_id,
        'initial_capital': a['initial_capital'],
        'cash': a['cash'],
        'total_value': snap['total_value'] if snap else a['initial_capital'],
        'net_value': snap['net_value'] if snap else 1.0,
        'cumulative_return_pct': snap['cumulative_return_pct'] if snap else 0,
        'daily_return_pct': snap['daily_return_pct'] if snap else 0,
        'max_drawdown': snap['max_drawdown'] if snap else 0,
        'trade_date': snap['trade_date'] if snap else None,
        'holdings': [{'product_id': h['product_id'], 'product_name': h['strategy_name'] or h['product_id'],
                       'amount': h['amount_invested'], 'market_value': h['market_value'],
                       'weight': h['weight'], 'role': h['role'],
                       'pnl': h['unrealized_pnl'], 'pnl_pct': h['unrealized_pnl_pct']}
                      for h in holdings]
    })
conn.close()
print(json.dumps(result, ensure_ascii=False))
`;
      const out = execSync(`python3 -c ${JSON.stringify(py)}`, { timeout: 5000, encoding: "utf8" });
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(out.trim());
    } catch (e) {
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // --- Avatar API ---
  const IMG_EXTS = [".png", ".jpg", ".jpeg", ".webp"];
  const MIME_MAP = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp" };

  // Batch endpoint: all avatar thumbnails in one call
  if (url.pathname === "/api/bot/avatars" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "max-age=60" });
    res.end(JSON.stringify(avatarCache));
    return;
  }

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
    const stat = fs.statSync(found);
    const etag = `"${stat.mtimeMs.toString(36)}-${stat.size.toString(36)}"`;
    if (req.headers["if-none-match"] === etag) { res.writeHead(304); res.end(); return; }
    res.writeHead(200, { "Content-Type": MIME_MAP[ext] || "application/octet-stream", "Cache-Control": "max-age=86400", "ETag": etag });
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
    req.on("end", async () => {
      try {
        const { path: imgPath } = JSON.parse(body);
        const wsDir = path.join(OPENCLAW_DIR, botWorkspaceDir(botId));
        const src = path.join(wsDir, imgPath);
        if (!fs.existsSync(src)) { res.writeHead(404); res.end("Image not found"); return; }
        if (!fs.realpathSync(src).startsWith(fs.realpathSync(wsDir))) { res.writeHead(403); res.end("Forbidden"); return; }
        const srcSize = fs.statSync(src).size;
        if (srcSize > AVATAR_MAX_SIZE) {
          res.writeHead(413, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: `图片太大 (${(srcSize / 1024 / 1024).toFixed(1)}MB)，上限 ${AVATAR_MAX_SIZE / 1024 / 1024}MB` }));
          return;
        }
        const ext = path.extname(imgPath).toLowerCase();
        for (const e of IMG_EXTS) {
          const old = path.join(wsDir, "avatar" + e);
          if (fs.existsSync(old)) fs.unlinkSync(old);
        }
        const dest = path.join(wsDir, "avatar" + ext);
        fs.copyFileSync(src, dest);
        const thumb = await generateThumbnail(botId);
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true, avatar: "avatar" + ext, thumb }));
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

  // ── Skill Evolution API ──────────────────────────────────────────
  const SKILLS_SANDBOX = path.join(OPENCLAW_DIR, "skills-sandbox");
  const PENDING_APPROVAL_DIR = path.join(SKILLS_SANDBOX, "pending-approval");
  const LIVE_SKILLS_DIR = path.join(OPENCLAW_DIR, "workspace", "skills");

  // GET /api/skill-evolution/pool — list sandbox skills with status
  if (url.pathname === "/api/skill-evolution/pool" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      const items = [];
      for (const name of fs.readdirSync(SKILLS_SANDBOX)) {
        const dir = path.join(SKILLS_SANDBOX, name);
        if (!fs.statSync(dir).isDirectory() || name === "pending-approval") continue;
        const hasUploadMeta = fs.existsSync(path.join(dir, ".upload_meta.json"));
        const hasExclude = fs.existsSync(path.join(dir, ".exclude"));
        const skillMd = path.join(dir, "SKILL.md");
        const sizeKB = fs.existsSync(skillMd) ? Math.round(fs.statSync(skillMd).size / 1024 * 10) / 10 : 0;
        const liveMd = path.join(resolveSkillDir(name), "SKILL.md");
        const liveSizeKB = fs.existsSync(liveMd) ? Math.round(fs.statSync(liveMd).size / 1024 * 10) / 10 : 0;
        const directionFile = path.join(dir, ".direction");
        const direction = fs.existsSync(directionFile) ? fs.readFileSync(directionFile, "utf-8").trim() : "";
        items.push({
          name,
          status: hasExclude ? "excluded" : hasUploadMeta ? "evolved" : "candidate",
          sizeKB,
          liveSizeKB,
          direction,
        });
      }
      res.end(JSON.stringify({ items }));
    } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    return;
  }

  // POST /api/skill-evolution/pool/exclude/:name
  if (url.pathname.startsWith("/api/skill-evolution/pool/exclude/") && req.method === "POST") {
    const name = url.pathname.split("/").pop();
    const dir = path.join(SKILLS_SANDBOX, name);
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    if (!fs.existsSync(dir)) { res.end(JSON.stringify({ error: "not found" })); return; }
    fs.writeFileSync(path.join(dir, ".exclude"), "");
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  // GET /api/skill-evolution/pool/content/:name — read skill SKILL.md content
  if (url.pathname.startsWith("/api/skill-evolution/pool/content/") && req.method === "GET") {
    const name = url.pathname.replace("/api/skill-evolution/pool/content/", "");
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    // Read both sandbox and live versions
    const sandboxMd = path.join(SKILLS_SANDBOX, name, "SKILL.md");
    const liveSkillDir = resolveSkillDir(name);
    const liveMd = path.join(liveSkillDir, "SKILL.md");
    try {
      const sandbox = fs.existsSync(sandboxMd) ? fs.readFileSync(sandboxMd, "utf-8") : "";
      const live = fs.existsSync(liveMd) ? fs.readFileSync(liveMd, "utf-8") : "";
      // List all files in the skill directory
      const sandboxDir = path.join(SKILLS_SANDBOX, name);
      const liveDir = liveSkillDir;
      const sandboxFiles = fs.existsSync(sandboxDir) ? fs.readdirSync(sandboxDir).filter(f => !f.startsWith(".")) : [];
      const liveFiles = fs.existsSync(liveDir) ? fs.readdirSync(liveDir).filter(f => !f.startsWith(".")) : [];
      res.end(JSON.stringify({ name, sandbox, live, sandboxFiles, liveFiles }));
    } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    return;
  }

  // POST /api/xhs-stats/refresh — trigger collect-xhs-stats.js immediately
  if (url.pathname === "/api/xhs-stats/refresh" && req.method === "POST") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    const script = path.join(__dirname, "collect-xhs-stats.js");
    const logFile = fs.openSync("/tmp/xhs-stats-refresh.log", "a");
    const child = spawn("node", [script], { stdio: ["ignore", logFile, logFile], detached: true });
    child.unref();
    child.on("close", (code) => {
      fs.closeSync(logFile);
      console.log(`[xhs-stats] collect finished with code ${code}`);
      // Only invalidate cache AFTER collection finishes, so the next request
      // rebuilds with fresh data. Don't clear before — that forces an immediate
      // rebuild while redis is still busy with the collector, causing execSync hangs.
      cachedData = null; cacheTime = 0;
    });
    res.end(JSON.stringify({ ok: true, message: "已触发 XHS 数据刷新" }));
    return;
  }

  // GET /api/xhs-stats/export — export published records as Excel
  if (url.pathname === "/api/xhs-stats/export" && req.method === "GET") {
    const start = url.searchParams.get("start") || "";
    const end = url.searchParams.get("end") || "";
    const xhsStats = getXhsStats();
    const pq = getPublishQueue();
    if (xhsStats) pq.published = matchXhsMetrics(pq.published, xhsStats);
    let items = pq.published || [];
    if (start || end) {
      items = items.filter(item => {
        const dateMatch = (item.name || "").match(/^(\d{4}-\d{2}-\d{2})/);
        if (!dateMatch) return false;
        const d = dateMatch[1];
        if (start && d < start) return false;
        if (end && d > end) return false;
        return true;
      });
    }
    try {
      const wb = new ExcelJS.Workbook();
      const ws = wb.addWorksheet("发布记录");
      const columns = [
        { header: "账号", key: "bot", width: 12 },
        { header: "状态", key: "status", width: 8 },
        { header: "发布时间", key: "date", width: 18 },
        { header: "标题", key: "title", width: 36 },
        { header: "曝光", key: "impressions", width: 10 },
        { header: "浏览", key: "views", width: 10 },
        { header: "封面点击率", key: "click_rate", width: 12 },
        { header: "点赞", key: "likes", width: 8 },
        { header: "评论", key: "comments", width: 8 },
        { header: "收藏", key: "favorites", width: 8 },
        { header: "涨粉", key: "new_followers", width: 8 },
        { header: "分享", key: "shares", width: 8 },
        { header: "人均观看时长", key: "avg_watch_time", width: 14 },
        { header: "弹幕", key: "danmaku", width: 8 },
      ];
      ws.columns = columns;
      // Style header row
      ws.getRow(1).font = { bold: true };
      ws.getRow(1).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF1a1a2e" } };
      ws.getRow(1).font = { bold: true, color: { argb: "FFFECA57" } };
      for (const item of items) {
        const f = item.name || "";
        const botMatch = f.match(/_(\w+?)_/) || f.match(/-(bot\d+)-/);
        const bot = botMatch ? botMatch[1] : "?";
        const ls = xhsStats ? (xhsStats.bots?.[bot]?.loginStatus) : null;
        const status = ls ? (ls.creator ? "已登录" : "未登录") : "-";
        const dateMatch = f.match(/^(\d{4}-\d{2}-\d{2}T\d{2}-\d{2})/);
        const date = dateMatch ? dateMatch[1].replace("T", " ") : (item.metrics?.publish_time || "");
        const m = item.metrics || {};
        ws.addRow({
          bot, status, date,
          title: item.title || f,
          impressions: m.impressions || "-",
          views: m.views || "-",
          click_rate: m.click_rate || "-",
          likes: m.likes || "-",
          comments: m.comments || "-",
          favorites: m.favorites || "-",
          new_followers: m.new_followers || "-",
          shares: m.shares || "-",
          avg_watch_time: m.avg_watch_time || "-",
          danmaku: m.danmaku || "-",
        });
      }
      const dateStr = new Date().toISOString().slice(0, 10);
      res.writeHead(200, {
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Disposition": `attachment; filename=xhs-publish-records-${dateStr}.xlsx`,
        "Access-Control-Allow-Origin": "*"
      });
      wb.xlsx.write(res).then(() => res.end());
    } catch (e) {
      res.writeHead(500, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // POST /api/skill-evolution/trigger — trigger sys2 to run evolution in a fresh session
  if (url.pathname === "/api/skill-evolution/trigger" && req.method === "POST") {
    let body = "";
    req.on("data", c => body += c);
    req.on("end", async () => {
      let skills = [];
      try { skills = JSON.parse(body).skills || []; } catch {}

      // Only remove lock files (not session files) — avoids destroying active sessions
      const sys2Sessions = path.join(AGENTS_DIR, "sys2", "sessions");
      try {
        const files = await fs.promises.readdir(sys2Sessions);
        await Promise.all(files.filter(f => f.endsWith(".lock")).map(f =>
          fs.promises.unlink(path.join(sys2Sessions, f)).catch(() => {})
        ));
      } catch {}

      // If specific skills selected, pause other .direction files (async)
      const SKILLS_SANDBOX = path.join(OPENCLAW_DIR, "skills-sandbox");
      const pausedDirs = [];
      if (skills.length) {
        try {
          const dirs = await fs.promises.readdir(SKILLS_SANDBOX);
          for (const name of dirs) {
            if (skills.includes(name)) continue;
            const dirFile = path.join(SKILLS_SANDBOX, name, ".direction");
            try {
              await fs.promises.access(dirFile);
              await fs.promises.rename(dirFile, dirFile + ".paused");
              pausedDirs.push(dirFile);
            } catch {}
          }
        } catch (e) { console.error("[skill-evo] pause error:", e.message); }
      }

      const prompt = "跑一遍技能进化";
      runAgent(["agent", "--agent=sys2", "-m", prompt], 600000)
        .then(r => console.log("[skill-evo] trigger done:", r.error || "ok"))
        .catch(e => console.error("[skill-evo] trigger error:", e))
        .finally(async () => {
          for (const f of pausedDirs) {
            try { await fs.promises.rename(f + ".paused", f); } catch {}
          }
        });

      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      res.end(JSON.stringify({ ok: true, message: `已触发 sys2 进化任务${skills.length ? '（' + skills.join('、') + '）' : ''}` }));
    });
    return;
  }

  // POST /api/skill-evolution/pool/direction/:name — set custom evolution direction
  if (url.pathname.startsWith("/api/skill-evolution/pool/direction/") && req.method === "POST") {
    const name = url.pathname.replace("/api/skill-evolution/pool/direction/", "");
    const dir = path.join(SKILLS_SANDBOX, name);
    let body = "";
    req.on("data", c => body += c);
    req.on("end", () => {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      if (!fs.existsSync(dir)) { res.end(JSON.stringify({ error: "not found" })); return; }
      try {
        const { direction } = JSON.parse(body || "{}");
        const df = path.join(dir, ".direction");
        if (direction && direction.trim()) {
          fs.writeFileSync(df, direction.trim());
        } else {
          if (fs.existsSync(df)) fs.unlinkSync(df);
        }
        res.end(JSON.stringify({ ok: true }));
      } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    });
    return;
  }

  // POST /api/skill-evolution/pool/delete/:name — permanently remove from sandbox
  if (url.pathname.startsWith("/api/skill-evolution/pool/delete/") && req.method === "POST") {
    const name = url.pathname.replace("/api/skill-evolution/pool/delete/", "");
    const dir = path.join(SKILLS_SANDBOX, name);
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    if (!fs.existsSync(dir)) { res.end(JSON.stringify({ error: "not found" })); return; }
    fs.rmSync(dir, { recursive: true, force: true });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  // POST /api/skill-evolution/pool/reset/:name — clear evolved markers, restore from live
  if (url.pathname.startsWith("/api/skill-evolution/pool/reset/") && req.method === "POST") {
    const name = url.pathname.split("/").pop();
    const sandboxDir = path.join(SKILLS_SANDBOX, name);
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    if (!fs.existsSync(sandboxDir)) { res.end(JSON.stringify({ error: "not found" })); return; }
    // Remove evolution markers
    for (const marker of [".upload_meta.json", "DIFF.patch", ".skill_id"]) {
      const p = path.join(sandboxDir, marker);
      if (fs.existsSync(p)) fs.unlinkSync(p);
    }
    // Restore .md files from live
    const liveDir = resolveSkillDir(name);
    if (fs.existsSync(liveDir)) {
      for (const f of fs.readdirSync(liveDir)) {
        if (f.endsWith(".md")) {
          fs.copyFileSync(path.join(liveDir, f), path.join(sandboxDir, f));
        }
      }
    }
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  // POST /api/skill-evolution/pool/include/:name
  if (url.pathname.startsWith("/api/skill-evolution/pool/include/") && req.method === "POST") {
    const name = url.pathname.split("/").pop();
    const excl = path.join(SKILLS_SANDBOX, name, ".exclude");
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    if (fs.existsSync(excl)) fs.unlinkSync(excl);
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  // GET /api/skill-evolution/pending — list pending approvals
  if (url.pathname === "/api/skill-evolution/pending" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    try {
      const items = [];
      if (fs.existsSync(PENDING_APPROVAL_DIR)) {
        for (const name of fs.readdirSync(PENDING_APPROVAL_DIR)) {
          const dir = path.join(PENDING_APPROVAL_DIR, name);
          if (!fs.statSync(dir).isDirectory()) continue;
          const pf = path.join(dir, "proposal.json");
          if (fs.existsSync(pf)) {
            const proposal = JSON.parse(fs.readFileSync(pf, "utf-8"));
            if (proposal.status === "pending") items.push(proposal);
          } else {
            // No proposal.json — construct from DIFF.patch + SKILL.md
            const diffPath = path.join(dir, "DIFF.patch");
            const skillPath = path.join(dir, "SKILL.md");
            const hasDiff = fs.existsSync(diffPath);
            const hasSkill = fs.existsSync(skillPath);
            if (!hasDiff && !hasSkill) continue;
            const liveSkillPath = path.join(resolveSkillDir(name), "SKILL.md");
            const beforeKB = fs.existsSync(liveSkillPath) ? (fs.statSync(liveSkillPath).size / 1024).toFixed(1) : "?";
            const afterKB = hasSkill ? (fs.statSync(skillPath).size / 1024).toFixed(1) : "?";
            const diff = hasDiff ? fs.readFileSync(diffPath, "utf-8") : "";
            const addedLines = (diff.match(/^\+[^+]/gm) || []).length;
            const removedLines = (diff.match(/^-[^-]/gm) || []).length;
            items.push({
              skillName: name,
              status: "pending",
              createdAt: hasDiff ? fs.statSync(diffPath).mtime.toISOString() : new Date().toISOString(),
              evolution: { changeSummary: `+${addedLines}/-${removedLines} 行变更` },
              size: { before: { skillMdKB: beforeKB }, after: { skillMdKB: afterKB }, tokenDelta: `${beforeKB !== "?" && afterKB !== "?" ? (((afterKB - beforeKB) / beforeKB * 100) | 0) + "%" : "?"}` },
              verification: { result: {} },
              diffStats: { added: addedLines, removed: removedLines }
            });
          }
        }
      }
      items.sort((a, b) => (b.createdAt || "").localeCompare(a.createdAt || ""));
      res.end(JSON.stringify({ items }));
    } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    return;
  }

  // GET /api/skill-evolution/diff/:name — get proposal + diff content
  if (url.pathname.startsWith("/api/skill-evolution/diff/") && req.method === "GET") {
    const name = url.pathname.replace("/api/skill-evolution/diff/", "");
    const dir = path.join(PENDING_APPROVAL_DIR, name);
    res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    if (!fs.existsSync(dir)) { res.end(JSON.stringify({ error: "not found" })); return; }
    try {
      const pf = path.join(dir, "proposal.json");
      const proposal = fs.existsSync(pf) ? JSON.parse(fs.readFileSync(pf, "utf-8")) : { skillName: name, status: "pending" };
      const diffPath = path.join(dir, "DIFF.patch");
      const diff = fs.existsSync(diffPath) ? fs.readFileSync(diffPath, "utf-8") : "";
      res.end(JSON.stringify({ proposal, diff }));
    } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    return;
  }

  // POST /api/skill-evolution/approve/:name
  if (url.pathname.startsWith("/api/skill-evolution/approve/") && req.method === "POST") {
    const name = url.pathname.replace("/api/skill-evolution/approve/", "");
    const dir = path.join(PENDING_APPROVAL_DIR, name);
    let body = "";
    req.on("data", c => body += c);
    req.on("end", () => {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      try {
        const { password } = JSON.parse(body || "{}");
        if (password !== ADMIN_PASSWORD) { res.end(JSON.stringify({ error: "wrong password" })); return; }
        if (!fs.existsSync(dir)) { res.end(JSON.stringify({ error: "not found" })); return; }

        let liveDir = resolveSkillDir(name);

        // Backup current live version before overwriting
        if (fs.existsSync(liveDir)) {
          const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
          const backupDir = path.join(LIVE_SKILLS_DIR, "_backups", `${name}.backup-${ts}`);
          fs.mkdirSync(path.join(LIVE_SKILLS_DIR, "_backups"), { recursive: true });
          fs.cpSync(liveDir, backupDir, { recursive: true });
        } else {
          // New skill: determine category from sandbox skill.json slot field
          const sandboxJson = path.join(SKILLS_SANDBOX, name, "skill.json");
          let cat = "utility";
          try {
            const meta = JSON.parse(fs.readFileSync(sandboxJson, "utf8"));
            if (SKILL_CATEGORIES.includes(meta.slot)) cat = meta.slot;
          } catch {}
          liveDir = path.join(LIVE_SKILLS_DIR, cat, name);
        }

        // Copy .md files to live
        if (!fs.existsSync(liveDir)) fs.mkdirSync(liveDir, { recursive: true });
        for (const f of fs.readdirSync(dir)) {
          if (f.endsWith(".md") && f !== "DIFF.patch") {
            fs.copyFileSync(path.join(dir, f), path.join(liveDir, f));
          }
        }

        // Clean sandbox markers so next sync overwrites sandbox with new live version
        const sandboxDir = path.join(SKILLS_SANDBOX, name);
        for (const marker of [".upload_meta.json", "DIFF.patch"]) {
          const p = path.join(sandboxDir, marker);
          if (fs.existsSync(p)) fs.unlinkSync(p);
        }

        // Update proposal status
        const pf = path.join(dir, "proposal.json");
        const proposal = fs.existsSync(pf) ? JSON.parse(fs.readFileSync(pf, "utf-8")) : { skillName: name, status: "pending" };
        proposal.status = "approved";
        proposal.resolvedAt = new Date().toISOString();
        fs.writeFileSync(pf, JSON.stringify(proposal, null, 2));

        res.end(JSON.stringify({ ok: true, merged: name }));
      } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    });
    return;
  }

  // POST /api/skill-evolution/reject/:name
  if (url.pathname.startsWith("/api/skill-evolution/reject/") && req.method === "POST") {
    const name = url.pathname.replace("/api/skill-evolution/reject/", "");
    const dir = path.join(PENDING_APPROVAL_DIR, name);
    let body = "";
    req.on("data", c => body += c);
    req.on("end", () => {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      try {
        const { password, reason } = JSON.parse(body || "{}");
        if (password !== ADMIN_PASSWORD) { res.end(JSON.stringify({ error: "wrong password" })); return; }
        if (!fs.existsSync(dir)) { res.end(JSON.stringify({ error: "not found" })); return; }

        // Clean sandbox markers and restore sandbox to match live version
        const sandboxDir = path.join(SKILLS_SANDBOX, name);
        for (const marker of [".upload_meta.json", "DIFF.patch"]) {
          const p = path.join(sandboxDir, marker);
          if (fs.existsSync(p)) fs.unlinkSync(p);
        }
        // Overwrite sandbox .md files with live version
        const liveDir = resolveSkillDir(name);
        if (fs.existsSync(liveDir) && fs.existsSync(sandboxDir)) {
          for (const f of fs.readdirSync(liveDir)) {
            if (f.endsWith(".md")) {
              fs.copyFileSync(path.join(liveDir, f), path.join(sandboxDir, f));
            }
          }
        }

        // Update proposal status
        const pf = path.join(dir, "proposal.json");
        const proposal = fs.existsSync(pf) ? JSON.parse(fs.readFileSync(pf, "utf-8")) : { skillName: name, status: "pending" };
        proposal.status = "rejected";
        proposal.resolvedAt = new Date().toISOString();
        proposal.rejectReason = reason || null;
        fs.writeFileSync(pf, JSON.stringify(proposal, null, 2));

        res.end(JSON.stringify({ ok: true, rejected: name }));
      } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    });
    return;
  }

  // === Publish Queue Hold/Review Endpoints ===

  // POST /api/queue/publish-now — skip hold, wake sys1 immediately
  if (url.pathname === "/api/queue/publish-now" && req.method === "POST") {
    let body = "";
    req.on("data", c => body += c);
    req.on("end", () => {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      try {
        const { name } = JSON.parse(body || "{}");
        const dir = path.join(PUBLISH_QUEUE, "pending", name);
        if (!fs.existsSync(dir)) { res.end(JSON.stringify({ error: "not found in pending queue" })); return; }
        const postMd = path.join(dir, "post.md");
        const meta = fs.existsSync(postMd) ? readPostFull(postMd) : null;
        releasedEntries.add(name);
        wakeSys1ForEntry(name, meta);
        cachedData = null; cacheTime = 0;
        res.end(JSON.stringify({ ok: true }));
      } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    });
    return;
  }

  // POST /api/queue/reject — reject post, move to rejected/
  if (url.pathname === "/api/queue/reject" && req.method === "POST") {
    let body = "";
    req.on("data", c => body += c);
    req.on("end", () => {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      try {
        const { name, reason } = JSON.parse(body || "{}");
        const src = path.join(PUBLISH_QUEUE, "pending", name);
        if (!fs.existsSync(src)) { res.end(JSON.stringify({ error: "not found in pending queue (may already be publishing)" })); return; }
        const dst = path.join(PUBLISH_QUEUE, "rejected", name);
        fs.renameSync(src, dst);
        // Append rejection info to post.md
        const postMd = path.join(dst, "post.md");
        if (fs.existsSync(postMd)) {
          const content = fs.readFileSync(postMd, "utf8");
          const extra = `\n\n<!-- REJECTED at ${new Date().toISOString()} | reason: ${reason || "无"} -->`;
          fs.writeFileSync(postMd, content + extra);
        }
        releasedEntries.delete(name);
        cachedData = null; cacheTime = 0;
        res.end(JSON.stringify({ ok: true }));
      } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    });
    return;
  }

  // POST /api/queue/edit — edit pending post content
  if (url.pathname === "/api/queue/edit" && req.method === "POST") {
    let body = "";
    req.on("data", c => body += c);
    req.on("end", () => {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      try {
        const { name, title, content, text_image, desc, tags, visibility } = JSON.parse(body || "{}");
        const dir = path.join(PUBLISH_QUEUE, "pending", name);
        if (!fs.existsSync(dir)) { res.end(JSON.stringify({ error: "not found in pending queue" })); return; }
        const postMd = path.join(dir, "post.md");
        if (!fs.existsSync(postMd)) { res.end(JSON.stringify({ error: "post.md not found" })); return; }
        let raw = fs.readFileSync(postMd, "utf8");
        const meta = readPostFull(postMd) || {};
        const esc = s => (s || "").replace(/"/g, '\\"');
        const updated = [];
        if (title !== undefined) {
          raw = raw.replace(/^title:\s*".*?"$/m, `title: "${esc(title)}"`);
          updated.push("title");
        }
        if (content !== undefined) {
          raw = raw.replace(/^content:\s*"[\s\S]*?"$/m, `content: "${esc(content)}"`);
          if ((meta.content_mode || meta.publish_type) !== "text_to_image") {
            raw = raw.replace(/(^---\n[\s\S]*?\n---\n)[\s\S]*$/, `$1\n${content}\n`);
          }
          updated.push("content");
        }
        if (text_image !== undefined) {
          // Update frontmatter text_image (multiline quoted value)
          raw = raw.replace(/^text_image:\s*"[\s\S]*?"$/m, `text_image: "${esc(text_image)}"`);
          // Also update the body (everything after the closing ---)
          raw = raw.replace(/(^---\n(?:[\s\S]*?\n)?---\n)[\s\S]*$/, `$1\n${text_image}\n`);
          updated.push("text_image");
        }
        if (desc !== undefined) {
          raw = raw.replace(/^desc:\s*".*?"$/m, `desc: "${esc(desc)}"`);
          updated.push("desc");
        }
        if (tags !== undefined) {
          const normalizedTags = tags
            .map(t => String(t || "").trim())
            .map(t => t.replace(/^#+|#+$/g, "").replace(/\[话题\]$/g, "").trim())
            .filter(Boolean);
          const tagsYaml = "[" + normalizedTags.map(t => `"${esc(t)}"`).join(", ") + "]";
          raw = raw.replace(/^tags:\s*\[.*?\]$/m, `tags: ${tagsYaml}`);
          updated.push("tags");
        }
        if (visibility !== undefined) {
          raw = raw.replace(/^visibility:\s*".*?"$/m, `visibility: "${visibility}"`);
          updated.push("visibility");
        }
        fs.writeFileSync(postMd, raw);
        cachedData = null; cacheTime = 0;
        res.end(JSON.stringify({ ok: true, updated }));
      } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    });
    return;
  }

  // GET /api/queue/image — serve images from pending queue folders
  if (url.pathname === "/api/queue/image" && req.method === "GET") {
    const status = url.searchParams.get("status") || "pending";
    const name = url.searchParams.get("name") || "";
    const file = url.searchParams.get("file") || "";
    if (!["pending", "publishing"].includes(status) || !name || !file) {
      res.writeHead(400); res.end("Bad request"); return;
    }
    const imgPath = path.join(PUBLISH_QUEUE, status, name, file);
    try {
      const real = fs.realpathSync(imgPath);
      if (!real.startsWith(fs.realpathSync(PUBLISH_QUEUE))) {
        res.writeHead(403); res.end("Forbidden"); return;
      }
      if (!fs.existsSync(imgPath)) { res.writeHead(404); res.end("Not found"); return; }
      const ext = path.extname(file).toLowerCase();
      const types = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp", ".mp4": "video/mp4" };
      res.writeHead(200, { "Content-Type": types[ext] || "application/octet-stream", "Cache-Control": "no-cache", "Access-Control-Allow-Origin": "*" });
      fs.createReadStream(imgPath).pipe(res);
    } catch { res.writeHead(404); res.end("Not found"); }
    return;
  }

  // GET /api/queue/read-failed — full post metadata for editing
  if (url.pathname === "/api/queue/read-failed" && req.method === "GET") {
    const name = url.searchParams.get("name") || "";
    const postMd = path.join(PUBLISH_QUEUE, "failed", name, "post.md");
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*" });
    try {
      if (!fs.existsSync(postMd)) { res.end(JSON.stringify({ error: "not found" })); return; }
      const full = readPostFull(postMd);
      res.end(JSON.stringify({ ok: true, ...full }));
    } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    return;
  }

  // POST /api/queue/edit-failed — edit fields in a failed post.md then move to pending
  if (url.pathname === "/api/queue/edit-failed" && req.method === "POST") {
    let body = "";
    req.on("data", c => body += c);
    req.on("end", () => {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      try {
        const { name, title, content, text_image, tags, visibility } = JSON.parse(body || "{}");
        const postMd = path.join(PUBLISH_QUEUE, "failed", name, "post.md");
        if (!fs.existsSync(postMd)) { res.end(JSON.stringify({ error: "not found in failed/" })); return; }
        let raw = fs.readFileSync(postMd, "utf8");
        const esc = s => String(s || "").replace(/"/g, '\\"');
        const updated = [];
        if (title !== undefined) { raw = raw.replace(/^title:\s*".*?"$/m, `title: "${esc(title)}"`); updated.push("title"); }
        if (content !== undefined) { raw = raw.replace(/^content:\s*"[\s\S]*?"$/m, `content: "${esc(content)}"`); updated.push("content"); }
        if (text_image !== undefined) { raw = raw.replace(/^text_image:\s*".*?"$/m, `text_image: "${esc(text_image)}"`); updated.push("text_image"); }
        if (visibility !== undefined) { raw = raw.replace(/^visibility:\s*".*?"$/m, `visibility: "${visibility}"`); updated.push("visibility"); }
        if (tags !== undefined) {
          const normalizedTags = tags.map(t => String(t || "").trim()).map(t => t.replace(/^#+|#+$/g, "").trim()).filter(Boolean);
          const tagsYaml = "[" + normalizedTags.map(t => `"${esc(t)}"`).join(", ") + "]";
          raw = raw.replace(/^tags:\s*\[.*?\]$/m, `tags: ${tagsYaml}`);
          updated.push("tags");
        }
        fs.writeFileSync(postMd, raw);
        // Move to pending (with hold timer)
        const src = path.join(PUBLISH_QUEUE, "failed", name);
        const dst = path.join(PUBLISH_QUEUE, "pending", name);
        const errFile = path.join(src, "error.txt");
        if (fs.existsSync(errFile)) fs.unlinkSync(errFile);
        // Update submitted_at so the 5-min hold timer restarts
        let raw2 = fs.readFileSync(postMd, "utf8");
        raw2 = raw2.replace(/^submitted_at:\s*".*?"$/m, `submitted_at: "${new Date().toISOString()}"`);
        fs.writeFileSync(postMd, raw2);
        fs.renameSync(src, dst);
        cachedData = null; cacheTime = 0;
        res.end(JSON.stringify({ ok: true, updated }));
      } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    });
    return;
  }

  // GET /api/queue/worker-log — tail global log OR stream a single entry
  if (url.pathname === "/api/queue/worker-log" && req.method === "GET") {
    const entry = url.searchParams.get("entry");

    // Per-entry streaming: return buffered lines + done status
    if (entry) {
      const state = activeWorkers.get(entry);
      const offset = parseInt(url.searchParams.get("offset")) || 0;
      res.writeHead(200, { "Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*" });
      if (!state) {
        res.end(JSON.stringify({ lines: [], offset: 0, done: true, exitCode: null, found: false }));
      } else {
        const newLines = state.lines.slice(offset);
        res.end(JSON.stringify({ lines: newLines, offset: state.lines.length, done: state.done, exitCode: state.exitCode, found: true }));
      }
      return;
    }

    // Global log tail
    const tail = parseInt(url.searchParams.get("tail")) || 100;
    const logPath = path.join(PUBLISH_QUEUE, "worker.log");
    try {
      if (!fs.existsSync(logPath)) {
        res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
        res.end(JSON.stringify({ lines: [], size: 0 }));
        return;
      }
      const raw = fs.readFileSync(logPath, "utf8");
      const allLines = raw.split("\n");
      const lines = allLines.slice(-tail);
      const stat = fs.statSync(logPath);
      res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ lines, size: stat.size }));
    } catch (e) {
      res.writeHead(500, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // POST /api/queue/retry — move failed entry back to pending
  if (url.pathname === "/api/queue/retry" && req.method === "POST") {
    let body = "";
    req.on("data", c => body += c);
    req.on("end", () => {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      try {
        const { name } = JSON.parse(body || "{}");
        const src = path.join(PUBLISH_QUEUE, "failed", name);
        const dst = path.join(PUBLISH_QUEUE, "pending", name);
        if (!fs.existsSync(src)) { res.end(JSON.stringify({ error: "not found in failed/" })); return; }
        const errFile = path.join(src, "error.txt");
        if (fs.existsSync(errFile)) fs.unlinkSync(errFile);
        fs.renameSync(src, dst);
        cachedData = null; cacheTime = 0;
        res.end(JSON.stringify({ ok: true }));
      } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    });
    return;
  }

  // POST /api/queue/delete-failed — permanently remove failed entry
  if (url.pathname === "/api/queue/delete-failed" && req.method === "POST") {
    let body = "";
    req.on("data", c => body += c);
    req.on("end", () => {
      res.writeHead(200, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
      try {
        const { name } = JSON.parse(body || "{}");
        const target = path.join(PUBLISH_QUEUE, "failed", name);
        if (!fs.existsSync(target)) { res.end(JSON.stringify({ error: "not found in failed/" })); return; }
        fs.rmSync(target, { recursive: true, force: true });
        cachedData = null; cacheTime = 0;
        res.end(JSON.stringify({ ok: true }));
      } catch (e) { res.end(JSON.stringify({ error: e.message })); }
    });
    return;
  }

  if (url.pathname === "/api/commercial/draft-requests" && req.method === "GET") {
    try {
      const status = url.searchParams.get("status") || "pending_review";
      const result = await requestCommercial(`/api/research/draft-requests?status=${encodeURIComponent(status)}`);
      res.writeHead(result.statusCode, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify(result.data));
    } catch (err) {
      res.writeHead(500, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  const commercialApproveMatch = url.pathname.match(/^\/api\/commercial\/draft-requests\/([^/]+)\/approve$/);
  if (commercialApproveMatch && req.method === "POST") {
    try {
      const body = await readJsonBody(req);
      const result = await requestCommercial(
        `/api/research/draft-requests/${encodeURIComponent(commercialApproveMatch[1])}/approve`,
        "POST",
        body
      );
      res.writeHead(result.statusCode, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify(result.data));
    } catch (err) {
      res.writeHead(500, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  const commercialRejectMatch = url.pathname.match(/^\/api\/commercial\/draft-requests\/([^/]+)\/reject$/);
  if (commercialRejectMatch && req.method === "POST") {
    try {
      const body = await readJsonBody(req);
      const result = await requestCommercial(
        `/api/research/draft-requests/${encodeURIComponent(commercialRejectMatch[1])}/reject`,
        "POST",
        body
      );
      res.writeHead(result.statusCode, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify(result.data));
    } catch (err) {
      res.writeHead(500, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // --- Publish review queue (new flow: research confirms final publish) ---
  if (url.pathname === "/api/commercial/publish-queue" && req.method === "GET") {
    try {
      const result = await requestCommercial("/api/research/publish-queue");
      res.writeHead(result.statusCode, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify(result.data));
    } catch (err) {
      res.writeHead(500, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  const commercialConfirmPublishMatch = url.pathname.match(/^\/api\/commercial\/orders\/([^/]+)\/confirm-publish$/);
  if (commercialConfirmPublishMatch && req.method === "POST") {
    try {
      const body = await readJsonBody(req);
      const result = await requestCommercial(
        `/api/research/orders/${encodeURIComponent(commercialConfirmPublishMatch[1])}/confirm-publish`,
        "POST",
        body
      );
      res.writeHead(result.statusCode, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify(result.data));
    } catch (err) {
      res.writeHead(500, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  const commercialRejectPublishMatch = url.pathname.match(/^\/api\/commercial\/orders\/([^/]+)\/reject-publish$/);
  if (commercialRejectPublishMatch && req.method === "POST") {
    try {
      const body = await readJsonBody(req);
      const result = await requestCommercial(
        `/api/research/orders/${encodeURIComponent(commercialRejectPublishMatch[1])}/reject-publish`,
        "POST",
        body
      );
      res.writeHead(result.statusCode, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify(result.data));
    } catch (err) {
      res.writeHead(500, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  res.writeHead(404);
  res.end("Not Found");
});

// === Hold Timer: auto-wake sys1 after HOLD_MINUTES ===
setInterval(() => {
  try {
    const pendingDir = path.join(PUBLISH_QUEUE, "pending");
    if (!fs.existsSync(pendingDir)) return;
    const entries = fs.readdirSync(pendingDir).filter(f => !f.startsWith("."));
    const now = Date.now();

    for (const entry of entries) {
      if (releasedEntries.has(entry)) continue;
      const fullPath = path.join(pendingDir, entry);
      if (!fs.statSync(fullPath).isDirectory()) continue;
      const postMd = path.join(fullPath, "post.md");
      if (!fs.existsSync(postMd)) continue;

      const meta = readPostFull(postMd);
      const submittedMs = meta?.submitted_at ? new Date(meta.submitted_at).getTime() : 0;
      const holdDeadline = submittedMs ? submittedMs + HOLD_MINUTES * 60000 : 0;

      // No submitted_at (legacy) or hold expired → release
      if (!submittedMs || holdDeadline <= now) {
        releasedEntries.add(entry);
        wakeSys1ForEntry(entry, meta);
      }
    }

    // Clean up entries that are no longer in pending (moved by sys1 or rejected)
    for (const name of releasedEntries) {
      if (!fs.existsSync(path.join(pendingDir, name))) {
        releasedEntries.delete(name);
      }
    }
  } catch (err) {
    console.error("[hold-timer] error:", err.message);
  }
}, 30000);

server.listen(PORT, () => {
  console.log(`📮 Agent Message Dashboard: http://localhost:${PORT}`);
  buildAvatarCache().catch(err => console.error("Avatar cache build failed:", err.message));
  // 启动时检查：所有装备了 xiaohongshu-mcp 的 bot 必须有独立的 xhs-profiles 目录
  for (const botId of getAllBots()) {
    try {
      const mcporter = readMcporter(botId);
      if (mcporter.mcpServers?.["xiaohongshu-mcp"]) {
        const profileDir = path.join(XHS_PROFILES_DIR, botId);
        if (!fs.existsSync(profileDir)) {
          fs.mkdirSync(profileDir, { recursive: true });
          console.log(`📁 Auto-created missing xhs-profiles dir: ${profileDir}`);
        }
      }
    } catch {}
  }
});
