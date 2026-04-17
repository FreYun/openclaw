import { Router } from "express";
import { v4 as uuidv4 } from "uuid";
import fs from "fs";
import path from "path";
import { getDb } from "../db.js";
import { requireAuth } from "../auth.js";
import { generateDraft, refineDraftViaChat, refineDraftViaChatStreaming } from "../services/bot-integration.js";
import { generateCoverImage, getBotImageStyle, splitContentForImages } from "../services/image-gen.js";
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
  const materials = db
    .prepare("SELECT * FROM order_materials WHERE order_id = ? ORDER BY sort_order ASC, id ASC")
    .all(order.id);
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

// PATCH /api/orders/:id/drafts/:version - edit draft fields inline.
// Only the latest draft in status='ready' can be edited by the client.
router.patch("/:id/drafts/:version", requireAuth, (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const version = parseInt(req.params.version, 10);
  const draft = db.prepare("SELECT * FROM drafts WHERE order_id = ? AND version = ?").get(order.id, version);
  if (!draft) return res.status(404).json({ error: "草稿不存在" });
  if (draft.status !== "ready") {
    return res.status(400).json({ error: `草稿状态 (${draft.status}) 不可编辑` });
  }

  const latest = db.prepare("SELECT MAX(version) AS v FROM drafts WHERE order_id = ?").get(order.id);
  if (latest.v !== version) {
    return res.status(400).json({ error: "只能编辑最新版本草稿" });
  }

  const updates = [];
  const params = [];
  const body = req.body || {};

  if (typeof body.title === "string") {
    if (body.title.length > 200) return res.status(400).json({ error: "标题过长" });
    updates.push("title = ?");
    params.push(body.title);
  }
  if (typeof body.content === "string") {
    if (body.content.length > 20000) return res.status(400).json({ error: "正文过长" });
    updates.push("content = ?");
    params.push(body.content);
  }
  if (typeof body.card_text === "string") {
    if (body.card_text.length > 2000) return res.status(400).json({ error: "卡片文字过长" });
    updates.push("card_text = ?");
    params.push(body.card_text);
  }
  if (Array.isArray(body.tags)) {
    const cleaned = body.tags
      .map((t) => (typeof t === "string" ? t.trim().replace(/^#+/, "") : ""))
      .filter(Boolean)
      .slice(0, 20);
    updates.push("tags = ?");
    params.push(JSON.stringify(cleaned));
  }

  if (updates.length === 0) {
    return res.status(400).json({ error: "没有可更新字段" });
  }

  params.push(draft.id);
  db.prepare(`UPDATE drafts SET ${updates.join(", ")} WHERE id = ?`).run(...params);

  const updated = db.prepare("SELECT * FROM drafts WHERE id = ?").get(draft.id);
  res.json({ ...updated, tags: parseTags(updated.tags) });
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

// POST /api/orders/:id/drafts/:version/unapprove - roll back the previous "approve" step.
// 用于客户点过"通过"/安排过时间之后想继续修改。只要订单还没走到研究部最终审核 (awaiting_publish_review)
// 就可以退回到 draft_ready 状态。
router.post("/:id/drafts/:version/unapprove", requireAuth, (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  if (!["approved", "scheduled"].includes(order.status)) {
    return res.status(400).json({ error: `当前状态 (${order.status}) 不可回退` });
  }

  const draft = db.prepare("SELECT * FROM drafts WHERE order_id = ? AND version = ?").get(
    order.id,
    parseInt(req.params.version, 10)
  );
  if (!draft) return res.status(404).json({ error: "草稿不存在" });
  if (draft.status !== "approved") {
    return res.status(400).json({ error: `草稿状态 (${draft.status}) 不可回退` });
  }

  db.prepare("UPDATE drafts SET status = 'ready', reviewed_at = NULL WHERE id = ?").run(draft.id);
  db.prepare(
    "UPDATE orders SET status = 'draft_ready', schedule_at = NULL, updated_at = datetime('now') WHERE id = ?"
  ).run(order.id);

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
// description 可空 —— 为空时用最新草稿的标题+正文作为生图内容,配合 bot 专属画风
router.post("/:id/generate-cover", requireAuth, async (req, res) => {
  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  let description = typeof req.body?.description === "string" ? req.body.description.trim() : "";
  // Desired output count. Billing convention: 1 MCP call == 1 image, even if
  // banana2 happens to return 2 files per call (we discard the extras). So
  // desiredCount == number of MCP calls we make, 1:1.
  const rawCount = Number(req.body?.count);
  const desiredCount = Number.isFinite(rawCount) ? Math.min(5, Math.max(1, Math.round(rawCount))) : 1;

  if (!description) {
    // 取最新一版草稿的 title + content 作为生图依据
    const latestDraft = db
      .prepare(
        "SELECT title, content FROM drafts WHERE order_id = ? AND status NOT IN ('pending', 'failed') ORDER BY version DESC LIMIT 1"
      )
      .get(order.id);

    const parts = [];
    if (latestDraft?.title) parts.push(`标题:${latestDraft.title}`);
    if (latestDraft?.content) parts.push(latestDraft.content.slice(0, 600));
    // 没有草稿就回退到订单需求
    if (!parts.length && order.requirements) parts.push(order.requirements.slice(0, 600));

    if (!parts.length) {
      return res.status(400).json({ error: "尚无草稿或订单需求可作为生图依据,请手动描述封面内容" });
    }

    description = parts.join("\n\n");
  }

  try {
    // When generating multiple images, split content into distinct segments
    // so each cover image depicts a different part of the article.
    let descriptions;
    if (desiredCount > 1) {
      // Extract title separately for better splitting
      const titleMatch = description.match(/^标题:(.+?)(?:\n|$)/);
      const title = titleMatch ? titleMatch[1].trim() : "";
      const body = titleMatch ? description.slice(titleMatch[0].length).trim() : description;
      // Pass bot's style doc so Qwen can follow the CONTENT template format
      const styleDoc = getBotImageStyle(order.bot_id);
      try {
        descriptions = await splitContentForImages(title, body, desiredCount, styleDoc);
      } catch (err) {
        console.warn(`段落划分失败,回退到整段生图: ${err.message}`);
        descriptions = Array(desiredCount).fill(description);
      }
    } else {
      descriptions = [description];
    }

    const insertStmt = db.prepare(
      "INSERT INTO order_materials (order_id, file_name, file_path, file_type, file_size, sort_order) VALUES (?, ?, ?, ?, ?, ?)"
    );
    let nextSort = db
      .prepare("SELECT COALESCE(MAX(sort_order), 0) AS max FROM order_materials WHERE order_id = ?")
      .get(order.id).max;

    const savedFiles = [];
    let lastOutputDir = null;

    for (let i = 0; i < descriptions.length; i += 1) {
      const result = await generateCoverImage(order.bot_id, descriptions[i]);
      lastOutputDir = result.outputDir || lastOutputDir;

      // Collect the files this call produced. Prefer result.files; fall back
      // to scanning outputDir when the MCP tool returns an empty list but
      // did write files to disk.
      const batch = [...(result.files || [])];
      if (batch.length === 0 && result.outputDir) {
        try {
          const dirFiles = fs
            .readdirSync(result.outputDir)
            .filter((fileName) => fileName.endsWith(".png") || fileName.endsWith(".jpg"))
            .sort();
          for (const fileName of dirFiles) {
            batch.push(path.join(result.outputDir, fileName));
          }
        } catch {}
      }

      // Per billing rule: one MCP call = one image, even though banana2 may
      // return 2 files. Take the first one that exists on disk and isn't
      // already saved, then discard the rest from this call.
      let pickedForThisCall = null;
      for (const filePath of batch) {
        if (!fs.existsSync(filePath)) continue;
        if (savedFiles.some((f) => f.file_path === filePath)) continue;
        pickedForThisCall = filePath;
        break;
      }

      if (!pickedForThisCall) {
        // No usable file this round — bail instead of looping forever.
        break;
      }

      const stat = fs.statSync(pickedForThisCall);
      const fileName = `cover_${path.basename(pickedForThisCall)}`;
      nextSort += 1;
      const dbResult = insertStmt.run(order.id, fileName, pickedForThisCall, "image/png", stat.size, nextSort);
      savedFiles.push({
        id: dbResult.lastInsertRowid,
        file_name: fileName,
        file_path: pickedForThisCall,
        file_size: stat.size,
      });
    }

    if (savedFiles.length === 0) {
      return res.status(500).json({
        error: "图片生成完成但未产出文件,请检查 bot 画风配置或稍后重试",
      });
    }
    res.json({ success: true, output_dir: lastOutputDir, files: savedFiles });
  } catch (err) {
    console.error(`Cover generation failed for order ${order.id}:`, err);
    res.status(500).json({ error: err.message });
  }
});

// POST /api/orders/:id/refine - iterate on the order's draft by sending the bot
// a new instruction. Each successful call creates a NEW draft version (V1, V2, ...).
// This is the single channel through which clients interact with the bot —
// there is no free-form chat. The bot must always emit a JSON draft contract.
//
// Uses a per-order session (agent:<bot>:commercial:order:<orderId>) so the bot's
// context does not leak between different orders of the same client.
// Quota (client_bot_chat_quota) is shared across all of a client's orders for
// a given bot; charged only on successful refinement.
router.post("/:id/refine", requireAuth, async (req, res) => {
  const rawInstruction = typeof req.body?.instruction === "string" ? req.body.instruction.trim() : "";
  if (!rawInstruction) {
    return res.status(400).json({ error: "请输入需求或修改意见" });
  }
  if (rawInstruction.length > 4000) {
    return res.status(400).json({ error: "单次指令过长(上限 4000 字)" });
  }

  const db = getDb();
  const order = db
    .prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?")
    .get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const blockedStatuses = [
    "awaiting_publish_review",
    "publishing",
    "published",
    "cancelled",
    "rejected",
    "failed",
  ];
  if (blockedStatuses.includes(order.status)) {
    return res.status(400).json({ error: `当前状态 (${order.status}) 不可继续生成草稿` });
  }

  // Quota check — charged only on success.
  db.prepare(
    "INSERT OR IGNORE INTO client_bot_chat_quota (client_id, bot_id) VALUES (?, ?)"
  ).run(req.clientId, order.bot_id);
  const quota = db
    .prepare(
      "SELECT used_count, max_count FROM client_bot_chat_quota WHERE client_id = ? AND bot_id = ?"
    )
    .get(req.clientId, order.bot_id);
  if (quota.used_count >= quota.max_count) {
    return res.status(429).json({
      error: `与 ${order.bot_id} 的对话次数已达上限 (${quota.max_count}),请联系研究部`,
      quota: { used: quota.used_count, max: quota.max_count },
    });
  }

  // On the very first refine turn, the client has nothing in order.requirements
  // yet (the simplified OrderCreate page skips that field). Treat the first
  // instruction as the "background brief" so future turns still get stable
  // context in the 【客户要求】 section even after session memory churns.
  let effectiveOrder = order;
  if (!order.requirements || !order.requirements.trim()) {
    db.prepare(
      "UPDATE orders SET requirements = ?, updated_at = datetime('now') WHERE id = ?"
    ).run(rawInstruction, order.id);
    effectiveOrder = { ...order, requirements: rawInstruction };
  }

  // Per-order session: context does not leak across orders. Session key format
  // is required by openclaw gateway — must start with `agent:<agentId>:`.
  const sessionId = `agent:${order.bot_id}:commercial:order:${order.id}`;

  // ---- Shared "commit draft after bot returns" logic ------------------------
  // Takes a raw draft object from the bot, charges quota, inserts a new draft
  // row, advances order status, and returns the success payload (same shape
  // for both JSON and SSE modes).
  const commitDraft = (draft) => {
    db.prepare(
      `UPDATE client_bot_chat_quota
       SET used_count = used_count + 1,
           last_used_at = datetime('now'),
           updated_at = datetime('now')
       WHERE client_id = ? AND bot_id = ?`
    ).run(req.clientId, order.bot_id);

    const versionRow = db
      .prepare("SELECT COALESCE(MAX(version), 0) AS max_v FROM drafts WHERE order_id = ?")
      .get(order.id);
    const nextVersion = (versionRow?.max_v || 0) + 1;

    const draftId = uuidv4();
    db.prepare(
      `INSERT INTO drafts (id, order_id, version, title, content, card_text, tags, image_style, status, revision_note, generated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ready', ?, datetime('now'))`
    ).run(
      draftId,
      order.id,
      nextVersion,
      draft.title || "",
      draft.content || "",
      draft.card_text || "",
      JSON.stringify(draft.tags || []),
      draft.image_style || "基础",
      rawInstruction
    );

    db.prepare(
      `UPDATE draft_generation_requests
       SET status = 'superseded', updated_at = datetime('now')
       WHERE order_id = ? AND status IN ('pending_review', 'approved', 'generating')`
    ).run(order.id);

    db.prepare("UPDATE orders SET status = 'draft_ready', updated_at = datetime('now') WHERE id = ?").run(order.id);

    return {
      success: true,
      draft: {
        id: draftId,
        version: nextVersion,
        title: draft.title || "",
        content: draft.content || "",
        card_text: draft.card_text || "",
        tags: draft.tags || [],
        image_style: draft.image_style || "基础",
        status: "ready",
        revision_note: rawInstruction,
        generated_at: new Date().toISOString(),
      },
      quota: { used: quota.used_count + 1, max: quota.max_count },
    };
  };

  // ---- SSE branch: stream live tool-call events to the client ---------------
  // Triggered when the client sends `Accept: text/event-stream`. The response
  // is a long-lived event stream terminated by a `done` or `error` event.
  const acceptsSse = (req.headers.accept || "").includes("text/event-stream");
  if (acceptsSse) {
    res.writeHead(200, {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    });
    // Flush headers immediately so EventSource/fetch sees them right away.
    if (typeof res.flushHeaders === "function") res.flushHeaders();

    // Client disconnect flag — set via req.on("close") below. Declared here
    // so sendEvent's closure captures it.
    let clientClosed = false;

    let writeCount = 0;
    const sendEvent = (type, data) => {
      try {
        const payload = `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`;
        const ok = res.write(payload);
        writeCount++;
        // stderr = line-buffered, so we see events live even when stdout is
        // piped to a log file.
        console.error(`[sse] wrote ${type} (${payload.length}B) total=${writeCount} ok=${ok} writable=${res.writable} destroyed=${res.destroyed} clientClosed=${clientClosed}`);
      } catch (err) {
        console.error("[sse] write failed:", err.message);
      }
    };

    // Heartbeat every 15s to keep proxies from closing idle connections.
    const heartbeat = setInterval(() => {
      try { res.write(`: hb\n\n`); } catch {}
    }, 15000);

    // Client disconnect = fire-and-forget on our side. The openclaw agent
    // subprocess keeps running (detached); commitDraft still runs when it
    // finishes, so the client can refresh the page later and see the draft.
    //
    // IMPORTANT: listen on `res.on("close")`, NOT `req.on("close")`.
    // req's `close` fires when the request body is fully consumed (which
    // happens immediately after bodyParser runs), not when the TCP connection
    // drops. That would set clientClosed=true right away and drop every
    // tool_use event in the onEvent callback below.
    res.on("close", () => {
      clientClosed = true;
      console.error(`[sse] res close fired, writable=${res.writable} destroyed=${res.destroyed}`);
    });

    sendEvent("start", { order_id: order.id, session_id: sessionId });

    const streamResult = await refineDraftViaChatStreaming(effectiveOrder, sessionId, rawInstruction, {
      onEvent: (evt) => {
        if (clientClosed) return;
        // Only forward tool_use for now. Extend here if we want toolResult too.
        if (evt?.type === "tool_use") sendEvent("tool_use", evt);
      },
    });

    clearInterval(heartbeat);

    if (streamResult.error) {
      sendEvent("error", {
        error: streamResult.error,
        quota: { used: quota.used_count, max: quota.max_count },
      });
      try { res.end(); } catch {}
      return;
    }

    const payload = commitDraft(streamResult.draft);
    sendEvent("done", payload);
    try { res.end(); } catch {}
    return;
  }

  // ---- Non-SSE branch: original JSON request/response behavior --------------
  const result = await refineDraftViaChat(effectiveOrder, sessionId, rawInstruction);
  if (result.error) {
    return res.status(500).json({
      error: result.error,
      quota: { used: quota.used_count, max: quota.max_count },
    });
  }

  const payload = commitDraft(result.draft);
  res.json(payload);
});

// GET /api/orders/:id/refine/quota - read current quota for this order's bot
router.get("/:id/refine/quota", requireAuth, (req, res) => {
  const db = getDb();
  const order = db
    .prepare("SELECT bot_id FROM orders WHERE id = ? AND client_id = ?")
    .get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });

  const row = db
    .prepare(
      "SELECT used_count, max_count FROM client_bot_chat_quota WHERE client_id = ? AND bot_id = ?"
    )
    .get(req.clientId, order.bot_id);

  res.json({
    bot_id: order.bot_id,
    quota: row
      ? { used: row.used_count, max: row.max_count }
      : { used: 0, max: 50 }, // Matches DB schema default for new quotas.
  });
});

export default router;
