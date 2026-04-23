import { Router } from "express";
import fs from "fs";
import path from "path";
import { getDb } from "../db.js";
import { syncBotCatalog } from "../services/bot-catalog.js";
import { getClientAllowedBotIds, tryResolveClientId } from "../bot-access.js";

import { OPENCLAW_DIR } from "../paths.js";

const router = Router();
const IMG_EXTS = [".png", ".jpg", ".jpeg", ".webp"];
const MIME_MAP = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp" };
const avatarPlaceholder = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
  "base64"
);

function botWorkspaceDir(botId) {
  const mapping = { mag1: "workspace-mag1", main: "workspace-mag1", sys1: "workspace-sys1", sys2: "workspace-sys2", sys3: "workspace-sys3" };
  return mapping[botId] || `workspace-${botId}`;
}

function resolveAvatarPath(botId) {
  const wsDir = path.join(OPENCLAW_DIR, botWorkspaceDir(botId));
  for (const ext of IMG_EXTS) {
    const candidate = path.join(wsDir, `avatar${ext}`);
    if (fs.existsSync(candidate)) return candidate;
  }
  return null;
}

function sendAvatarPlaceholder(res) {
  res.set("Content-Type", "image/png");
  res.send(avatarPlaceholder);
}

// GET /api/bots - list available bots (restricted users only see allowed bots)
router.get("/", (req, res) => {
  const db = getDb();
  let bots = db.prepare("SELECT * FROM bot_profiles WHERE is_available = 1 ORDER BY bot_id").all();
  const clientId = tryResolveClientId(req);
  if (clientId) {
    const allowed = getClientAllowedBotIds(db, clientId);
    if (allowed) {
      const set = new Set(allowed);
      bots = bots.filter((b) => set.has(b.bot_id));
    }
  }
  res.json(bots.map((b) => ({ ...b, specialties: JSON.parse(b.specialties) })));
});

// GET /api/bots/:id - bot detail
router.get("/:id", (req, res) => {
  const db = getDb();
  const bot = db.prepare("SELECT * FROM bot_profiles WHERE bot_id = ?").get(req.params.id);
  if (!bot) return res.status(404).json({ error: "Bot 不存在" });
  res.json({ ...bot, specialties: JSON.parse(bot.specialties) });
});

// GET /api/bots/:id/capabilities - read-only snapshot of equipped skills and
// MCP servers. Source of truth is workspace-botN/EQUIPPED_SKILLS.md (written
// by the 装备 system) and workspace-botN/config/mcporter.json. Commercial
// clients see this so they know what the达人 can actually do before ordering.
const MCP_DISPLAY_NAMES = {
  "xiaohongshu-mcp": "小红书",
  "xhs-mcp": "小红书",
  "research-mcp": "研究数据库",
  "compliance-mcp": "合规审核",
  "image-gen-mcp": "图像生成",
  "tougu-portfolio-mcp": "投顾组合",
  "feishu-mcp": "飞书",
};

function parseEquippedSkills(mdPath) {
  if (!fs.existsSync(mdPath)) return {};
  const text = fs.readFileSync(mdPath, "utf8");
  const lines = text.split(/\r?\n/);
  const result = {};
  let currentCategory = null;
  for (const line of lines) {
    const hdr = line.match(/^##\s+(.+?)\s*$/);
    if (hdr) {
      currentCategory = hdr[1].trim();
      result[currentCategory] = [];
      continue;
    }
    if (!currentCategory) continue;
    // Match lines like: `- 小红书运营（xhs-op） — ...` or `- xxx (xxx) — ...`
    const item = line.match(/^-\s+(.+?)\s*[（(]\s*([^）)]+?)\s*[）)]/);
    if (item) {
      result[currentCategory].push({ name: item[1].trim(), id: item[2].trim() });
    }
  }
  // Drop empty categories.
  for (const key of Object.keys(result)) {
    if (result[key].length === 0) delete result[key];
  }
  return result;
}

function parseMcpServers(jsonPath) {
  if (!fs.existsSync(jsonPath)) return [];
  try {
    const raw = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
    const servers = raw.mcpServers || {};
    return Object.keys(servers).map((name) => ({
      name,
      display_name: MCP_DISPLAY_NAMES[name] || name,
    }));
  } catch {
    return [];
  }
}

router.get("/:id/capabilities", (req, res) => {
  const botId = req.params.id;
  const db = getDb();
  const bot = db.prepare("SELECT bot_id FROM bot_profiles WHERE bot_id = ?").get(botId);
  if (!bot) return res.status(404).json({ error: "Bot 不存在" });

  const wsDir = path.join(OPENCLAW_DIR, botWorkspaceDir(botId));
  const skills = parseEquippedSkills(path.join(wsDir, "EQUIPPED_SKILLS.md"));
  const mcpServers = parseMcpServers(path.join(wsDir, "config", "mcporter.json"));

  res.json({
    bot_id: botId,
    skills,
    mcp_servers: mcpServers,
  });
});

// GET /api/bots/:id/avatar - serve avatar image
router.get("/:id/avatar", (req, res) => {
  const avatarPath = resolveAvatarPath(req.params.id);
  if (!avatarPath) {
    return sendAvatarPlaceholder(res);
  }

  try {
    const ext = path.extname(avatarPath).toLowerCase();
    const stat = fs.statSync(avatarPath);
    const etag = `"${stat.mtimeMs.toString(36)}-${stat.size.toString(36)}"`;
    if (req.headers["if-none-match"] === etag) {
      return res.status(304).end();
    }

    res.set("Content-Type", MIME_MAP[ext] || "application/octet-stream");
    res.set("Cache-Control", "max-age=86400");
    res.set("ETag", etag);
    return fs.createReadStream(avatarPath)
      .on("error", () => sendAvatarPlaceholder(res))
      .pipe(res);
  } catch {
    return sendAvatarPlaceholder(res);
  }
});

// GET /api/bots/:id/offerings - per-bot service offerings for the service
// selection step. Reads workspace-botN/commercial-offerings.json. Bots without
// this file return an empty array (no selection step needed).
router.get("/:id/offerings", (req, res) => {
  const botId = req.params.id;
  const wsDir = path.join(OPENCLAW_DIR, botWorkspaceDir(botId));
  const offeringsPath = path.join(wsDir, "commercial-offerings.json");
  if (!fs.existsSync(offeringsPath)) {
    return res.json({ offerings: [] });
  }
  try {
    const data = JSON.parse(fs.readFileSync(offeringsPath, "utf8"));
    res.json({ offerings: data.offerings || [] });
  } catch {
    res.status(500).json({ error: "配置文件解析失败" });
  }
});

// POST /api/bots/sync - admin: re-sync bot catalog from workspace files
router.post("/sync", (req, res) => {
  try {
    const count = syncBotCatalog();
    res.json({ synced: count });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
