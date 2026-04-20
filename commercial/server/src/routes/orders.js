import { Router } from "express";
import { v4 as uuidv4 } from "uuid";
import { getDb } from "../db.js";
import { requireAuth } from "../auth.js";
import { cleanupOrderArtifacts } from "../services/order-cleanup.js";

const router = Router();

// POST /api/orders - create order.
// requirements / title / reference_links / materials are now optional here — the
// client can start with just { bot_id, content_type } and fill in the rest on
// the OrderDetail page (via PATCH /orders/:id and POST /orders/:id/materials).
router.post("/", requireAuth, (req, res) => {
  const { bot_id, title, requirements, content_type, reference_links, max_revisions } = req.body;
  if (!bot_id) {
    return res.status(400).json({ error: "bot_id 为必填项" });
  }

  const db = getDb();
  const bot = db.prepare("SELECT bot_id FROM bot_profiles WHERE bot_id = ? AND is_available = 1").get(bot_id);
  if (!bot) return res.status(400).json({ error: "该 Bot 当前不接单" });

  const id = uuidv4();
  db.prepare(`
    INSERT INTO orders (id, client_id, bot_id, title, requirements, content_type, reference_links, max_revisions)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    id,
    req.clientId,
    bot_id,
    title || "",
    requirements || "",
    content_type || "text_to_image",
    JSON.stringify(reference_links || []),
    max_revisions || 3
  );

  const order = db.prepare("SELECT * FROM orders WHERE id = ?").get(id);
  res.status(201).json({ ...order, reference_links: JSON.parse(order.reference_links) });
});

// PATCH /api/orders/:id - inline edit requirements / reference_links /
// content_type. Only allowed while the order is in a "client can still shape
// the brief" status. Title is auto-generated from V1 draft, not user-editable.
router.patch("/:id", requireAuth, (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const editable = ["pending", "draft_ready", "revision_requested", "approved", "awaiting_review"];
  if (!editable.includes(order.status)) {
    return res.status(400).json({ error: `当前状态 (${order.status}) 不可编辑订单` });
  }

  const body = req.body || {};
  const updates = [];
  const params = [];

  if (typeof body.requirements === "string") {
    if (body.requirements.length > 10000) return res.status(400).json({ error: "内容要求过长" });
    updates.push("requirements = ?");
    params.push(body.requirements);
  }
  if (Array.isArray(body.reference_links)) {
    const cleaned = body.reference_links
      .map((l) => (typeof l === "string" ? l.trim() : ""))
      .filter(Boolean)
      .slice(0, 20);
    updates.push("reference_links = ?");
    params.push(JSON.stringify(cleaned));
  }
  if (typeof body.content_type === "string") {
    const allowed = ["text_to_image", "image", "longform"];
    if (!allowed.includes(body.content_type)) {
      return res.status(400).json({ error: "无效的内容类型" });
    }
    updates.push("content_type = ?");
    params.push(body.content_type);
  }

  if (updates.length === 0) {
    return res.status(400).json({ error: "没有可更新字段" });
  }

  updates.push("updated_at = datetime('now')");
  params.push(order.id);
  db.prepare(`UPDATE orders SET ${updates.join(", ")} WHERE id = ?`).run(...params);

  const updated = db.prepare("SELECT * FROM orders WHERE id = ?").get(order.id);
  res.json({ ...updated, reference_links: JSON.parse(updated.reference_links || "[]") });
});

// GET /api/orders - list my orders
router.get("/", requireAuth, (req, res) => {
  const { status, page = 1, limit = 20 } = req.query;
  const db = getDb();
  const offset = (parseInt(page) - 1) * parseInt(limit);

  let sql = "SELECT o.*, bp.display_name as bot_name FROM orders o LEFT JOIN bot_profiles bp ON o.bot_id = bp.bot_id WHERE o.client_id = ?";
  const params = [req.clientId];

  if (status) {
    sql += " AND o.status = ?";
    params.push(status);
  }

  const countSql = sql.replace("SELECT o.*, bp.display_name as bot_name", "SELECT COUNT(*) as total");
  const { total } = db.prepare(countSql).get(...params);

  sql += " ORDER BY o.created_at DESC LIMIT ? OFFSET ?";
  params.push(parseInt(limit), offset);

  const orders = db.prepare(sql).all(...params);
  res.json({
    orders: orders.map((o) => ({ ...o, reference_links: JSON.parse(o.reference_links) })),
    total,
    page: parseInt(page),
    limit: parseInt(limit),
  });
});

// GET /api/orders/:id - order detail
router.get("/:id", requireAuth, (req, res) => {
  const db = getDb();
  const order = db.prepare(
    "SELECT o.*, bp.display_name as bot_name FROM orders o LEFT JOIN bot_profiles bp ON o.bot_id = bp.bot_id WHERE o.id = ? AND o.client_id = ?"
  ).get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const materials = db
    .prepare("SELECT * FROM order_materials WHERE order_id = ? ORDER BY sort_order ASC, id ASC")
    .all(order.id);
  const drafts = db.prepare("SELECT * FROM drafts WHERE order_id = ? ORDER BY version DESC").all(order.id);
  const latestGenerationRequest = db.prepare(`
    SELECT *
    FROM draft_generation_requests
    WHERE order_id = ?
    ORDER BY created_at DESC
    LIMIT 1
  `).get(order.id);

  res.json({
    ...order,
    reference_links: JSON.parse(order.reference_links),
    materials,
    drafts: drafts.map((d) => ({ ...d, tags: JSON.parse(d.tags) })),
    latest_generation_request: latestGenerationRequest || null,
  });
});

// POST /api/orders/:id/cancel - cancel order
router.post("/:id/cancel", requireAuth, (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const cancellable = ["pending", "awaiting_review", "draft_ready", "revision_requested", "approved"];
  if (!cancellable.includes(order.status)) {
    return res.status(400).json({ error: `当前状态 (${order.status}) 不可取消` });
  }

  db.prepare("UPDATE orders SET status = 'cancelled', updated_at = datetime('now') WHERE id = ?").run(order.id);
  // Sweep iteration scratch (draft-live snapshot + bot session). DB rows and
  // uploaded materials are kept for audit.
  try { cleanupOrderArtifacts(order.id); } catch (err) {
    console.error(`[orders] cleanup after cancel failed:`, err.message);
  }
  res.json({ success: true });
});

export default router;
