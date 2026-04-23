import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { getDb } from "../db.js";
import { OPENCLAW_DIR } from "../paths.js";
import * as tunnel from "../tunnel/client-api.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DRAFT_LIVE_DIR = path.resolve(__dirname, "../../../draft-live");
const AGENTS_DIR = path.join(OPENCLAW_DIR, "agents");

// Orders in these states are done with refinement and can have transient
// iteration artifacts safely swept. DB rows and uploaded materials are kept
// for audit — only iteration scratch is deleted.
const TERMINAL_STATES = new Set(["published", "cancelled"]);

/**
 * Sweep transient artifacts for one order. Idempotent — safe to call multiple
 * times, missing files are silently skipped.
 *
 * Cleans:
 *   1. draft-live/<orderId>.json             (refine iteration scratch)
 *   2. agents/<botId>/sessions/<sid>.jsonl   (per-order bot session transcript)
 *   3. agents/<botId>/sessions/sessions.json (remove the sid entry if present)
 *
 * Does NOT touch:
 *   - DB rows (orders / drafts / order_materials / draft_generation_requests)
 *   - uploads/orders/<orderId>/               (raw client-uploaded materials)
 *   - draft-review-snapshots/                 (research-review audit trail)
 */
export async function cleanupOrderArtifacts(orderId) {
  const db = getDb();
  const order = db.prepare("SELECT id, bot_id, status FROM orders WHERE id = ?").get(orderId);
  if (!order) return { ok: false, reason: "order not found" };

  const removed = [];

  // 1. draft-live snapshot (always local to commercial/)
  const liveDraftPath = path.join(DRAFT_LIVE_DIR, `${orderId}.json`);
  if (fs.existsSync(liveDraftPath)) {
    try {
      fs.unlinkSync(liveDraftPath);
      removed.push("draft-live");
    } catch (err) {
      console.error(`[order-cleanup] Failed to remove ${liveDraftPath}:`, err.message);
    }
  }

  // 2 + 3. Gateway session file + sessions.json registry entry.
  //   agents/<bot_id>/sessions/<uuid>.jsonl
  //   agents/<bot_id>/sessions/sessions.json  (maps session-id → uuid)
  const sessionId = `agent:${order.bot_id}:commercial:order:${orderId}`;
  const sessionsDir = path.join(AGENTS_DIR, order.bot_id, "sessions");
  const registryPath = path.join(sessionsDir, "sessions.json");

  try {
    const registryText = tunnel.isConnected()
      ? (await tunnel.readFile(registryPath)).content
      : (fs.existsSync(registryPath) ? fs.readFileSync(registryPath, "utf8") : null);

    if (!registryText) {
      if (removed.length > 0) console.log(`[order-cleanup] Swept order ${orderId}: ${removed.join(", ")}`);
      return { ok: true, removed };
    }

    const registry = JSON.parse(registryText);
    let sessionUuid = null;
    if (registry && typeof registry === "object") {
      if (registry[sessionId]?.id) {
        sessionUuid = registry[sessionId].id;
        delete registry[sessionId];
      }
      if (!sessionUuid && Array.isArray(registry.sessions)) {
        const idx = registry.sessions.findIndex((s) => s?.sessionId === sessionId);
        if (idx !== -1) {
          sessionUuid = registry.sessions[idx].id;
          registry.sessions.splice(idx, 1);
        }
      }
    }

    if (sessionUuid) {
      const jsonlPath = path.join(sessionsDir, `${sessionUuid}.jsonl`);
      const updatedRegistry = JSON.stringify(registry, null, 2);

      if (tunnel.isConnected()) {
        await tunnel.exec("bash", ["-c",
          `rm -f '${jsonlPath}' && cat > '${registryPath}' << 'REGISTRY_EOF'\n${updatedRegistry}\nREGISTRY_EOF`
        ], { timeout: 10000 });
      } else {
        try { fs.unlinkSync(jsonlPath); } catch {}
        fs.writeFileSync(registryPath, updatedRegistry);
      }
      removed.push(`session:${sessionUuid.slice(0, 8)}`);
    }
  } catch (err) {
    console.error(`[order-cleanup] Failed to clean sessions for ${registryPath}:`, err.message);
  }

  if (removed.length > 0) {
    console.log(`[order-cleanup] Swept order ${orderId}: ${removed.join(", ")}`);
  }
  return { ok: true, removed };
}

/**
 * Periodic safety net: find any terminal orders that still have a draft-live
 * snapshot on disk and sweep them. Handles races where the transition hook
 * might have been missed (server crash mid-transition, manual DB edit, etc).
 */
export async function sweepStaleArtifacts() {
  if (!fs.existsSync(DRAFT_LIVE_DIR)) return 0;

  const db = getDb();
  let files;
  try {
    files = fs.readdirSync(DRAFT_LIVE_DIR).filter((f) => f.endsWith(".json"));
  } catch {
    return 0;
  }

  let swept = 0;
  for (const f of files) {
    const orderId = f.replace(/\.json$/, "");
    const row = db.prepare("SELECT status FROM orders WHERE id = ?").get(orderId);
    if (!row) {
      // Orphan snapshot — order no longer exists.
      try {
        fs.unlinkSync(path.join(DRAFT_LIVE_DIR, f));
        swept += 1;
      } catch {}
      continue;
    }
    if (TERMINAL_STATES.has(row.status)) {
      await cleanupOrderArtifacts(orderId);
      swept += 1;
    }
  }
  return swept;
}
