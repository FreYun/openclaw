import { Router } from "express";
import { getDb } from "../db.js";
import { requireResearchAuth } from "../research-auth.js";
import {
  getDraftReviewQueueBase,
  moveDraftReviewSnapshot,
  readDraftReviewSnapshot,
} from "../services/draft-review-queue.js";
import { startDraftGenerationFromRequest } from "./drafts.js";
import { submitToPublisher } from "../services/publish-bridge.js";

const router = Router();

router.use(requireResearchAuth);

function loadDraftRequest(db, requestId) {
  return db.prepare(`
    SELECT r.*, o.title AS order_title, o.status AS order_status,
      c.display_name AS client_name, c.company AS client_company
    FROM draft_generation_requests r
    LEFT JOIN orders o ON o.id = r.order_id
    LEFT JOIN clients c ON c.id = r.client_id
    WHERE r.id = ?
  `).get(requestId);
}

router.get("/draft-requests", (req, res) => {
  const db = getDb();
  const status = req.query.status?.toString().trim();
  const params = [];

  let sql = `
    SELECT r.*, o.title AS order_title, o.status AS order_status,
      c.display_name AS client_name, c.company AS client_company
    FROM draft_generation_requests r
    LEFT JOIN orders o ON o.id = r.order_id
    LEFT JOIN clients c ON c.id = r.client_id
  `;

  if (status && status !== "all") {
    sql += " WHERE r.status = ?";
    params.push(status);
  }

  sql += " ORDER BY r.created_at DESC";

  const requests = db.prepare(sql).all(...params).map((request) => {
    let snapshot = null;
    try {
      snapshot = readDraftReviewSnapshot(request.snapshot_path);
    } catch (err) {
      snapshot = { error: `读取审批快照失败: ${err.message}` };
    }
    return { ...request, snapshot };
  });

  res.json({
    queue_base_path: getDraftReviewQueueBase(),
    requests,
  });
});

router.post("/draft-requests/:id/approve", (req, res) => {
  const db = getDb();
  const request = loadDraftRequest(db, req.params.id);
  if (!request) return res.status(404).json({ error: "审批单不存在" });
  if (request.status !== "pending_review") {
    return res.status(400).json({ error: `当前状态 (${request.status}) 不可审批通过` });
  }

  const reviewerNote = (req.body?.reviewer_note || "").trim();
  const reviewedAt = new Date().toISOString();
  const snapshotPath = moveDraftReviewSnapshot(request.id, request.snapshot_path, "approved", {
    reviewer_note: reviewerNote,
    approved_at: reviewedAt,
    reviewed_at: reviewedAt,
  });

  db.prepare(`
    UPDATE draft_generation_requests
    SET status = 'approved',
        reviewer_note = ?,
        approved_at = ?,
        reviewed_at = ?,
        snapshot_path = ?,
        updated_at = datetime('now')
    WHERE id = ?
  `).run(reviewerNote, reviewedAt, reviewedAt, snapshotPath, request.id);

  res.json({ success: true, request_id: request.id, status: "approved" });

  queueMicrotask(() => {
    startDraftGenerationFromRequest(request.id).catch((err) => {
      console.error(`[research] Failed to start generation for request ${request.id}:`, err);
    });
  });
});

router.post("/draft-requests/:id/reject", (req, res) => {
  const db = getDb();
  const request = loadDraftRequest(db, req.params.id);
  if (!request) return res.status(404).json({ error: "审批单不存在" });
  if (request.status !== "pending_review") {
    return res.status(400).json({ error: `当前状态 (${request.status}) 不可驳回` });
  }

  const reviewerNote = (req.body?.reviewer_note || "").trim();
  const reviewedAt = new Date().toISOString();
  const snapshotPath = moveDraftReviewSnapshot(request.id, request.snapshot_path, "rejected", {
    reviewer_note: reviewerNote,
    reviewed_at: reviewedAt,
  });
  const nextOrderStatus = request.version > 1 ? "revision_requested" : "pending";

  db.prepare(`
    UPDATE draft_generation_requests
    SET status = 'rejected',
        reviewer_note = ?,
        reviewed_at = ?,
        snapshot_path = ?,
        updated_at = datetime('now')
    WHERE id = ?
  `).run(reviewerNote, reviewedAt, snapshotPath, request.id);

  db.prepare("UPDATE orders SET status = ?, updated_at = datetime('now') WHERE id = ?").run(
    nextOrderStatus,
    request.order_id
  );

  res.json({
    success: true,
    request_id: request.id,
    status: "rejected",
    order_status: nextOrderStatus,
  });
});

