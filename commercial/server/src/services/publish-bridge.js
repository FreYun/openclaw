import { execSync } from "child_process";
import fs from "fs";
import path from "path";
import os from "os";
import { getDb } from "../db.js";

const SUBMIT_SCRIPT = "/home/rooot/.openclaw/workspace/skills/xhs-op/submit-to-publisher.sh";

function getOrderImagePaths(orderId) {
  const db = getDb();
  const materials = db.prepare(
    "SELECT file_path FROM order_materials WHERE order_id = ? AND file_type LIKE 'image/%' ORDER BY id"
  ).all(orderId);

  return materials
    .map((m) => m.file_path)
    .filter((filePath) => {
      try {
        return fs.statSync(filePath).isFile();
      } catch {
        return false;
      }
    });
}

/**
 * Submit an approved order+draft to the existing publish queue
 * via submit-to-publisher.sh (same path all bots use).
 */
export async function submitToPublisher(order, draft) {
  const tags = JSON.parse(draft.tags || "[]");
  const imagePaths = order.content_type === "image" ? getOrderImagePaths(order.id) : [];

  // Write body content to temp file
  const bodyFile = path.join(os.tmpdir(), `commercial_body_${order.id}.txt`);
  const bodyContent = draft.card_text || draft.content;
  fs.writeFileSync(bodyFile, bodyContent, "utf8");

  try {
    // Build command arguments
    const args = [
      "-a", order.bot_id,
      "-t", draft.title,
      "-b", bodyFile,
      "-m", order.content_type || "text_to_image",
      "-r", "direct:commercial_system",
    ];

    if (tags.length > 0) {
      args.push("-T", tags.join(","));
    }

    if (order.content_type === "image") {
      if (imagePaths.length === 0) {
        throw new Error("图文发布缺少可用图片素材");
      }
      args.push("-i", imagePaths.join(","));
    }

    // For text_to_image, pass the below-image content
    if (order.content_type === "text_to_image" && draft.content) {
      args.push("-c", draft.content);
    }

    // Image style
    if (draft.image_style && draft.image_style !== "基础") {
      args.push("-s", draft.image_style);
    }

    // Schedule
    if (order.schedule_at) {
      args.push("-S", order.schedule_at);
    }

    // Execute the submit script
    const escapedArgs = args.map((a) => `'${a.replace(/'/g, "'\\''")}'`).join(" ");
    const result = execSync(`bash ${SUBMIT_SCRIPT} ${escapedArgs}`, {
      encoding: "utf8",
      timeout: 30000,
      cwd: "/home/rooot/.openclaw",
    });

    return result.trim(); // Returns the folder name
  } finally {
    // Cleanup temp file
    try {
      fs.unlinkSync(bodyFile);
    } catch {}
  }
}
