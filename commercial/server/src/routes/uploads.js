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

// POST /api/orders/:id/materials - upload materials
router.post("/:id/materials", requireAuth, requireOwnedOrder, upload.array("files", MAX_FILES), async (req, res) => {
  const db = getDb();
  const order = req.order;

  const insertStmt = db.prepare(
    "INSERT INTO order_materials (order_id, file_name, file_path, file_type, file_size) VALUES (?, ?, ?, ?, ?)"
  );

  const results = [];
  let hasDocxImages = false;

  for (const file of req.files) {
    const fileName = decodeFilename(file.originalname);
    const isDocx = file.mimetype === "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

    if (isDocx) {
      // Parse DOCX: extract text + images
      try {
        const outputDir = path.join(UPLOADS_BASE, req.params.id);
        const parsed = await parseDocx(file.path, outputDir);

        // Save extracted text as a material
        if (parsed.text) {
          const textPath = path.join(outputDir, "materials", `${Date.now()}_docx_content.txt`);
          fs.writeFileSync(textPath, parsed.text, "utf8");
          const textResult = insertStmt.run(order.id, `${fileName} (文字内容)`, textPath, "text/plain", Buffer.byteLength(parsed.text));
          results.push({
            id: textResult.lastInsertRowid,
            file_name: `${fileName} (文字内容)`,
            file_type: "text/plain",
            file_size: Buffer.byteLength(parsed.text),
          });
        }

        // Save extracted images as materials
        for (const img of parsed.images) {
          const imgResult = insertStmt.run(order.id, img.fileName, img.path, img.contentType, fs.statSync(img.path).size);
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
        const result = insertStmt.run(order.id, fileName, file.path, file.mimetype, file.size);
        results.push({ id: result.lastInsertRowid, file_name: fileName, file_type: file.mimetype, file_size: file.size });
      }
    } else {
      // Regular file
      const result = insertStmt.run(order.id, fileName, file.path, file.mimetype, file.size);
      results.push({ id: result.lastInsertRowid, file_name: fileName, file_type: file.mimetype, file_size: file.size });
    }
  }

  // Auto-switch to image mode if DOCX contained images
  let modeChanged = false;
  if (hasDocxImages && order.content_type !== "image") {
    db.prepare("UPDATE orders SET content_type = 'image', updated_at = datetime('now') WHERE id = ?").run(order.id);
    modeChanged = true;
  }

  res.status(201).json({ materials: results, mode_changed: modeChanged, content_type: modeChanged ? "image" : order.content_type });
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

  res.download(material.file_path, material.file_name);
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
