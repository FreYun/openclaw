import { Router } from "express";
import { v4 as uuidv4 } from "uuid";
import fs from "fs";
import path from "path";
import { getDb } from "../db.js";
import { requireAuth } from "../auth.js";
import { generateDraft } from "../services/bot-integration.js";
import { generateCoverImage, getBotImageStyle } from "../services/image-gen.js";

const router = Router();
const activeGenerations = new Set();

// POST /api/orders/:id/generate - trigger draft generation
router.post("/:id/generate", requireAuth, async (req, res) => {
  const db = getDb();
  const orderId = req.params.id;
  if (activeGenerations.has(orderId)) {
    return res.status(409).json({ error: "草稿生成中，请稍候刷新" });
  }

  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(orderId, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  // Allow retry from stale 'generating', but not while an active pending draft still exists.
  const allowedStatuses = ["pending", "revision_requested", "generating"];
  if (!allowedStatuses.includes(order.status)) {
    return res.status(400).json({ error: `当前状态 (${order.status}) 不可生成草稿` });
  }

  const pendingDraft = db.prepare("SELECT id FROM drafts WHERE order_id = ? AND status = 'pending'").get(order.id);
  if (order.status === "generating" && pendingDraft) {
    return res.status(409).json({ error: "草稿生成中，请稍候刷新" });
  }

  try {
    // Clean up any failed/pending drafts from previous attempts
    db.prepare("DELETE FROM drafts WHERE order_id = ? AND status IN ('pending', 'failed')").run(order.id);

    // Check revision limit (only count successful drafts, not failed/pending)
    const draftCount = db.prepare("SELECT COUNT(*) as count FROM drafts WHERE order_id = ? AND status NOT IN ('pending', 'failed')").get(order.id).count;
    if (draftCount >= order.max_revisions) {
      return res.status(400).json({ error: `已达最大修改次数 (${order.max_revisions})` });
    }

    activeGenerations.add(orderId);

    const version = draftCount + 1;
    const draftId = uuidv4();

    // Create pending draft record
    db.prepare(
      "INSERT INTO drafts (id, order_id, version, status) VALUES (?, ?, ?, 'pending')"
    ).run(draftId, order.id, version);

    // Update order status
    db.prepare("UPDATE orders SET status = 'generating', updated_at = datetime('now') WHERE id = ?").run(order.id);

    // Start generation async
    res.json({ draft_id: draftId, version, status: "generating" });

    // Generate in background
    try {
      const revisionNote = version > 1
        ? db.prepare("SELECT revision_note FROM drafts WHERE order_id = ? AND version = ?").get(order.id, version - 1)?.revision_note
        : null;

      const result = await generateDraft(order, version, revisionNote);

      db.prepare(`
        UPDATE drafts SET title = ?, content = ?, card_text = ?, tags = ?, image_style = ?,
          status = 'ready', generated_at = datetime('now')
        WHERE id = ? AND status = 'pending'
      `).run(result.title, result.content, result.card_text || "", JSON.stringify(result.tags || []), result.image_style || "基础", draftId);

      db.prepare("UPDATE orders SET status = 'draft_ready', updated_at = datetime('now') WHERE id = ? AND status = 'generating'").run(order.id);
    } catch (err) {
      console.error(`Draft generation failed for order ${order.id}:`, err);
      db.prepare("UPDATE drafts SET status = 'failed' WHERE id = ? AND status = 'pending'").run(draftId);

      const nextStatus = version > 1 ? "revision_requested" : "pending";
      db.prepare("UPDATE orders SET status = ?, updated_at = datetime('now') WHERE id = ? AND status = 'generating'").run(
        nextStatus,
        order.id
      );
    } finally {
      activeGenerations.delete(orderId);
    }
  } catch (err) {
    activeGenerations.delete(orderId);
    throw err;
  }
});

// GET /api/orders/:id/drafts - list drafts
router.get("/:id/drafts", requireAuth, (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT id FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const drafts = db.prepare("SELECT * FROM drafts WHERE order_id = ? ORDER BY version DESC").all(order.id);
  res.json(drafts.map((d) => ({ ...d, tags: JSON.parse(d.tags) })));
});

// GET /api/orders/:id/drafts/:version - get specific draft
router.get("/:id/drafts/:version", requireAuth, (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT id FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const draft = db.prepare("SELECT * FROM drafts WHERE order_id = ? AND version = ?").get(
    order.id,
    parseInt(req.params.version)
  );
  if (!draft) return res.status(404).json({ error: "草稿不存在" });

  res.json({ ...draft, tags: JSON.parse(draft.tags) });
});

// POST /api/orders/:id/drafts/:version/approve - approve draft
router.post("/:id/drafts/:version/approve", requireAuth, (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const draft = db.prepare("SELECT * FROM drafts WHERE order_id = ? AND version = ?").get(
    order.id,
    parseInt(req.params.version)
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
  const { revision_note } = req.body;
  if (!revision_note) {
    return res.status(400).json({ error: "请填写修改意见" });
  }

  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const draft = db.prepare("SELECT * FROM drafts WHERE order_id = ? AND version = ?").get(
    order.id,
    parseInt(req.params.version)
  );
  if (!draft) return res.status(404).json({ error: "草稿不存在" });
  if (draft.status !== "ready") {
    return res.status(400).json({ error: `草稿状态 (${draft.status}) 不可请求修改` });
  }

  // Check revision limit
  const draftCount = db.prepare("SELECT COUNT(*) as count FROM drafts WHERE order_id = ?").get(order.id).count;
  if (draftCount >= order.max_revisions) {
    return res.status(400).json({ error: `已达最大修改次数 (${order.max_revisions})` });
  }

  db.prepare("UPDATE drafts SET status = 'revision_requested', revision_note = ?, reviewed_at = datetime('now') WHERE id = ?").run(
    revision_note,
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

    // Save generated images as order materials
    const insertStmt = db.prepare(
      "INSERT INTO order_materials (order_id, file_name, file_path, file_type, file_size) VALUES (?, ?, ?, ?, ?)"
    );

    const savedFiles = [];
    const files = result.files || [];

    // If files array is empty but outputDir exists, scan directory
    if (files.length === 0 && result.outputDir) {
      try {
        const dirFiles = fs.readdirSync(result.outputDir).filter((f) => f.endsWith(".png") || f.endsWith(".jpg"));
        for (const f of dirFiles) {
          files.push(path.join(result.outputDir, f));
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
