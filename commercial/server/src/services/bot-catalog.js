import fs from "fs";
import path from "path";
import { getDb } from "../db.js";

const OPENCLAW_DIR = "/home/rooot/.openclaw";
const OPENCLAW_CONFIG = path.join(OPENCLAW_DIR, "openclaw.json");
const AVATAR_EXTS = [".png", ".jpg", ".jpeg", ".webp"];

function loadConfiguredBotNames() {
  try {
    const config = JSON.parse(fs.readFileSync(OPENCLAW_CONFIG, "utf8"));
    return new Map(
      (config.agents?.list || [])
        .filter((agent) => agent?.id && agent?.name)
        .map((agent) => [agent.id, agent.name.trim()])
    );
  } catch {
    return new Map();
  }
}

function findAvatarPath(workspacePath) {
  for (const ext of AVATAR_EXTS) {
    const candidate = path.join(workspacePath, `avatar${ext}`);
    if (fs.existsSync(candidate)) return candidate;
  }
  return null;
}

/**
 * Sync bot profiles from workspace files into the database.
 * Reads IDENTITY.md and SOUL.md from each workspace-botN directory.
 */
export function syncBotCatalog() {
  const db = getDb();
  const configuredNames = loadConfiguredBotNames();
  const upsert = db.prepare(`
    INSERT INTO bot_profiles (bot_id, display_name, avatar_path, description, style_summary, specialties, synced_at)
    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    ON CONFLICT(bot_id) DO UPDATE SET
      display_name = excluded.display_name,
      avatar_path = excluded.avatar_path,
      description = excluded.description,
      style_summary = excluded.style_summary,
      specialties = excluded.specialties,
      synced_at = datetime('now')
  `);

  let count = 0;

  // Scan workspace-bot* directories
  const entries = fs.readdirSync(OPENCLAW_DIR).filter((e) => /^workspace-bot\d+$/.test(e));

  for (const dir of entries) {
    const botId = dir.replace("workspace-", "");
    const wsPath = path.join(OPENCLAW_DIR, dir);

    // Read IDENTITY.md
    const identityPath = path.join(wsPath, "IDENTITY.md");
    let displayName = configuredNames.get(botId) || botId;
    let specialties = [];

    if (fs.existsSync(identityPath)) {
      const identity = fs.readFileSync(identityPath, "utf8");
      // Extract name
      const nameMatch = identity.match(/名字[：:]\s*\*{0,2}(.+?)\*{0,2}\s*$/m);
      if (!configuredNames.has(botId) && nameMatch) displayName = nameMatch[1].trim();
      // Extract specialties from 擅长
      const specMatch = identity.match(/擅长[：:]\s*(.+?)$/m);
      if (specMatch) {
        specialties = specMatch[1]
          .split(/[、,，]/)
          .map((s) => s.trim())
          .filter(Boolean);
      }
    }

    // Description priority:
    //   1. workspace-botN/commercial-selfintro  — bot-authored marketing blurb
    //      specifically for the 商单系统 card. This is the source of truth
    //      when present.
    //   2. SOUL.md first few lines — fallback for bots that haven't written
    //      a self-intro yet.
    let description = "";
    let styleSummary = "";

    const selfIntroPath = path.join(wsPath, "commercial-selfintro");
    if (fs.existsSync(selfIntroPath)) {
      try {
        const intro = fs.readFileSync(selfIntroPath, "utf8").trim();
        if (intro) {
          description = intro.slice(0, 300);
          // Use the first line as the subtitle so the marketplace card has
          // something shorter to show. If the file is a single line it'll be
          // the same as description, which the template handles fine.
          styleSummary = intro.split("\n")[0].trim().slice(0, 200);
        }
      } catch {}
    }

    if (!description) {
      const soulPath = path.join(wsPath, "SOUL.md");
      if (fs.existsSync(soulPath)) {
        const soul = fs.readFileSync(soulPath, "utf8");
        // Extract first paragraph as description (skip headings and HTML comments)
        const cleaned = soul.replace(/<!--[\s\S]*?-->/g, "");
        const lines = cleaned
          .split("\n")
          .filter((l) => l.trim() && !l.startsWith("#") && !l.startsWith("---"));
        description = lines.slice(0, 3).join(" ").slice(0, 300);

        // Extract style info
        const styleMatch = soul.match(/说话风格[：:][\s\S]*?(?=\n##|\n---|\n\n\n|$)/i);
        if (styleMatch) {
          styleSummary = styleMatch[0].slice(0, 200).trim();
        }
      }
    }

    // Check avatar
    const hasAvatar = findAvatarPath(wsPath);

    upsert.run(botId, displayName, hasAvatar, description, styleSummary, JSON.stringify(specialties));
    count++;
  }

  return count;
}

/**
 * Auto-sync on first load if empty.
 */
export function ensureBotCatalog() {
  const db = getDb();
  const count = db.prepare("SELECT COUNT(*) as count FROM bot_profiles").get().count;
  if (count === 0) {
    syncBotCatalog();
  }
}
