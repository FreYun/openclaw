import { Router } from "express";
import { v4 as uuidv4 } from "uuid";
import fs from "fs";
import path from "path";
import { getDb } from "../db.js";
import { requireAuth } from "../auth.js";
import { generateDraft } from "../services/bot-integration.js";
import { generateCoverImage, getBotImageStyle } from "../services/image-gen.js";
import {
  createDraftReviewSnapshot,
  moveDraftReviewSnapshot,
  readDraftReviewSnapshot,
} from "../services/draft-review-queue.js";

const router = Router();
const activeGenerations = new Set();

function parseTags(tags) {
  try {
    return JSON.parse(tags || "[]");
  } catch {
    return [];
  }
}

function readTextMaterial(material) {
  if (!material.file_type.startsWith("text/")) return null;
  try {
    return fs.readFileSync(material.file_path, "utf8");
  } catch {
    return null;
  }
}

function getCompletedDraftCount(db, orderId) {
  return db
    .prepare("SELECT COUNT(*) AS count FROM drafts WHERE order_id = ? AND status NOT IN ('pending', 'failed')")
    .get(orderId).count;
}

function buildDraftReviewSnapshot(db, order, client, version, revisionNote) {
  const materials = db.prepare("SELECT * FROM order_materials WHERE order_id = ? ORDER BY uploaded_at ASC").all(order.id);
  const drafts = db.prepare("SELECT * FROM drafts WHERE order_id = ? ORDER BY version DESC").all(order.id);

  return {
    order: {
      id: order.id,
      title: order.title,
      bot_id: order.bot_id,
      status: order.status,
      requirements: order.requirements,
      content_type: order.content_type,
      max_revisions: order.max_revisions,
      reference_links: JSON.parse(order.reference_links || "[]"),
      created_at: order.created_at,
      updated_at: order.updated_at,
    },
    client: client
      ? {
          id: client.id,
          username: client.username,
          display_name: client.display_name,
          company: client.company,
          phone: client.phone,
        }
      : null,
    generation_request: {
      version,
      revision_note: revisionNote || "",
    },
    materials: materials.map((material) => ({
      id: material.id,
      file_name: material.file_name,
      file_type: material.file_type,
      file_size: material.file_size,
      file_path: material.file_path,
      uploaded_at: material.uploaded_at,
      text_content: readTextMaterial(material),
    })),
    drafts: drafts.map((draft) => ({
      id: draft.id,
      version: draft.version,
      title: draft.title,
      content: draft.content,
      card_text: draft.card_text,
      tags: parseTags(draft.tags),
      image_style: draft.image_style,
      status: draft.status,
      revision_note: draft.revision_note,
      generated_at: draft.generated_at,
      reviewed_at: draft.reviewed_at,
      created_at: draft.created_at,
    })),
  };
}

