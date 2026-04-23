import { Router } from "express";
import bcrypt from "bcryptjs";
import { getDb } from "../db.js";
import { requireAdminAuth } from "../admin-auth.js";

const router = Router();

router.use(requireAdminAuth);

// GET /api/admin/clients
router.get("/clients", (req, res) => {
  const db = getDb();
  const clients = db
    .prepare("SELECT id, username, display_name, company, phone, role, status, bot_access_mode, created_at, updated_at FROM clients ORDER BY id")
    .all();
  const quotas = db
    .prepare(
      `SELECT client_id, bot_id, used_count, max_count, last_used_at, updated_at
       FROM client_bot_chat_quota
       ORDER BY client_id, bot_id`
    )
    .all();
  const botAccess = db
    .prepare("SELECT client_id, bot_id FROM client_bot_access ORDER BY client_id, bot_id")
    .all();
  const byClient = new Map(clients.map((c) => [c.id, { ...c, quotas: [], allowed_bots: [] }]));
  for (const q of quotas) {
    const row = byClient.get(q.client_id);
    if (row) row.quotas.push(q);
  }
  for (const a of botAccess) {
    const row = byClient.get(a.client_id);
    if (row) row.allowed_bots.push(a.bot_id);
  }
  res.json({ clients: [...byClient.values()] });
});

// POST /api/admin/clients — create a new client
router.post("/clients", (req, res) => {
  const { username, password, display_name, company, phone, role } = req.body || {};

  if (!username || !password || !display_name) {
    return res.status(400).json({ error: "username, password, display_name 必填" });
  }
  if (username.length < 2 || username.length > 50) {
    return res.status(400).json({ error: "用户名长度 2-50" });
  }
  if (password.length < 4) {
    return res.status(400).json({ error: "密码至少 4 位" });
  }

  const db = getDb();
  const existing = db.prepare("SELECT id FROM clients WHERE username = ?").get(username);
  if (existing) {
    return res.status(409).json({ error: "用户名已存在" });
  }

  const validRoles = ["client", "admin", "internal"];
  const finalRole = validRoles.includes(role) ? role : "client";
  const hash = bcrypt.hashSync(password, 10);

  const result = db.prepare(
    "INSERT INTO clients (username, password_hash, display_name, company, phone, role) VALUES (?, ?, ?, ?, ?, ?)"
  ).run(username, hash, display_name, company || "", phone || "", finalRole);

  res.json({
    success: true,
    client: { id: result.lastInsertRowid, username, display_name, company: company || "", phone: phone || "", role: finalRole, status: "active" },
  });
});

// PATCH /api/admin/clients/:id — edit client fields
router.patch("/clients/:id", (req, res) => {
  const db = getDb();
  const clientId = Number(req.params.id);
  if (!Number.isInteger(clientId)) {
    return res.status(400).json({ error: "客户 ID 非法" });
  }

  const client = db.prepare("SELECT id FROM clients WHERE id = ?").get(clientId);
  if (!client) return res.status(404).json({ error: "客户不存在" });

  const body = req.body || {};
  const updates = [];
  const params = [];

  if (typeof body.display_name === "string" && body.display_name.trim()) {
    updates.push("display_name = ?");
    params.push(body.display_name.trim());
  }
  if (typeof body.company === "string") {
    updates.push("company = ?");
    params.push(body.company.trim());
  }
  if (typeof body.phone === "string") {
    updates.push("phone = ?");
    params.push(body.phone.trim());
  }
  if (typeof body.role === "string" && ["client", "admin", "internal"].includes(body.role)) {
    updates.push("role = ?");
    params.push(body.role);
  }
  if (typeof body.status === "string" && ["active", "disabled"].includes(body.status)) {
    updates.push("status = ?");
    params.push(body.status);
  }

  if (updates.length === 0) {
    return res.status(400).json({ error: "没有可更新字段" });
  }

  updates.push("updated_at = datetime('now')");
  params.push(clientId);
  db.prepare(`UPDATE clients SET ${updates.join(", ")} WHERE id = ?`).run(...params);

  const updated = db.prepare(
    "SELECT id, username, display_name, company, phone, role, status, created_at FROM clients WHERE id = ?"
  ).get(clientId);
  res.json({ success: true, client: updated });
});

