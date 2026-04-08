import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const QUEUE_BASE = path.resolve(__dirname, "../../../review-queue/draft-generation");
const QUEUE_STATUSES = [
  "pending_review",
  "approved",
  "rejected",
  "generating",
  "completed",
  "failed",
];

function ensureQueueDirs() {
  for (const status of QUEUE_STATUSES) {
    fs.mkdirSync(path.join(QUEUE_BASE, status), { recursive: true });
  }
}

function writeSnapshot(snapshotPath, payload) {
  fs.writeFileSync(snapshotPath, JSON.stringify(payload, null, 2), "utf8");
}

export function getDraftReviewQueueBase() {
  ensureQueueDirs();
  return QUEUE_BASE;
}

export function readDraftReviewSnapshot(snapshotPath) {
  if (!snapshotPath) return null;
  return JSON.parse(fs.readFileSync(snapshotPath, "utf8"));
}

export function createDraftReviewSnapshot(requestId, payload) {
  ensureQueueDirs();
  const createdAt = new Date().toISOString();
  const snapshot = {
    ...payload,
    request_id: requestId,
    status: "pending_review",
    created_at: createdAt,
    updated_at: createdAt,
  };
  const snapshotPath = path.join(QUEUE_BASE, "pending_review", `${requestId}.json`);
  writeSnapshot(snapshotPath, snapshot);
  return { snapshotPath, snapshot };
}

export function moveDraftReviewSnapshot(requestId, currentPath, nextStatus, patch = {}) {
  ensureQueueDirs();
  const current = currentPath && fs.existsSync(currentPath) ? readDraftReviewSnapshot(currentPath) : {};
  const nextPath = path.join(QUEUE_BASE, nextStatus, `${requestId}.json`);
  const nextSnapshot = {
    ...current,
    ...patch,
    request_id: requestId,
    status: nextStatus,
    updated_at: new Date().toISOString(),
  };

  writeSnapshot(nextPath, nextSnapshot);
  if (currentPath && currentPath !== nextPath && fs.existsSync(currentPath)) {
    fs.unlinkSync(currentPath);
  }

  return nextPath;
}