// ---------------------------------------------------------------------------
// Publish review endpoints (new "research department is the final publish gate" flow)
// ---------------------------------------------------------------------------

// GET /api/research/publish-queue - list orders awaiting publish review.
// Each order is enriched with its latest approved draft so the dashboard can
// render everything research needs to decide inline, without a second call.
router.get("/publish-queue", (req, res) => {
  const db = getDb();
  const rows = db.prepare(`
    SELECT o.id, o.title, o.bot_id, o.status, o.schedule_at, o.updated_at,
           o.requirements, o.content_type, o.reference_links,
           c.display_name AS client_name, c.company AS client_company, c.phone AS client_phone
    FROM orders o
    LEFT JOIN clients c ON c.id = o.client_id
    WHERE o.status = 'awaiting_publish_review'
    ORDER BY o.updated_at ASC
  `).all();

  const draftStmt = db.prepare(
    "SELECT * FROM drafts WHERE order_id = ? AND status = 'approved' ORDER BY version DESC LIMIT 1"
  );
  const materialsStmt = db.prepare(
    "SELECT id, file_name, file_type, file_size FROM order_materials WHERE order_id = ? ORDER BY sort_order ASC, id ASC"
  );

  const parseTags = (raw) => {
    try { return JSON.parse(raw || "[]"); } catch { return []; }
  };
  const parseLinks = (raw) => {
    try { return JSON.parse(raw || "[]"); } catch { return []; }
  };

  const enriched = rows.map((order) => {
    const draft = draftStmt.get(order.id);
    return {
      ...order,
      reference_links: parseLinks(order.reference_links),
      materials: materialsStmt.all(order.id),
      draft: draft
        ? { ...draft, tags: parseTags(draft.tags) }
        : null,
    };
  });

  res.json({ orders: enriched });
});

// GET /api/research/orders/:id - load order with its approved draft for review
router.get("/orders/:id", (req, res) => {
  const db = getDb();
  const order = db.prepare(`
    SELECT o.*, c.display_name AS client_name, c.company AS client_company, c.phone AS client_phone
    FROM orders o
    LEFT JOIN clients c ON c.id = o.client_id
    WHERE o.id = ?
  `).get(req.params.id);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const draft = db.prepare(
    "SELECT * FROM drafts WHERE order_id = ? AND status = 'approved' ORDER BY version DESC LIMIT 1"
  ).get(order.id);

  res.json({ order, draft });
});

// POST /api/research/orders/:id/confirm-publish - research confirms the publish,
// actually pushes the draft to the publisher queue.
router.post("/orders/:id/confirm-publish", async (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ?").get(req.params.id);
  if (!order) return res.status(404).json({ error: "订单不存在" });
  if (order.status !== "awaiting_publish_review") {
    return res.status(400).json({ error: `当前状态 (${order.status}) 不可确认发布` });
  }

  const draft = db.prepare(
    "SELECT * FROM drafts WHERE order_id = ? AND status = 'approved'"
  ).get(order.id);
  if (!draft) {
    return res.status(400).json({ error: "没有已批准的草稿" });
  }

  try {
    const folder = await submitToPublisher(order, draft);
    db.prepare(
      "UPDATE orders SET status = 'publishing', publish_folder = ?, updated_at = datetime('now') WHERE id = ?"
    ).run(folder, order.id);
    res.json({ success: true, status: "publishing", publish_folder: folder });
  } catch (err) {
    console.error(`[research] confirm-publish failed for order ${order.id}:`, err);
    res.status(500).json({ error: "发布失败: " + err.message });
  }
});

// POST /api/research/orders/:id/reject-publish - research rejects the publish
// submission, sends the order back to the client (status → approved) so they
// can resubmit or revise.
router.post("/orders/:id/reject-publish", (req, res) => {
  const { reason } = req.body || {};
  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ?").get(req.params.id);
  if (!order) return res.status(404).json({ error: "订单不存在" });
  if (order.status !== "awaiting_publish_review") {
    return res.status(400).json({ error: `当前状态 (${order.status}) 不可驳回发布` });
  }

  db.prepare(
    "UPDATE orders SET status = 'approved', updated_at = datetime('now') WHERE id = ?"
  ).run(order.id);

  // Note: reject reason currently not persisted to a dedicated column. If
  // auditability becomes a requirement, add an orders.publish_review_note column.
  res.json({ success: true, status: "approved", reason: reason || "" });
});

export default router;
