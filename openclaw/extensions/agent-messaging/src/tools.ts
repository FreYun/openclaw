import { Type } from "@sinclair/typebox";
import { nanoid } from "nanoid";
import type { OpenClawPluginApi, OpenClawPluginToolContext } from "openclaw/plugin-sdk";
import { dispatchMessage } from "./dispatch.js";
import type { MessageStore } from "./store.js";
import { popTrace, resolveDirectDeliveryRoute, resolveReplyRoute } from "./trace.js";
import type { AgentMessage, TraceEntry } from "./types.js";

function json(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
    details: data,
  };
}

// Schema for a single trace entry (used in arrays)
const TraceEntrySchema = Type.Object({
  agent: Type.String({ description: "Agent ID of this trace hop" }),
  session_id: Type.Optional(Type.String({ description: "Session ID at this hop" })),
  reply_channel: Type.Optional(
    Type.String({ description: "External channel for origin entry (e.g. 'feishu')" }),
  ),
  reply_to: Type.Optional(
    Type.String({ description: "External target for origin entry (e.g. 'ou_xxx')" }),
  ),
  reply_account: Type.Optional(
    Type.String({ description: "Bot account for origin entry (e.g. 'bot7')" }),
  ),
});

function getKnownAgentIds(runtime: { config: { loadConfig: () => unknown } }): Set<string> {
  try {
    const cfg = runtime.config.loadConfig() as { agents?: { list?: Array<{ id?: string }> } };
    const list = cfg?.agents?.list;
    if (!Array.isArray(list)) return new Set(["main"]);
    const ids = list
      .map((e) => e?.id?.trim().toLowerCase())
      .filter((id): id is string => Boolean(id));
    return new Set(ids.length > 0 ? ids : ["main"]);
  } catch {
    return new Set(["main"]);
  }
}