// DELETE /api/admin/clients/:id
router.delete("/clients/:id", (req, res) => {
  const db = getDb();
  const clientId = Number(req.params.id);
  if (!Number.isInteger(clientId)) {
    return res.status(400).json({ error: "客户 ID 非法" });
  }

  if (req.clientId && req.clientId === clientId) {
    return res.status(400).json({ error: "不能删除自己" });
  }

  const client = db.prepare("SELECT id, username, status FROM clients WHERE id = ?").get(clientId);
  if (!client) return res.status(404).json({ error: "客户不存在" });

  if (client.status !== "disabled") {
    return res.status(400).json({ error: "请先停用该用户再删除" });
  }

  const orderIds = db.prepare("SELECT id FROM orders WHERE client_id = ?").all(clientId).map((r) => r.id);
  if (orderIds.length > 0) {
    const ph = orderIds.map(() => "?").join(",");
    db.prepare(`DELETE FROM order_materials WHERE order_id IN (${ph})`).run(...orderIds);
    db.prepare(`DELETE FROM drafts WHERE order_id IN (${ph})`).run(...orderIds);
    db.prepare(`DELETE FROM draft_generation_requests WHERE order_id IN (${ph})`).run(...orderIds);
  }
  db.prepare("DELETE FROM orders WHERE client_id = ?").run(clientId);
  db.prepare("DELETE FROM client_bot_access WHERE client_id = ?").run(clientId);
  db.prepare("DELETE FROM client_bot_chat_quota WHERE client_id = ?").run(clientId);
  db.prepare("DELETE FROM clients WHERE id = ?").run(clientId);

  res.json({ success: true });
});

// POST /api/admin/clients/:id/reset-password
router.post("/clients/:id/reset-password", (req, res) => {
  const db = getDb();
  const clientId = Number(req.params.id);
  if (!Number.isInteger(clientId)) {
    return res.status(400).json({ error: "客户 ID 非法" });
  }

  const client = db.prepare("SELECT id FROM clients WHERE id = ?").get(clientId);
  if (!client) return res.status(404).json({ error: "客户不存在" });

  const { password } = req.body || {};
  if (!password || password.length < 4) {
    return res.status(400).json({ error: "新密码至少 4 位" });
  }

  const hash = bcrypt.hashSync(password, 10);
  db.prepare("UPDATE clients SET password_hash = ?, updated_at = datetime('now') WHERE id = ?").run(hash, clientId);

  res.json({ success: true });
});

// GET /api/admin/clients/:id/quota
router.get("/clients/:id/quota", (req, res) => {
  const db = getDb();
  const clientId = Number(req.params.id);
  if (!Number.isInteger(clientId)) {
    return res.status(400).json({ error: "客户 ID 非法" });
  }

  const client = db.prepare("SELECT id, username, display_name, company FROM clients WHERE id = ?").get(clientId);
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

// PATCH /api/admin/clients/:id/quota
router.patch("/clients/:id/quota", (req, res) => {
  const db = getDb();
  const clientId = Number(req.params.id);
  if (!Number.isInteger(clientId)) {
    return res.status(400).json({ error: "客户 ID 非法" });
  }

  const client = db.prepare("SELECT id, username, display_name, company FROM clients WHERE id = ?").get(clientId);
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

  const row = db.prepare(
    `SELECT client_id, bot_id, used_count, max_count, last_used_at, updated_at
     FROM client_bot_chat_quota
     WHERE client_id = ? AND bot_id = ?`
  ).get(clientId, botId);
  res.json({ success: true, client_id: clientId, quota: row });
});

// GET /api/admin/clients/:id/bot-access
router.get("/clients/:id/bot-access", (req, res) => {
  const db = getDb();
  const clientId = Number(req.params.id);
  if (!Number.isInteger(clientId)) {
    return res.status(400).json({ error: "客户 ID 非法" });
  }

  const client = db.prepare("SELECT id, bot_access_mode FROM clients WHERE id = ?").get(clientId);
  if (!client) return res.status(404).json({ error: "客户不存在" });

  const botIds = db.prepare("SELECT bot_id FROM client_bot_access WHERE client_id = ? ORDER BY bot_id").all(clientId).map((r) => r.bot_id);

  res.json({ mode: client.bot_access_mode, bot_ids: botIds });
});

// PUT /api/admin/clients/:id/bot-access
// Body: { mode: "all" | "restricted", bot_ids?: string[] }
router.put("/clients/:id/bot-access", (req, res) => {
  const db = getDb();
  const clientId = Number(req.params.id);
  if (!Number.isInteger(clientId)) {
    return res.status(400).json({ error: "客户 ID 非法" });
  }

  const client = db.prepare("SELECT id FROM clients WHERE id = ?").get(clientId);
  if (!client) return res.status(404).json({ error: "客户不存在" });

  const { mode, bot_ids } = req.body || {};
  if (!["all", "restricted"].includes(mode)) {
    return res.status(400).json({ error: "mode 必须是 all 或 restricted" });
  }

  db.prepare("UPDATE clients SET bot_access_mode = ?, updated_at = datetime('now') WHERE id = ?").run(mode, clientId);

  if (mode === "restricted" && Array.isArray(bot_ids)) {
    db.prepare("DELETE FROM client_bot_access WHERE client_id = ?").run(clientId);
    const insert = db.prepare("INSERT INTO client_bot_access (client_id, bot_id) VALUES (?, ?)");
    for (const botId of bot_ids) {
      if (typeof botId === "string" && botId.trim()) {
        insert.run(clientId, botId.trim());
      }
    }
  }

  const updatedBotIds = db.prepare("SELECT bot_id FROM client_bot_access WHERE client_id = ? ORDER BY bot_id").all(clientId).map((r) => r.bot_id);
  res.json({ success: true, mode, bot_ids: updatedBotIds });
});

export default router;
