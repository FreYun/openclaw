#!/usr/bin/env node
/**
 * Portfolio Overview — 独立服务
 * 端口: 18071
 * 数据: 直接读 tougu.db + openclaw.json + avatar 文件
 */

const http = require("http");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const PORT = 28080;
const OPENCLAW_DIR = "/home/rooot/.openclaw";
const OPENCLAW_JSON = path.join(OPENCLAW_DIR, "openclaw.json");
const DASHBOARD_DIR = __dirname;
const AVATAR_CACHE_DIR = path.join(DASHBOARD_DIR, "avatar-cache");
const IMG_EXTS = [".png", ".jpg", ".jpeg", ".webp"];

// --- Avatar cache (read from dashboard's existing cache) ---
function loadAvatarCache() {
  const cache = {};
  if (!fs.existsSync(AVATAR_CACHE_DIR)) return cache;
  for (const f of fs.readdirSync(AVATAR_CACHE_DIR)) {
    if (!f.endsWith(".webp")) continue;
    const botId = f.replace(".webp", "");
    const b64 = fs.readFileSync(path.join(AVATAR_CACHE_DIR, f), "base64");
    cache[botId] = "data:image/webp;base64," + b64;
  }
  // Also check raw avatars for bots without cached thumbs
  for (const e of fs.readdirSync(OPENCLAW_DIR)) {
    if (!e.startsWith("workspace-")) continue;
    const botId = e.replace("workspace-", "");
    if (cache[botId]) continue;
    for (const ext of IMG_EXTS) {
      const p = path.join(OPENCLAW_DIR, e, "avatar" + ext);
      if (fs.existsSync(p)) {
        const mime = ext === ".png" ? "image/png" : ext === ".webp" ? "image/webp" : "image/jpeg";
        cache[botId] = `data:${mime};base64,` + fs.readFileSync(p, "base64");
        break;
      }
    }
  }
  return cache;
}

// --- Agent metadata from openclaw.json + IDENTITY.md ---
function loadAgentMeta() {
  const meta = {};
  // 1. Names from openclaw.json
  try {
    const data = JSON.parse(fs.readFileSync(OPENCLAW_JSON, "utf8"));
    for (const a of (data.agents?.list || [])) {
      meta[a.id] = { name: a.name || a.id, emoji: a.emoji || "" };
    }
  } catch {}
  // 2. Fill in bots from workspace dirs + read IDENTITY.md for emoji/role
  for (const e of fs.readdirSync(OPENCLAW_DIR)) {
    if (!e.startsWith("workspace-bot")) continue;
    const botId = e.replace("workspace-", "");
    if (!meta[botId]) meta[botId] = { name: botId, emoji: "" };
    // Read IDENTITY.md for emoji and role
    const idFile = path.join(OPENCLAW_DIR, e, "IDENTITY.md");
    try {
      const content = fs.readFileSync(idFile, "utf8");
      const clean = s => s.replace(/\*+/g, "").trim();
      // Extract emoji
      const emojiMatch = content.match(/Emoji[：:]\s*(.+)/i);
      if (emojiMatch) {
        let em = clean(emojiMatch[1]);
        if (em === ":sparkles:") em = "\u2728";
        if (em.startsWith("（") || em.startsWith("(")) em = ""; // skip placeholders like （待确认）
        if (em && !meta[botId].emoji) meta[botId].emoji = em;
      }
      // Extract persona/role
      const roleMatch = content.match(/人设[：:]\s*(.+)/i);
      if (roleMatch) meta[botId].role = clean(roleMatch[1]);
      // Extract name from IDENTITY.md if not in openclaw.json
      const nameMatch = content.match(/名字[：:]\s*(.+)/i);
      if (nameMatch && (!meta[botId].name || meta[botId].name === botId)) {
        meta[botId].name = clean(nameMatch[1]);
      }
    } catch {}
  }
  return meta;
}

// --- Portfolio data from tougu.db ---
const PORTFOLIO_PY = path.join(__dirname, "portfolio-query.py");

function getPortfolioSummary() {
  try {
    return execSync(`python3 ${PORTFOLIO_PY}`, { timeout: 5000, encoding: "utf8" }).trim();
  } catch (e) {
    return JSON.stringify({ error: e.message });
  }
}

// --- HTTP server ---
const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);

  // CORS
  res.setHeader("Access-Control-Allow-Origin", "*");

  // Page
  if (url.pathname === "/" || url.pathname === "/portfolio") {
    const html = fs.readFileSync(path.join(DASHBOARD_DIR, "portfolio.html"), "utf8");
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(html);
    return;
  }

  // Portfolio data
  if (url.pathname === "/api/portfolio/summary") {
    const data = getPortfolioSummary();
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(data);
    return;
  }

  // Avatars
  if (url.pathname === "/api/bot/avatars") {
    const cache = loadAvatarCache();
    res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "max-age=60" });
    res.end(JSON.stringify(cache));
    return;
  }

  // Agent meta (names, emojis)
  if (url.pathname === "/api/agents") {
    const meta = loadAgentMeta();
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(meta));
    return;
  }

  res.writeHead(404);
  res.end("Not found");
});

server.listen(PORT, () => {
  console.log(`📊 Portfolio Overview on http://localhost:${PORT}`);
});