export function registerMessagingTools(api: OpenClawPluginApi, store: MessageStore): void {
  const { runtime } = api;

  // Validate target agent exists
  const validateTarget = (to: string) => {
    const knownAgents = getKnownAgentIds(runtime);
    if (!knownAgents.has(to.trim().toLowerCase())) {
      return json({ error: `Unknown agent: "${to}". Known agents: ${[...knownAgents].join(", ")}` });
    }
    return null;
  };

  // ── send_message ──────────────────────────────────────────────────────
  api.registerTool(
    (ctx: OpenClawPluginToolContext) => ({
      name: "send_message",
      label: "Send Agent Message",
      description:
        "Send a message to another agent and wake it up. " +
        "The trace array carries routing context for reply chain.",
      parameters: Type.Object({
        to: Type.String({ description: "Target agent ID (e.g. 'mcp_publisher', 'bot7')" }),
        content: Type.String({ description: "Message content" }),
        trace: Type.Array(TraceEntrySchema, {
          description:
            "Trace chain. First entry should be your origin context " +
            "(agent, session_id, reply_channel, reply_to, reply_account)",
        }),
        metadata: Type.Optional(
          Type.Object({}, { additionalProperties: true, description: "Optional metadata" }),
        ),
      }),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        const { to, content, trace, metadata } = params as {
          to: string;
          content: string;
          trace: TraceEntry[];
          metadata?: Record<string, unknown>;
        };

        const rejected = validateTarget(to);
        if (rejected) return rejected;

        const msg: AgentMessage = {
          message_id: nanoid(),
          from: ctx.agentId ?? "unknown",
          to,
          content,
          type: "request",
          trace,
          metadata,
          created_at: new Date().toISOString(),
          status: "pending",
        };

        await store.save(msg);

        // Fire-and-forget: wake the target agent without blocking the caller
        dispatchMessage(
          runtime,
          { kind: "wake_agent", agent: to },
          msg.message_id,
          msg.from,
          content,
        ).then(
          (result) => store.updateStatus(msg.message_id, result.ok ? "delivered" : "failed"),
          () => store.updateStatus(msg.message_id, "failed"),
        );

        return json({
          message_id: msg.message_id,
          status: "sent",
        });
      },
    }),
    { name: "send_message" },
  );

  // ── reply_message ─────────────────────────────────────────────────────
  api.registerTool(
    (ctx: OpenClawPluginToolContext) => ({
      name: "reply_message",
      label: "Reply Agent Message",
      description:
        "Reply to a received message. ALWAYS delivers to the origin external user (e.g. feishu). " +
        "Set also_notify_agent=true to additionally wake the previous agent in the trace chain.",
      parameters: Type.Object({
        message_id: Type.String({ description: "The message_id of the message to reply to" }),
        content: Type.String({ description: "Reply content" }),
        also_notify_agent: Type.Optional(
          Type.Boolean({
            description:
              "If true, also wake the previous agent in the trace chain " +
              "in addition to delivering to the external user. Default: false.",
          }),
        ),
      }),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        const { message_id: origMsgId, content, also_notify_agent: alsoNotifyAgent } = params as {
          message_id: string;
          content: string;
          also_notify_agent?: boolean;
        };

        const original = await store.get(origMsgId);
        if (!original) {
          return json({ error: `Message not found: ${origMsgId}` });
        }

        if (original.trace.length === 0) {
          return json({ error: "Cannot reply: trace is empty (no route back)" });
        }

        // Always deliver to the origin external user
        const userRoute = resolveDirectDeliveryRoute(original.trace);
        const primaryRoute = userRoute ?? resolveReplyRoute(original.trace);

        // Create the reply message with trace peeled back one hop
        const reply: AgentMessage = {
          message_id: nanoid(),
          from: ctx.agentId ?? "unknown",
          to: primaryRoute.agent,
          content,
          type: "reply",
          trace: popTrace(original.trace),
          reply_to_message_id: origMsgId,
          created_at: new Date().toISOString(),
          status: "pending",
        };

        await store.save(reply);

        // Deliver to user
        const result = await dispatchMessage(
          runtime,
          primaryRoute,
          reply.message_id,
          reply.from,
          content,
        );

        await store.updateStatus(reply.message_id, result.ok ? "delivered" : "failed");

        // Do NOT auto-wake the originating agent on reply.
        // Re-waking causes runaway multi-turn loops: sender sees reply → sends
        // another request → receiver replies → sender sees reply → …
        // The reply is stored in Redis; the sender can retrieve it via
        // list_messages / get_message, or use ask_agent for synchronous flow.
        let agentNotified = false;
        if (alsoNotifyAgent) {
          const fallback = resolveReplyRoute(original.trace);
          dispatchMessage(
            runtime,
            fallback,
            reply.message_id,
            reply.from,
            content,
          ).catch(() => {}); // fire-and-forget
          agentNotified = true;
        }

        return json({
          message_id: reply.message_id,
          routed_to: primaryRoute.agent,
          route_kind: primaryRoute.kind,
          agent_notified: agentNotified,
          status: result.ok ? "delivered" : "failed",
          error: result.error,
        });
      },
    }),
    { name: "reply_message" },
  );

  // ── forward_message ───────────────────────────────────────────────────
  api.registerTool(
    (ctx: OpenClawPluginToolContext) => ({
      name: "forward_message",
      label: "Forward Agent Message",
      description:
        "Forward a received message to the next agent in the chain. " +
        "Automatically appends your context to the trace so replies can route back through you.",
      parameters: Type.Object({
        message_id: Type.String({ description: "The message_id of the message to forward" }),
        to: Type.String({ description: "Target agent ID to forward to" }),
        content: Type.String({ description: "Message content (may differ from original)" }),
      }),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        const { message_id: origMsgId, to, content } = params as {
          message_id: string;
          to: string;
          content: string;
        };

        const rejected = validateTarget(to);
        if (rejected) return rejected;

        const original = await store.get(origMsgId);
        if (!original) {
          return json({ error: `Message not found: ${origMsgId}` });
        }

        // Extend trace with current agent's context
        const extendedTrace: TraceEntry[] = [
          ...original.trace,
          {
            agent: ctx.agentId ?? "unknown",
            session_id: ctx.sessionKey,
          },
        ];

        const fwd: AgentMessage = {
          message_id: nanoid(),
          from: ctx.agentId ?? "unknown",
          to,
          content,
          type: "request",
          trace: extendedTrace,
          reply_to_message_id: origMsgId,
          created_at: new Date().toISOString(),
          status: "pending",
        };

        await store.save(fwd);

        // Fire-and-forget: wake the target agent without blocking the caller
        dispatchMessage(
          runtime,
          { kind: "wake_agent", agent: to },
          fwd.message_id,
          fwd.from,
          content,
        ).then(
          (result) => store.updateStatus(fwd.message_id, result.ok ? "delivered" : "failed"),
          () => store.updateStatus(fwd.message_id, "failed"),
        );

        return json({
          message_id: fwd.message_id,
          forwarded_to: to,
          trace_depth: extendedTrace.length,
          status: "sent",
        });
      },
    }),
    { name: "forward_message" },
  );

  // ── ask_agent ───────────────────────────────────────────────────────
  // Synchronous request-reply: wake the target agent and wait for it to finish.
  // Use only when the caller genuinely needs the answer before it can continue.
  api.registerTool(
    (ctx: OpenClawPluginToolContext) => ({
      name: "ask_agent",
      label: "Ask Agent (sync)",
      description:
        "Send a message to another agent and WAIT for it to finish processing. " +
        "Use this only when you need the result before you can continue " +
        "(e.g. asking a specialist agent a question). " +
        "For fire-and-forget tasks (e.g. submitting to a queue), use send_message instead.",
      parameters: Type.Object({
        to: Type.String({ description: "Target agent ID (e.g. 'security', 'skills')" }),
        content: Type.String({ description: "Question or request content" }),
        trace: Type.Array(TraceEntrySchema, {
          description:
            "Trace chain. First entry should be your origin context " +
            "(agent, session_id, reply_channel, reply_to, reply_account)",
        }),
        metadata: Type.Optional(
          Type.Object({}, { additionalProperties: true, description: "Optional metadata" }),
        ),
      }),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        const { to, content, trace, metadata } = params as {
          to: string;
          content: string;
          trace: TraceEntry[];
          metadata?: Record<string, unknown>;
        };

        const rejected = validateTarget(to);
        if (rejected) return rejected;

        const msg: AgentMessage = {
          message_id: nanoid(),
          from: ctx.agentId ?? "unknown",
          to,
          content,
          type: "request",
          trace,
          metadata,
          created_at: new Date().toISOString(),
          status: "pending",
        };

        await store.save(msg);

        // Synchronous: wait for the target agent to finish processing
        const result = await dispatchMessage(
          runtime,
          { kind: "wake_agent", agent: to },
          msg.message_id,
          msg.from,
          content,
        );

        await store.updateStatus(msg.message_id, result.ok ? "delivered" : "failed");

        return json({
          message_id: msg.message_id,
          status: result.ok ? "delivered" : "failed",
          error: result.error,
        });
      },
    }),
    { name: "ask_agent" },
  );

  // ── get_message ───────────────────────────────────────────────────────
  api.registerTool(
    {
      name: "get_message",
      label: "Get Agent Message",
      description: "Retrieve details of a specific message by ID.",
      parameters: Type.Object({
        message_id: Type.String({ description: "The message_id to look up" }),
      }),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        const { message_id: msgId } = params as { message_id: string };
        const msg = await store.get(msgId);
        if (!msg) {
          return json({ error: `Message not found: ${msgId}` });
        }
        return json(msg);
      },
    },
    { name: "get_message" },
  );

  // ── list_messages ─────────────────────────────────────────────────────
  api.registerTool(
    (ctx: OpenClawPluginToolContext) => ({
      name: "list_messages",
      label: "List Agent Messages",
      description: "List recent messages in your inbox (newest first).",
      parameters: Type.Object({
        limit: Type.Optional(
          Type.Number({ description: "Max messages to return (default 20)", minimum: 1, maximum: 100 }),
        ),
      }),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        const { limit } = params as { limit?: number };
        const agentId = ctx.agentId ?? "unknown";
        const messages = await store.listInbox(agentId, limit ?? 20);
        return json({ agent: agentId, count: messages.length, messages });
      },
    }),
    { name: "list_messages" },
  );
}