export async function startDraftGenerationFromRequest(requestId) {
  const db = getDb();
  const request = db.prepare("SELECT * FROM draft_generation_requests WHERE id = ?").get(requestId);
  if (!request) {
    throw new Error("审批单不存在");
  }
  if (!["approved", "generating"].includes(request.status)) {
    throw new Error(`审批单状态 (${request.status}) 不可开始生成`);
  }

  const order = db.prepare("SELECT * FROM orders WHERE id = ?").get(request.order_id);
  if (!order) {
    throw new Error("订单不存在");
  }

  if (activeGenerations.has(order.id)) {
    return;
  }

  let draftId = request.result_draft_id || uuidv4();
  let snapshotPath = request.snapshot_path;

  try {
    activeGenerations.add(order.id);

    db.prepare("DELETE FROM drafts WHERE order_id = ? AND status IN ('pending', 'failed')").run(order.id);

    const existingDraft = db.prepare("SELECT id FROM drafts WHERE id = ?").get(draftId);
    if (!existingDraft) {
      db.prepare("INSERT INTO drafts (id, order_id, version, status) VALUES (?, ?, ?, 'pending')").run(
        draftId,
        order.id,
        request.version
      );
    }

    snapshotPath = moveDraftReviewSnapshot(request.id, snapshotPath, "generating", {
      result_draft_id: draftId,
      generation_started_at: new Date().toISOString(),
    });

    db.prepare(`
      UPDATE draft_generation_requests
      SET status = 'generating',
          snapshot_path = ?,
          result_draft_id = ?,
          updated_at = datetime('now')
      WHERE id = ?
    `).run(snapshotPath, draftId, request.id);
    db.prepare("UPDATE orders SET status = 'generating', updated_at = datetime('now') WHERE id = ?").run(order.id);

    const requestSnapshot = readDraftReviewSnapshot(snapshotPath);
    const result = await generateDraft(order, request.version, request.revision_note || null, requestSnapshot);

    db.prepare(`
      UPDATE drafts
      SET title = ?,
          content = ?,
          card_text = ?,
          tags = ?,
          image_style = ?,
          status = 'ready',
          generated_at = datetime('now')
      WHERE id = ? AND status = 'pending'
    `).run(
      result.title,
      result.content,
      result.card_text || "",
      JSON.stringify(result.tags || []),
      result.image_style || "基础",
      draftId
    );

    snapshotPath = moveDraftReviewSnapshot(request.id, snapshotPath, "completed", {
      result_draft_id: draftId,
      completed_at: new Date().toISOString(),
      result: {
        title: result.title,
        tags: result.tags || [],
        image_style: result.image_style || "基础",
      },
    });

    db.prepare(`
      UPDATE draft_generation_requests
      SET status = 'completed',
          snapshot_path = ?,
          result_draft_id = ?,
          updated_at = datetime('now')
      WHERE id = ?
    `).run(snapshotPath, draftId, request.id);
    db.prepare("UPDATE orders SET status = 'draft_ready', updated_at = datetime('now') WHERE id = ?").run(order.id);
  } catch (err) {
    console.error(`Draft generation failed for request ${request.id}:`, err);

    db.prepare("UPDATE drafts SET status = 'failed' WHERE id = ? AND status = 'pending'").run(draftId);

    const nextOrderStatus = request.version > 1 ? "revision_requested" : "pending";
    snapshotPath = moveDraftReviewSnapshot(request.id, snapshotPath, "failed", {
      result_draft_id: draftId,
      failed_at: new Date().toISOString(),
      error: err.message,
    });

    db.prepare(`
      UPDATE draft_generation_requests
      SET status = 'failed',
          snapshot_path = ?,
          result_draft_id = ?,
          updated_at = datetime('now')
      WHERE id = ?
    `).run(snapshotPath, draftId, request.id);
    db.prepare("UPDATE orders SET status = ?, updated_at = datetime('now') WHERE id = ?").run(
      nextOrderStatus,
      order.id
    );

    throw err;
  } finally {
    activeGenerations.delete(order.id);
  }
}

