import { execSync } from "child_process";
import fs from "fs";
import path from "path";
import os from "os";
import { getDb } from "../db.js";
import { cleanupOrderArtifacts } from "./order-cleanup.js";
import * as tunnel from "../tunnel/client-api.js";

import { OPENCLAW_DIR } from "../paths.js";

const SUBMIT_SCRIPT = path.join(OPENCLAW_DIR, "workspace/skills/armor/xhs-op/submit-to-publisher.sh");
const QUEUE_ROOT = path.join(OPENCLAW_DIR, "workspace-sys1/publish-queue");

// Folder subdirs sys1 can move a publish entry into, and how the commercial
// order should react when it shows up there.
const QUEUE_STATE_TO_ORDER_STATUS = {
  pending: null,            // still being held — no change
  "pending-approval": null, // still being held — no change
  publishing: null,         // mid-publish — no change
  published: "published",
  done: "published",
  rejected: "approved",     // dashboard 打回 → client 可重新提交
  failed: "approved",       // publisher 失败 → client 可重新提交
};

async function findQueueFolderLocation(folderName) {
  if (!folderName) return null;

  if (tunnel.isConnected()) {
    const subs = Object.keys(QUEUE_STATE_TO_ORDER_STATUS).join(" ");
    const cmd = `for sub in ${subs}; do test -d "${QUEUE_ROOT}/$sub/${folderName}" && echo "$sub" && exit 0; done`;
    try {
      const res = await tunnel.exec("bash", ["-c", cmd], { timeout: 10000 });
      if (res.code === 0 && res.stdout?.trim()) return res.stdout.trim();
    } catch {}
    return null;
  }

  for (const sub of Object.keys(QUEUE_STATE_TO_ORDER_STATUS)) {
    try {
      if (fs.statSync(path.join(QUEUE_ROOT, sub, folderName)).isDirectory()) {
        return sub;
      }
    } catch {}
  }
  return null;
}

/**
 * Reconcile any orders stuck in `publishing` against the actual location of
 * their publish_folder in workspace-sys1/publish-queue. sys1 / the dashboard
 * can move folders between pending/rejected/published without telling us, so
 * commercial must poll to avoid orders being stuck in `publishing` forever.
 */
export async function reconcilePublishingOrders() {
  const db = getDb();
  const stuck = db
    .prepare(
      "SELECT id, publish_folder FROM orders WHERE status = 'publishing' AND publish_folder IS NOT NULL AND publish_folder != ''"
    )
    .all();

  let changed = 0;
  for (const order of stuck) {
    const loc = await findQueueFolderLocation(order.publish_folder);
    if (loc === null) {
      console.warn(
        `[publish-bridge] Reconcile: order ${order.id} folder "${order.publish_folder}" not found in any queue subdir — leaving as-is`
      );
      continue;
    }
    const nextStatus = QUEUE_STATE_TO_ORDER_STATUS[loc];
    if (!nextStatus) continue; // still in-flight

    db.prepare(
      "UPDATE orders SET status = ?, updated_at = datetime('now') WHERE id = ?"
    ).run(nextStatus, order.id);
    console.log(
      `[publish-bridge] Reconciled order ${order.id}: folder in "${loc}" → status=${nextStatus}`
    );
    // When a reconcile lands the order in a terminal state, sweep its
    // iteration scratch (draft-live, bot session). Other statuses (approved,
    // rejected) leave the scratch alone so the client can continue refining.
    if (nextStatus === "published") {
      try {
        cleanupOrderArtifacts(order.id);
      } catch (err) {
        console.error(`[publish-bridge] cleanup after published failed:`, err.message);
      }
    }
    changed++;
  }
  return changed;
}

function getOrderImagePaths(orderId) {
  const db = getDb();
  const materials = db.prepare(
    "SELECT file_path FROM order_materials WHERE order_id = ? AND file_type LIKE 'image/%' ORDER BY sort_order ASC, id ASC"
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
    if (tunnel.isConnected()) {
      const res = await tunnel.exec("bash", [SUBMIT_SCRIPT, ...args], { timeout: 30000 });
      if (res.error || res.code !== 0) {
        throw new Error(res.error || res.stderr || `exit ${res.code}`);
      }
      return (res.stdout || "").trim();
    }

    const escapedArgs = args.map((a) => `'${a.replace(/'/g, "'\\''")}'`).join(" ");
    const result = execSync(`bash ${SUBMIT_SCRIPT} ${escapedArgs}`, {
      encoding: "utf8",
      timeout: 30000,
      cwd: OPENCLAW_DIR,
    });

    return result.trim(); // Returns the folder name
  } finally {
    // Cleanup temp file
    try {
      fs.unlinkSync(bodyFile);
    } catch {}
  }
}
