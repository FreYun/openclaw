import fs from "fs";
import path from "path";
import bcrypt from "bcryptjs";
import { fileURLToPath } from "url";
import { getDb } from "../db.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WHITE_LIST_PATH = path.resolve(__dirname, "../../../white_id.json");

/**
 * On server startup, read white_id.json and INSERT OR IGNORE each account
 * into the clients table. Accounts that already exist in the DB are left
 * untouched (we do NOT overwrite passwords — manually changed passwords via
 * admin flows survive restarts).
 *
 * This is idempotent — running it multiple times is safe.
 *
 * File schema:
 *   { "accounts": [ { "username", "password", "display_name", "company"? } ] }
 */
export function seedWhitelistAccounts() {
  if (!fs.existsSync(WHITE_LIST_PATH)) {
    console.log(`[whitelist-seed] ${WHITE_LIST_PATH} 不存在,跳过 seed`);
    return 0;
  }

  let config;
  try {
    config = JSON.parse(fs.readFileSync(WHITE_LIST_PATH, "utf8"));
  } catch (err) {
    console.error(`[whitelist-seed] 解析 white_id.json 失败:`, err.message);
    return 0;
  }

  const accounts = Array.isArray(config?.accounts) ? config.accounts : [];
  if (accounts.length === 0) return 0;

  const db = getDb();
  const selectStmt = db.prepare("SELECT id FROM clients WHERE username = ?");
  const insertStmt = db.prepare(
    "INSERT INTO clients (username, password_hash, display_name, company, phone) VALUES (?, ?, ?, ?, ?)"
  );

  let created = 0;
  for (const acc of accounts) {
    if (!acc?.username || !acc?.password) continue;
    if (selectStmt.get(acc.username)) continue;
    const hash = bcrypt.hashSync(acc.password, 10);
    insertStmt.run(
      acc.username,
      hash,
      acc.display_name || acc.username,
      acc.company || "",
      acc.phone || ""
    );
    created += 1;
  }

  if (created > 0) {
    console.log(`[whitelist-seed] 从 white_id.json seed 了 ${created} 个新账号`);
  }
  return created;
}
