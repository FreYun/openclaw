import Redis from "ioredis";
import type { AgentMessage, MessageStatus } from "./types.js";

const PREFIX = "agentmsg";
const TTL_SECONDS = 7 * 24 * 3600; // 7 days
const STREAM_MAXLEN = 1000;

export interface MessageStore {
  save(msg: AgentMessage): Promise<void>;
  get(messageId: string): Promise<AgentMessage | null>;
  updateStatus(messageId: string, status: MessageStatus): Promise<void>;
  listInbox(agentId: string, limit?: number): Promise<AgentMessage[]>;
  listConversation(agentA: string, agentB: string, limit?: number): Promise<AgentMessage[]>;
  disconnect(): Promise<void>;
}

export function createStore(redisUrl = "redis://127.0.0.1:6379"): MessageStore {
  const redis = new Redis(redisUrl, { lazyConnect: false, maxRetriesPerRequest: 3 });

  function detailKey(id: string) {
    return `${PREFIX}:detail:${id}`;
  }

  function convStreamKey(a: string, b: string): string {
    const [lo, hi] = [a, b].sort();
    return `${PREFIX}:conv:${lo}:${hi}`;
  }

  async function save(msg: AgentMessage): Promise<void> {
    const key = detailKey(msg.message_id);
    const pipeline = redis.pipeline();
    pipeline.hset(key, {
      message_id: msg.message_id,
      from: msg.from,
      to: msg.to,
      content: msg.content,
      type: msg.type,
      trace: JSON.stringify(msg.trace),
      reply_to_message_id: msg.reply_to_message_id ?? "",
      metadata: JSON.stringify(msg.metadata ?? {}),
      created_at: msg.created_at,
      status: msg.status,
    });
    pipeline.expire(key, TTL_SECONDS);
    // Append to recipient inbox and sender outbox streams
    pipeline.xadd(
      `${PREFIX}:inbox:${msg.to}`,
      "MAXLEN",
      "~",
      String(STREAM_MAXLEN),
      "*",
      "message_id",
      msg.message_id,
    );
    pipeline.xadd(
      `${PREFIX}:outbox:${msg.from}`,
      "MAXLEN",
      "~",
      String(STREAM_MAXLEN),
      "*",
      "message_id",
      msg.message_id,
    );
    // Append to per-pair conversation stream for shared history
    pipeline.xadd(
      convStreamKey(msg.from, msg.to),
      "MAXLEN",
      "~",
      String(STREAM_MAXLEN),
      "*",
      "message_id",
      msg.message_id,
    );
    await pipeline.exec();
  }

  async function get(messageId: string): Promise<AgentMessage | null> {
    const data = await redis.hgetall(detailKey(messageId));
    if (!data || !data.message_id) return null;
    return {
      message_id: data.message_id,
      from: data.from,
      to: data.to,
      content: data.content,
      type: data.type as AgentMessage["type"],
      trace: JSON.parse(data.trace),
      reply_to_message_id: data.reply_to_message_id || undefined,
      metadata: JSON.parse(data.metadata || "{}"),
      created_at: data.created_at,
      status: data.status as AgentMessage["status"],
    };
  }

  async function updateStatus(messageId: string, status: MessageStatus): Promise<void> {
    await redis.hset(detailKey(messageId), "status", status);
  }

  async function listInbox(agentId: string, limit = 20): Promise<AgentMessage[]> {
    const entries = await redis.xrevrange(
      `${PREFIX}:inbox:${agentId}`,
      "+",
      "-",
      "COUNT",
      limit,
    );
    const messages: AgentMessage[] = [];
    for (const [, fields] of entries) {
      // fields = ["message_id", "msg_xxx"]
      const msgId = fields[1];
      if (msgId) {
        const msg = await get(msgId);
        if (msg) messages.push(msg);
      }
    }
    return messages;
  }

  async function listConversation(agentA: string, agentB: string, limit = 10): Promise<AgentMessage[]> {
    const entries = await redis.xrevrange(
      convStreamKey(agentA, agentB),
      "+",
      "-",
      "COUNT",
      limit,
    );
    const messages: AgentMessage[] = [];
    for (const [, fields] of entries) {
      const msgId = fields[1];
      if (msgId) {
        const msg = await get(msgId);
        if (msg) messages.push(msg);
      }
    }
    return messages.reverse(); // chronological order
  }

  async function disconnect(): Promise<void> {
    await redis.quit();
  }

  return { save, get, updateStatus, listInbox, listConversation, disconnect };
}
