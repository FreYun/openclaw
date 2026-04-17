import Database from "better-sqlite3";
import { fileURLToPath } from "url";
import path from "path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.resolve(__dirname, "../../commercial.sqlite");

let db;

export function getDb() {
  if (!db) {
    db = new Database(DB_PATH);
    db.pragma("journal_mode = WAL");
    db.pragma("foreign_keys = ON");
    migrate(db);
  }
  return db;
}

function migrate(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS clients (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      username      TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      display_name  TEXT NOT NULL,
      company       TEXT DEFAULT '',
      phone         TEXT DEFAULT '',
      status        TEXT NOT NULL DEFAULT 'active',
      created_at    TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS bot_profiles (
      bot_id        TEXT PRIMARY KEY,
      display_name  TEXT NOT NULL,
      avatar_path   TEXT,
      description   TEXT DEFAULT '',
      style_summary TEXT DEFAULT '',
      specialties   TEXT DEFAULT '[]',
      is_available  INTEGER NOT NULL DEFAULT 1,
      synced_at     TEXT
    );

    CREATE TABLE IF NOT EXISTS orders (
      id              TEXT PRIMARY KEY,
      client_id       INTEGER NOT NULL REFERENCES clients(id),
      bot_id          TEXT NOT NULL,
      status          TEXT NOT NULL DEFAULT 'pending',
      title           TEXT NOT NULL DEFAULT '',
      requirements    TEXT NOT NULL DEFAULT '',
      reference_links TEXT DEFAULT '[]',
      content_type    TEXT NOT NULL DEFAULT 'text_to_image',
      schedule_at     TEXT,
      publish_folder  TEXT,
      xhs_note_id     TEXT,
      max_revisions   INTEGER NOT NULL DEFAULT 3,
      created_at      TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_orders_client ON orders(client_id);
    CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
    CREATE INDEX IF NOT EXISTS idx_orders_bot    ON orders(bot_id);

    CREATE TABLE IF NOT EXISTS order_materials (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id    TEXT NOT NULL REFERENCES orders(id),
      file_name   TEXT NOT NULL,
      file_path   TEXT NOT NULL,
      file_type   TEXT NOT NULL,
      file_size   INTEGER NOT NULL,
      sort_order  INTEGER NOT NULL DEFAULT 0,
      uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_materials_order ON order_materials(order_id);

    CREATE TABLE IF NOT EXISTS drafts (
      id            TEXT PRIMARY KEY,
      order_id      TEXT NOT NULL REFERENCES orders(id),
      version       INTEGER NOT NULL DEFAULT 1,
      title         TEXT NOT NULL DEFAULT '',
      content       TEXT NOT NULL DEFAULT '',
      card_text     TEXT DEFAULT '',
      tags          TEXT DEFAULT '[]',
      image_style   TEXT DEFAULT '基础',
      status        TEXT NOT NULL DEFAULT 'pending',
      revision_note TEXT DEFAULT '',
      bot_session_id TEXT,
      generated_at  TEXT,
      reviewed_at   TEXT,
      created_at    TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_drafts_order ON drafts(order_id);

    CREATE TABLE IF NOT EXISTS draft_generation_requests (
      id              TEXT PRIMARY KEY,
      order_id        TEXT NOT NULL REFERENCES orders(id),
      client_id       INTEGER NOT NULL REFERENCES clients(id),
      bot_id          TEXT NOT NULL,
      version         INTEGER NOT NULL,
      status          TEXT NOT NULL DEFAULT 'pending_review',
      revision_note   TEXT DEFAULT '',
      reviewer_note   TEXT DEFAULT '',
      snapshot_path   TEXT NOT NULL,
      result_draft_id TEXT,
      approved_at     TEXT,
      reviewed_at     TEXT,
      created_at      TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_draft_generation_requests_order
      ON draft_generation_requests(order_id);
    CREATE INDEX IF NOT EXISTS idx_draft_generation_requests_status
      ON draft_generation_requests(status);

    CREATE TABLE IF NOT EXISTS client_bot_chat_quota (
      client_id    INTEGER NOT NULL REFERENCES clients(id),
      bot_id       TEXT NOT NULL,
      used_count   INTEGER NOT NULL DEFAULT 0,
      max_count    INTEGER NOT NULL DEFAULT 50,
      last_used_at TEXT,
      created_at   TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
      PRIMARY KEY (client_id, bot_id)
    );
  `);

  // Additive migrations for columns that were introduced after the
  // initial schema was shipped.
  const materialCols = db.prepare(`PRAGMA table_info(order_materials)`).all();
  if (!materialCols.some((c) => c.name === "sort_order")) {
    db.exec(`ALTER TABLE order_materials ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0`);
    // Backfill existing rows: use id as the initial sort_order so the
    // current upload order is preserved until someone drags to reorder.
    db.exec(`UPDATE order_materials SET sort_order = id WHERE sort_order = 0`);
  }
}

export default getDb;
