import fs from "fs";
import path from "path";
import { getDb } from "../db.js";

const OPENCLAW_DIR = "/home/rooot/.openclaw";

/**
 * Sync bot profiles from workspace files into the database.
 * Reads IDENTITY.md and SOUL.md from each workspace-botN directory.
 */
export function syncBotCatalog() {
  const db = getDb();
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
    let displayName = botId;
    let specialties = [];

    if (fs.existsSync(identityPath)) {
      const identity = fs.readFileSync(identityPath, "utf8");
      // Extract name
      const nameMatch = identity.match(/名字[：:]\s*\*{0,2}(.+?)\*{0,2}\s*$/m);
      if (nameMatch) displayName = nameMatch[1].trim();
      // Extract specialties from 擅长
      const specMatch = identity.match(/擅长[：:]\s*(.+?)$/m);
      if (specMatch) {
        specialties = specMatch[1]
          .split(/[、,，]/)
          .map((s) => s.trim())
          .filter(Boolean);
      }
    }

    // Read SOUL.md for description and style
    const soulPath = path.join(wsPath, "SOUL.md");
    let description = "";
    let styleSummary = "";

    if (fs.existsSync(soulPath)) {
      const soul = fs.readFileSync(soulPath, "utf8");
      // Extract first paragraph as description (skip headings and HTML comments)
      const cleaned = soul.replace(/<!--[\s\S]*?-->/g, "");
      const lines = cleaned.split("\n").filter((l) => l.trim() && !l.startsWith("#") && !l.startsWith("---"));
      description = lines.slice(0, 3).join(" ").slice(0, 300);

      // Extract style info
      const styleMatch = soul.match(/说话风格[：:][\s\S]*?(?=\n##|\n---|\n\n\n|$)/i);
      if (styleMatch) {
        styleSummary = styleMatch[0].slice(0, 200).trim();
      }
    }

    // Check avatar
    const avatarPath = path.join(wsPath, "avatar.png");
    const hasAvatar = fs.existsSync(avatarPath) ? avatarPath : null;

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
