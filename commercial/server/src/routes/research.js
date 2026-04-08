import { Router } from "express";
import { getDb } from "../db.js";
import { requireResearchAuth } from "../research-auth.js";
import {
  getDraftReviewQueueBase,
  moveDraftReviewSnapshot,
  readDraftReviewSnapshot,
} from "../services/draft-review-queue.js";
import { startDraftGenerationFromRequest } from "./drafts.js";

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

export default router;
