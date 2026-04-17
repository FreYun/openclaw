import { Router } from "express";
import multer from "multer";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";
import { getDb } from "../db.js";
import { requireAuth } from "../auth.js";
import { parseDocx } from "../services/docx-parser.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const UPLOADS_BASE = path.resolve(__dirname, "../../../uploads/orders");

const ALLOWED_TYPES = {
  "image/jpeg": ".jpg",
  "image/png": ".png",
  "image/webp": ".webp",
  "text/plain": ".txt",
  "text/markdown": ".md",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
};
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB (docx can be larger)
const MAX_FILES = 10;

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const dir = path.join(UPLOADS_BASE, req.params.id, "materials");
    fs.mkdirSync(dir, { recursive: true });
    cb(null, dir);
  },
  filename: (req, file, cb) => {
    cb(null, `${Date.now()}_${file.originalname}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: MAX_FILE_SIZE, files: MAX_FILES },
  fileFilter: (req, file, cb) => {
    if (ALLOWED_TYPES[file.mimetype]) {
      cb(null, true);
    } else {
      cb(new Error(`不支持的文件类型: ${file.mimetype}`));
    }
  },
});

const router = Router();

function decodeFilename(originalname) {
  try {
    return Buffer.from(originalname, "latin1").toString("utf8");
  } catch {
    return originalname;
  }
}

function requireOwnedOrder(req, res, next) {
  const db = getDb();
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND client_id = ?").get(req.params.id, req.clientId);
  if (!order) return res.status(404).json({ error: "订单不存在" });
  req.order = order;
  next();
}

function sendMaterialFile(res, material, inline = false) {
  let stat;
  try {
    stat = fs.statSync(material.file_path);
  } catch (err) {
    if (err?.code === "ENOENT") {
      return res.status(404).json({ error: "素材文件不存在" });
    }
    return res.status(500).json({ error: "素材读取失败" });
  }

  res.setHeader("Content-Type", material.file_type || "application/octet-stream");
  res.setHeader("Content-Length", stat.size);
  if (!inline) {
    res.attachment(material.file_name);
  }

  const stream = fs.createReadStream(material.file_path);
  stream.on("error", () => {
    if (!res.headersSent) {
      res.status(500).json({ error: "素材读取失败" });
    } else {
      res.destroy();
    }
  });
  stream.pipe(res);
}

// POST /api/orders/:id/materials - upload materials
router.post("/:id/materials", requireAuth, requireOwnedOrder, upload.array("files", MAX_FILES), async (req, res) => {
  const db = getDb();
  const order = req.order;

  // New uploads get appended at the end of the current order (max sort_order + 1).
  // We snapshot the base once per request and increment locally so multiple files
  // in the same upload keep their relative order.
  const maxSort = db
    .prepare("SELECT COALESCE(MAX(sort_order), 0) AS max FROM order_materials WHERE order_id = ?")
    .get(order.id).max;
  let nextSort = maxSort;
  const insertStmt = db.prepare(
    "INSERT INTO order_materials (order_id, file_name, file_path, file_type, file_size, sort_order) VALUES (?, ?, ?, ?, ?, ?)"
  );
  const insertMaterial = (orderId, fileName, filePath, fileType, fileSize) => {
    nextSort += 1;
    return insertStmt.run(orderId, fileName, filePath, fileType, fileSize, nextSort);
  };

  const results = [];
  let hasDocxImages = false;
  // DOCX 文字优先进 order.requirements:
  //   - 若 requirements 为空,直接写进去
  //   - 若已有内容,追加在已有内容后
  // (历史行为是把文字存成单独的 text material — 新流程不再这样做)
  let requirementsAppend = "";

  for (const file of req.files) {
    const fileName = decodeFilename(file.originalname);
    const isDocx = file.mimetype === "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

    if (isDocx) {
      // Parse DOCX: extract text + images
      try {
        const outputDir = path.join(UPLOADS_BASE, req.params.id);
        const parsed = await parseDocx(file.path, outputDir);

        if (parsed.text) {
          // Accumulate across all docx files uploaded in this request.
          requirementsAppend += (requirementsAppend ? "\n\n---\n\n" : "") + parsed.text;
        }

        // Save extracted images as materials
        for (const img of parsed.images) {
          const imgResult = insertMaterial(order.id, img.fileName, img.path, img.contentType, fs.statSync(img.path).size);
          results.push({
            id: imgResult.lastInsertRowid,
            file_name: img.fileName,
            file_type: img.contentType,
            file_size: fs.statSync(img.path).size,
          });
        }

        if (parsed.hasImages) {
          hasDocxImages = true;
        }
      } catch (err) {
        console.error(`DOCX parse error:`, err);
        // Fallback: save the docx as-is
        const result = insertMaterial(order.id, fileName, file.path, file.mimetype, file.size);
        results.push({ id: result.lastInsertRowid, file_name: fileName, file_type: file.mimetype, file_size: file.size });
      }
    } else {
      // Regular file
      const result = insertMaterial(order.id, fileName, file.path, file.mimetype, file.size);
      results.push({ id: result.lastInsertRowid, file_name: fileName, file_type: file.mimetype, file_size: file.size });
    }
  }

  // Auto-switch to image mode if DOCX contained images
  let modeChanged = false;
  if (hasDocxImages && order.content_type !== "image") {
    db.prepare("UPDATE orders SET content_type = 'image', updated_at = datetime('now') WHERE id = ?").run(order.id);
    modeChanged = true;
  }

  // Merge extracted DOCX text into order.requirements.
  let requirementsUpdated = false;
  let newRequirements = order.requirements || "";
  if (requirementsAppend) {
    newRequirements = newRequirements
      ? `${newRequirements}\n\n---\n\n${requirementsAppend}`
      : requirementsAppend;
    db.prepare(
      "UPDATE orders SET requirements = ?, updated_at = datetime('now') WHERE id = ?"
    ).run(newRequirements, order.id);
    requirementsUpdated = true;
  }

  res.status(201).json({
    materials: results,
    mode_changed: modeChanged,
    content_type: modeChanged ? "image" : order.content_type,
    requirements_updated: requirementsUpdated,
    requirements: requirementsUpdated ? newRequirements : undefined,
  });
});

// PUT /api/orders/:id/materials/order - reorder materials
// Body: { ids: [mid1, mid2, ...] } — the new display order.
// The array must contain exactly the set of image-material ids of this order.
// Non-image materials keep their existing sort_order.
router.put("/:id/materials/order", requireAuth, requireOwnedOrder, (req, res) => {
  const db = getDb();
  const order = req.order;
  const { ids } = req.body || {};

  if (!Array.isArray(ids) || ids.length === 0) {
    return res.status(400).json({ error: "ids 必须是非空数组" });
  }

  const allMaterials = db
    .prepare("SELECT id, file_type FROM order_materials WHERE order_id = ?")
    .all(order.id);
  const imageIds = new Set(
    allMaterials.filter((m) => m.file_type.startsWith("image/")).map((m) => m.id)
  );

  // Validate: every id in the request must be an image material of this order,
  // and every image material of this order must be represented exactly once.
  const seen = new Set();
  for (const raw of ids) {
    const id = parseInt(raw, 10);
    if (!Number.isInteger(id) || !imageIds.has(id)) {
      return res.status(400).json({ error: `素材 ${raw} 不属于本订单或不是图片` });
    }
    if (seen.has(id)) {
      return res.status(400).json({ error: `素材 ${id} 在列表中重复` });
    }
    seen.add(id);
  }
  if (seen.size !== imageIds.size) {
    return res.status(400).json({ error: "必须提供所有图片素材的新顺序" });
  }

  // Non-image materials keep their position: we interleave them by keeping their
  // old sort_order offset, but it's simpler to just put them after the images.
  const updateStmt = db.prepare("UPDATE order_materials SET sort_order = ? WHERE id = ?");
  const tx = db.transaction(() => {
    let i = 1;
    for (const raw of ids) {
      updateStmt.run(i, parseInt(raw, 10));
      i += 1;
    }
    // Non-image materials come after all images.
    const nonImage = allMaterials
      .filter((m) => !m.file_type.startsWith("image/"))
      .map((m) => m.id)
      .sort((a, b) => a - b);
    for (const id of nonImage) {
      updateStmt.run(i, id);
      i += 1;
    }
  });
  tx();

  res.json({ success: true });
});

// DELETE /api/orders/:id/materials/:mid - delete material
router.delete("/:id/materials/:mid", requireAuth, requireOwnedOrder, (req, res) => {
  const db = getDb();
  const order = req.order;

  const material = db.prepare("SELECT * FROM order_materials WHERE id = ? AND order_id = ?").get(
    parseInt(req.params.mid),
    order.id
  );
  if (!material) return res.status(404).json({ error: "素材不存在" });

  try {
    fs.unlinkSync(material.file_path);
  } catch {}

  db.prepare("DELETE FROM order_materials WHERE id = ?").run(material.id);
  res.json({ success: true });
});

// GET /api/orders/:id/materials/:mid/download - download material
router.get("/:id/materials/:mid/download", requireAuth, requireOwnedOrder, (req, res) => {
  const db = getDb();
  const order = req.order;

  const material = db.prepare("SELECT * FROM order_materials WHERE id = ? AND order_id = ?").get(
    parseInt(req.params.mid),
    order.id
  );
  if (!material) return res.status(404).json({ error: "素材不存在" });

  if (material.file_type.startsWith("image/")) {
    return sendMaterialFile(res, material, true);
  }

  return sendMaterialFile(res, material, false);
});

// Error handling for multer
router.use((err, req, res, next) => {
  if (err instanceof multer.MulterError) {
    if (err.code === "LIMIT_FILE_SIZE") return res.status(400).json({ error: "文件大小超过10MB限制" });
    if (err.code === "LIMIT_FILE_COUNT") return res.status(400).json({ error: `最多上传${MAX_FILES}个文件` });
    return res.status(400).json({ error: err.message });
  }
  if (err) return res.status(400).json({ error: err.message });
  next();
});

export default router;
