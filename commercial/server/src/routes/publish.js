import { Router } from "express";
import { getDb } from "../db.js";
import { requireAuth } from "../auth.js";

const router = Router();

// POST /api/orders/:id/schedule - set schedule time
router.post("/:id/schedule", requireAuth, (req, res) => {
  const { schedule_at } = req.body;
  if (!schedule_at) {
    return res.status(400).json({ error: "请设置发布时间" });
  }

  const scheduleDate = new Date(schedule_at);
  const now = new Date();
  const minTime = new Date(now.getTime() + 60 * 60 * 1000); // 1 hour from now
  const maxTime = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000); // 14 days from now

  if (scheduleDate < minTime) {
    return res.status(400).json({ error: "发布时间需至少在1小时后" });
  }
  if (scheduleDate > maxTime) {
    return res.status(400).json({ error: "发布时间不能超过14天" });
  }

  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });
  if (order.status !== "approved") {
    return res.status(400).json({ error: "只有已批准的订单才能设置发布时间" });
  }

  db.prepare("UPDATE orders SET schedule_at = ?, status = 'scheduled', updated_at = datetime('now') WHERE id = ?").run(
    schedule_at,
    order.id
  );

  res.json({ success: true, schedule_at });
});

// POST /api/orders/:id/submit-publish - client submits the approved draft for
// research department's final publish review. This does NOT push to the
// publisher queue directly — research must confirm via
// POST /api/research/orders/:id/confirm-publish.
router.post("/:id/submit-publish", requireAuth, (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const submittable = ["approved", "scheduled"];
  if (!submittable.includes(order.status)) {
    return res.status(400).json({ error: `当前状态 (${order.status}) 不可提交发布申请` });
  }

  const draft = db.prepare("SELECT id, version FROM drafts WHERE order_id = ? AND status = 'approved'").get(order.id);
  if (!draft) {
    return res.status(400).json({ error: "没有已批准的草稿" });
  }

  db.prepare(
    "UPDATE orders SET status = 'awaiting_publish_review', updated_at = datetime('now') WHERE id = ?"
  ).run(order.id);

  res.json({ success: true, status: "awaiting_publish_review", draft_version: draft.version });
});

// GET /api/orders/:id/publish-status - check publish status
router.get("/:id/publish-status", requireAuth, (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  res.json({ status: order.status, publish_folder: order.publish_folder, xhs_note_id: order.xhs_note_id });
});

export default router;
