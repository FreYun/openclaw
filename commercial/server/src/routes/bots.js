import { Router } from "express";
import fs from "fs";
import path from "path";
import { getDb } from "../db.js";
import { syncBotCatalog } from "../services/bot-catalog.js";

const router = Router();

// GET /api/bots - list available bots
router.get("/", (req, res) => {
  const db = getDb();
  const bots = db.prepare("SELECT * FROM bot_profiles WHERE is_available = 1 ORDER BY bot_id").all();
  res.json(bots.map((b) => ({ ...b, specialties: JSON.parse(b.specialties) })));
});

// GET /api/bots/:id - bot detail
router.get("/:id", (req, res) => {
  const db = getDb();
  const bot = db.prepare("SELECT * FROM bot_profiles WHERE bot_id = ?").get(req.params.id);
  if (!bot) return res.status(404).json({ error: "Bot 不存在" });
  res.json({ ...bot, specialties: JSON.parse(bot.specialties) });
});

// GET /api/bots/:id/avatar - serve avatar image
router.get("/:id/avatar", (req, res) => {
  const OPENCLAW_DIR = "/home/rooot/.openclaw";
  // Try png, jpg, webp
  for (const ext of ["png", "jpg", "jpeg", "webp"]) {
    const avatarPath = path.join(OPENCLAW_DIR, `workspace-${req.params.id}`, `avatar.${ext}`);
    if (fs.existsSync(avatarPath)) {
      return res.sendFile(avatarPath);
    }
  }
  // Return a 1x1 transparent PNG placeholder instead of error to avoid log spam
  const placeholder = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==", "base64");
  res.set("Content-Type", "image/png");
  res.send(placeholder);
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
