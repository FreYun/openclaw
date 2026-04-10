#!/usr/bin/env node
/**
 * One-time migration: read all agentmsg:detail:* hashes from Redis
 * and insert them into the SQLite archive.
 *
 * Usage: node --experimental-sqlite migrate-to-sqlite.ts
 */
import Redis from "ioredis";
import { createArchive } from "./archive.js";

const redis = new Redis("redis://127.0.0.1:6379", { lazyConnect: false, maxRetriesPerRequest: 3 });
const archive = createArchive();

async function migrate() {
  const keys: string[] = [];
  let cursor = "0";
  // SCAN for all detail keys
  do {
    const [next, batch] = await redis.scan(cursor, "MATCH", "agentmsg:detail:*", "COUNT", 200);
    cursor = next;
    keys.push(...batch);
  } while (cursor !== "0");

  console.log(`Found ${keys.length} message keys in Redis`);

  let saved = 0;
  let skipped = 0;
  for (const key of keys) {
    const data = await redis.hgetall(key);
    if (!data || !data.message_id) {
      skipped++;
      continue;
    }
    try {
      archive.save({
        message_id: data.message_id,
        from: data.from,
        to: data.to,
        content: data.content,
        type: data.type as "request" | "reply" | "notify",
        trace: JSON.parse(data.trace || "[]"),
        reply_to_message_id: data.reply_to_message_id || undefined,
        metadata: JSON.parse(data.metadata || "{}"),
        created_at: data.created_at,
        status: data.status as "pending" | "delivered" | "failed",
      });
      saved++;
    } catch (err) {
      console.error(`Failed to save ${data.message_id}:`, err);
    }
  }

  console.log(`Migration complete: ${saved} saved, ${skipped} skipped`);
  archive.close();
  await redis.quit();
}

migrate().catch((err) => {
  console.error("Migration failed:", err);
  process.exit(1);
});
