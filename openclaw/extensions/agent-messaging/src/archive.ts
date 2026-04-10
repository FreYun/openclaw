import { DatabaseSync } from "node:sqlite";
import type { AgentMessage } from "./types.js";

const DEFAULT_DB_PATH = "/home/rooot/.openclaw/data/messages.sqlite";

export interface MessageArchive {
  save(msg: AgentMessage): void;
  close(): void;
}

export function createArchive(dbPath = DEFAULT_DB_PATH): MessageArchive {
  const db = new DatabaseSync(dbPath);
  db.exec("PRAGMA journal_mode=WAL");
  db.exec("PRAGMA synchronous=NORMAL");

  db.exec(`
    CREATE TABLE IF NOT EXISTS messages (
      message_id TEXT PRIMARY KEY,
      "from" TEXT NOT NULL,
      "to" TEXT NOT NULL,
      content TEXT NOT NULL,
      type TEXT NOT NULL,
      trace TEXT,
      reply_to_message_id TEXT,
      metadata TEXT,
      created_at TEXT NOT NULL,
      status TEXT NOT NULL
    )
  `);
  db.exec('CREATE INDEX IF NOT EXISTS idx_messages_from ON messages("from")');
  db.exec('CREATE INDEX IF NOT EXISTS idx_messages_to ON messages("to")');
  db.exec("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)");

  const insertStmt = db.prepare(`
    INSERT OR IGNORE INTO messages
      (message_id, "from", "to", content, type, trace, reply_to_message_id, metadata, created_at, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  function save(msg: AgentMessage): void {
    insertStmt.run(
      msg.message_id,
      msg.from,
      msg.to,
      msg.content,
      msg.type,
      JSON.stringify(msg.trace),
      msg.reply_to_message_id ?? null,
      JSON.stringify(msg.metadata ?? {}),
      msg.created_at,
      msg.status,
    );
  }

  function close(): void {
    db.close();
  }

  return { save, close };
}
