import { Router } from "express";
import { getDb } from "../db.js";
import { requireResearchAuth } from "../research-auth.js";

const router = Router();

router.use(requireResearchAuth);

function loadClient(db, clientId) {
  return db
    .prepare("SELECT id, username, display_name, company FROM clients WHERE id = ?")
    .get(clientId);
}

function loadQuotaRow(db, clientId, botId) {
  return db
    .prepare(
      `SELECT client_id, bot_id, used_count, max_count, last_used_at, updated_at
       FROM client_bot_chat_quota
       WHERE client_id = ? AND bot_id = ?`
    )
    .get(clientId, botId);
}

// GET /api/admin/clients - list all clients with their refine-quota summary.
// Used by the quota admin page to show one row per (client, bot) plus any
// clients that don't have a quota row yet.
router.get("/clients", (req, res) => {
  const db = getDb();
  const clients = db
    .prepare("SELECT id, username, display_name, company, created_at FROM clients ORDER BY id")
    .all();
  const quotas = db
    .prepare(
      `SELECT client_id, bot_id, used_count, max_count, last_used_at, updated_at
       FROM client_bot_chat_quota
       ORDER BY client_id, bot_id`
    )
    .all();
  const byClient = new Map(clients.map((c) => [c.id, { ...c, quotas: [] }]));
  for (const q of quotas) {
    const row = byClient.get(q.client_id);
    if (row) row.quotas.push(q);
  }
  res.json({ clients: [...byClient.values()] });
});

// GET /api/admin/clients/:id/quota - list all chat quotas for a client
router.get("/clients/:id/quota", (req, res) => {
  const db = getDb();
  const clientId = Number(req.params.id);
  if (!Number.isInteger(clientId)) {
    return res.status(400).json({ error: "客户 ID 非法" });
  }

  const client = loadClient(db, clientId);
  if (!client) return res.status(404).json({ error: "客户不存在" });

  const rows = db
    .prepare(
      `SELECT bot_id, used_count, max_count, last_used_at, updated_at
       FROM client_bot_chat_quota
       WHERE client_id = ?
       ORDER BY bot_id`
    )
    .all(clientId);

  res.json({ client, quotas: rows });
});

// PATCH /api/admin/clients/:id/quota - adjust chat quota for a (client, bot) pair
// Body: { bot_id: "bot7", max_count?: number, reset?: boolean }
router.patch("/clients/:id/quota", (req, res) => {
  const db = getDb();
  const clientId = Number(req.params.id);
  if (!Number.isInteger(clientId)) {
    return res.status(400).json({ error: "客户 ID 非法" });
  }

  const client = loadClient(db, clientId);
  if (!client) return res.status(404).json({ error: "客户不存在" });

  const botId = typeof req.body?.bot_id === "string" ? req.body.bot_id.trim() : "";
  if (!botId) return res.status(400).json({ error: "bot_id 必填" });

  const { max_count: rawMax, reset } = req.body || {};
  let maxCount;
  if (rawMax !== undefined && rawMax !== null) {
    const parsed = Number(rawMax);
    if (!Number.isInteger(parsed) || parsed <= 0 || parsed > 10000) {
      return res.status(400).json({ error: "max_count 必须是 1-10000 之间的整数" });
    }
    maxCount = parsed;
  }

  if (maxCount === undefined && !reset) {
    return res.status(400).json({ error: "请提供 max_count 或 reset=true" });
  }

  db.prepare(
    "INSERT OR IGNORE INTO client_bot_chat_quota (client_id, bot_id) VALUES (?, ?)"
  ).run(clientId, botId);

  const updates = [];
  const params = [];
  if (maxCount !== undefined) {
    updates.push("max_count = ?");
    params.push(maxCount);
  }
  if (reset) {
    updates.push("used_count = 0");
  }
  updates.push("updated_at = datetime('now')");
  params.push(clientId, botId);

  db.prepare(
    `UPDATE client_bot_chat_quota
     SET ${updates.join(", ")}
     WHERE client_id = ? AND bot_id = ?`
  ).run(...params);

  const row = loadQuotaRow(db, clientId, botId);
  res.json({ success: true, client_id: clientId, quota: row });
});

export default router;
