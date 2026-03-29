export type MessageType = "request" | "reply" | "notify";
export type MessageStatus = "pending" | "delivered" | "failed";

export interface TraceEntry {
  agent: string;
  session_id?: string;
  /** Present only on the origin entry — the external channel to deliver back to */
  reply_channel?: string;
  /** Present only on the origin entry — the external target (e.g. "ou_xxx") */
  reply_to?: string;
  /** Present only on the origin entry — the bot account to deliver from */
  reply_account?: string;
}

export interface AgentMessage {
  message_id: string;
  from: string;
  to: string;
  content: string;
  type: MessageType;
  trace: TraceEntry[];
  reply_to_message_id?: string;
  /** Local file paths or URLs to send as media attachments */
  media?: string[];
  metadata?: Record<string, unknown>;
  created_at: string;
  status: MessageStatus;
}