// POST /api/orders/:id/generate - submit draft generation request for research approval
router.post("/:id/generate", requireAuth, async (req, res) => {
  const db = getDb();
  const orderId = req.params.id;
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(orderId, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const allowedStatuses = ["pending", "revision_requested"];
  if (!allowedStatuses.includes(order.status)) {
    return res.status(400).json({ error: `当前状态 (${order.status}) 不可提交草稿审批` });
  }

  const openRequest = db.prepare(`
    SELECT id, status
    FROM draft_generation_requests
    WHERE order_id = ?
      AND status IN ('pending_review', 'approved', 'generating')
    ORDER BY created_at DESC
    LIMIT 1
  `).get(order.id);
  if (openRequest) {
    return res.status(409).json({ error: "已有草稿审批单处理中，请稍候刷新" });
  }

  const draftCount = getCompletedDraftCount(db, order.id);
  if (draftCount >= order.max_revisions) {
    return res.status(400).json({ error: `已达最大修改次数 (${order.max_revisions})` });
  }

  const version = draftCount + 1;
  const revisionNote =
    version > 1
      ? db.prepare("SELECT revision_note FROM drafts WHERE order_id = ? AND version = ?").get(order.id, version - 1)
          ?.revision_note || ""
      : "";
  const client = db
    .prepare("SELECT id, username, display_name, company, phone FROM clients WHERE id = ?")
    .get(req.clientId);
  const requestId = uuidv4();

  try {
    const { snapshotPath } = createDraftReviewSnapshot(
      requestId,
      buildDraftReviewSnapshot(db, order, client, version, revisionNote)
    );

    db.prepare(`
      INSERT INTO draft_generation_requests (
        id, order_id, client_id, bot_id, version, status, revision_note, snapshot_path
      ) VALUES (?, ?, ?, ?, ?, 'pending_review', ?, ?)
    `).run(requestId, order.id, req.clientId, order.bot_id, version, revisionNote, snapshotPath);

    db.prepare("UPDATE orders SET status = 'awaiting_review', updated_at = datetime('now') WHERE id = ?").run(order.id);

    res.json({ request_id: requestId, version, status: "awaiting_review" });
  } catch (err) {
    console.error(`Failed to queue draft request for order ${order.id}:`, err);
    res.status(500).json({ error: "提交草稿审批失败" });
  }
});

// GET /api/orders/:id/drafts - list drafts
router.get("/:id/drafts", requireAuth, (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT id FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const drafts = db.prepare("SELECT * FROM drafts WHERE order_id = ? ORDER BY version DESC").all(order.id);
  res.json(drafts.map((draft) => ({ ...draft, tags: parseTags(draft.tags) })));
});

// GET /api/orders/:id/drafts/:version - get specific draft
router.get("/:id/drafts/:version", requireAuth, (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT id FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const draft = db.prepare("SELECT * FROM drafts WHERE order_id = ? AND version = ?").get(
    order.id,
    parseInt(req.params.version, 10)
  );
  if (!draft) return res.status(404).json({ error: "草稿不存在" });

  res.json({ ...draft, tags: parseTags(draft.tags) });
});

// POST /api/orders/:id/drafts/:version/approve - approve draft
router.post("/:id/drafts/:version/approve", requireAuth, (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const draft = db.prepare("SELECT * FROM drafts WHERE order_id = ? AND version = ?").get(
    order.id,
    parseInt(req.params.version, 10)
  );
  if (!draft) return res.status(404).json({ error: "草稿不存在" });
  if (draft.status !== "ready") {
    return res.status(400).json({ error: `草稿状态 (${draft.status}) 不可批准` });
  }

  db.prepare("UPDATE drafts SET status = 'approved', reviewed_at = datetime('now') WHERE id = ?").run(draft.id);
  db.prepare("UPDATE orders SET status = 'approved', updated_at = datetime('now') WHERE id = ?").run(order.id);

  res.json({ success: true });
});

// POST /api/orders/:id/drafts/:version/revise - request revision
router.post("/:id/drafts/:version/revise", requireAuth, (req, res) => {
  const { revision_note: revisionNote } = req.body;
  if (!revisionNote) {
    return res.status(400).json({ error: "请填写修改意见" });
  }

  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const draft = db.prepare("SELECT * FROM drafts WHERE order_id = ? AND version = ?").get(
    order.id,
    parseInt(req.params.version, 10)
  );
  if (!draft) return res.status(404).json({ error: "草稿不存在" });
  if (draft.status !== "ready") {
    return res.status(400).json({ error: `草稿状态 (${draft.status}) 不可请求修改` });
  }

  const draftCount = db.prepare("SELECT COUNT(*) AS count FROM drafts WHERE order_id = ?").get(order.id).count;
  if (draftCount >= order.max_revisions) {
    return res.status(400).json({ error: `已达最大修改次数 (${order.max_revisions})` });
  }

  db.prepare("UPDATE drafts SET status = 'revision_requested', revision_note = ?, reviewed_at = datetime('now') WHERE id = ?").run(
    revisionNote,
    draft.id
  );
  db.prepare("UPDATE orders SET status = 'revision_requested', updated_at = datetime('now') WHERE id = ?").run(order.id);

  res.json({ success: true });
});

// GET /api/orders/:id/cover-style - check if bot has an image style
router.get("/:id/cover-style", requireAuth, (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT bot_id FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const style = getBotImageStyle(order.bot_id);
  res.json({ has_style: !!style, bot_id: order.bot_id });
});

// POST /api/orders/:id/generate-cover - generate cover image
router.post("/:id/generate-cover", requireAuth, async (req, res) => {
  const { description } = req.body;
  if (!description) {
    return res.status(400).json({ error: "请描述封面内容" });
  }

  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  try {
    const result = await generateCoverImage(order.bot_id, description);

    const insertStmt = db.prepare(
      "INSERT INTO order_materials (order_id, file_name, file_path, file_type, file_size) VALUES (?, ?, ?, ?, ?)"
    );

    const savedFiles = [];
    const files = result.files || [];

    if (files.length === 0 && result.outputDir) {
      try {
        const dirFiles = fs
          .readdirSync(result.outputDir)
          .filter((fileName) => fileName.endsWith(".png") || fileName.endsWith(".jpg"));
        for (const fileName of dirFiles) {
          files.push(path.join(result.outputDir, fileName));
        }
      } catch {}
    }

    for (const filePath of files) {
      if (fs.existsSync(filePath)) {
        const stat = fs.statSync(filePath);
        const fileName = `cover_${path.basename(filePath)}`;
        const dbResult = insertStmt.run(order.id, fileName, filePath, "image/png", stat.size);
        savedFiles.push({
          id: dbResult.lastInsertRowid,
          file_name: fileName,
          file_path: filePath,
          file_size: stat.size,
        });
      }
    }

    res.json({ success: true, output_dir: result.outputDir, files: savedFiles });
  } catch (err) {
    console.error(`Cover generation failed for order ${order.id}:`, err);
    res.status(500).json({ error: err.message });
  }
});

export default router;
