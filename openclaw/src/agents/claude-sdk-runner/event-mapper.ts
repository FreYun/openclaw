/**
 * Maps Claude Agent SDK streaming events (SDKMessage) to the OpenClaw callback
 * interface expected by the gateway and cron layers.
 */
import type {
  SDKMessage,
  SDKAssistantMessage,
  SDKPartialAssistantMessage,
  SDKResultMessage,
  SDKToolUseSummaryMessage,
  SDKToolProgressMessage,
} from "@anthropic-ai/claude-agent-sdk";
import type { MessagingToolSend } from "../pi-embedded-subscribe.handlers.types.js";

export type EventMapperCallbacks = {
  onPartialReply?: (payload: { text?: string; mediaUrls?: string[] }) => void | Promise<void>;
  onBlockReply?: (payload: {
    text?: string;
    mediaUrls?: string[];
    audioAsVoice?: boolean;
    replyToId?: string;
    replyToTag?: boolean;
    replyToCurrent?: boolean;
  }) => void | Promise<void>;
  onBlockReplyFlush?: () => void | Promise<void>;
  onToolResult?: (payload: { text?: string; mediaUrls?: string[] }) => void | Promise<void>;
  onReasoningStream?: (payload: { text?: string; mediaUrls?: string[] }) => void | Promise<void>;
  onAgentEvent?: (evt: { stream: string; data: Record<string, unknown> }) => void | Promise<void>;
  onAssistantMessageStart?: () => void | Promise<void>;
};

export type EventMapperResult = {
  assistantTexts: string[];
  toolMetas: Array<{ toolName: string; meta?: string }>;
  messagingToolSentTexts: string[];
  messagingToolSentTargets: MessagingToolSend[];
  lastAssistantText: string;
  resultText: string;
  usage?: { input?: number; output?: number; cacheRead?: number; cacheWrite?: number };
  aborted: boolean;
  isError: boolean;
  sessionId: string;
};

/**
 * Consume the SDK's async message stream and map events to OpenClaw callbacks.
 */
export async function mapSdkEventsToCallbacks(
  sdkStream: AsyncIterable<SDKMessage>,
  callbacks: EventMapperCallbacks,
): Promise<EventMapperResult> {
  const assistantTexts: string[] = [];
  const toolMetas: Array<{ toolName: string; meta?: string }> = [];
  const messagingToolSentTexts: string[] = [];
  const messagingToolSentTargets: MessagingToolSend[] = [];
  let lastAssistantText = "";
  let resultText = "";
  let usage: EventMapperResult["usage"];
  let aborted = false;
  let isError = false;
  let sessionId = "";
  let currentAssistantBuffer = "";

  void callbacks.onAgentEvent?.({ stream: "lifecycle", data: { phase: "start" } });

  for await (const msg of sdkStream) {
    switch (msg.type) {
      case "stream_event":
        handleStreamEvent(msg as SDKPartialAssistantMessage, callbacks, {
          onTextDelta(text) {
            currentAssistantBuffer += text;
            void callbacks.onPartialReply?.({ text });
          },
          onThinkingDelta(text) {
            void callbacks.onReasoningStream?.({ text });
          },
        });
        break;

      case "assistant":
        handleAssistantMessage(msg as SDKAssistantMessage, callbacks, {
          currentAssistantBuffer,
          assistantTexts,
          toolMetas,
          onFlush() {
            currentAssistantBuffer = "";
          },
        });
        sessionId = (msg as SDKAssistantMessage).session_id;
        break;

      case "tool_use_summary":
        handleToolSummary(msg as SDKToolUseSummaryMessage, callbacks, toolMetas);
        break;

      case "tool_progress":
        handleToolProgress(msg as SDKToolProgressMessage, callbacks);
        break;

      case "result": {
        const result = msg as SDKResultMessage;
        if (result.subtype === "success") {
          resultText = (result as { result?: string }).result ?? "";
          if (resultText && !assistantTexts.includes(resultText)) {
            assistantTexts.push(resultText);
          }
        }
        isError = result.is_error;
        usage = {
          input: result.usage?.input_tokens,
          output: result.usage?.output_tokens,
          cacheRead: result.usage?.cache_read_input_tokens,
          cacheWrite: result.usage?.cache_creation_input_tokens,
        };
        sessionId = sessionId || "";
        break;
      }

      default:
        // Ignore system, user, and other message types
        break;
    }
  }

  // Flush any remaining assistant text as block reply
  if (currentAssistantBuffer.trim()) {
    lastAssistantText = currentAssistantBuffer.trim();
    if (!assistantTexts.includes(lastAssistantText)) {
      assistantTexts.push(lastAssistantText);
    }
    void callbacks.onBlockReply?.({ text: lastAssistantText });
  }

  void callbacks.onAgentEvent?.({ stream: "lifecycle", data: { phase: "end" } });

  return {
    assistantTexts,
    toolMetas,
    messagingToolSentTexts,
    messagingToolSentTargets,
    lastAssistantText,
    resultText,
    usage,
    aborted,
    isError,
    sessionId,
  };
}

// ---- Internal handlers ----

function handleStreamEvent(
  msg: SDKPartialAssistantMessage,
  _callbacks: EventMapperCallbacks,
  ctx: {
    onTextDelta: (text: string) => void;
    onThinkingDelta: (text: string) => void;
  },
) {
  const event = msg.event;
  if (!event || typeof event !== "object") return;

  const eventType = (event as { type?: string }).type;

  if (eventType === "content_block_delta") {
    const delta = (event as { delta?: { type?: string; text?: string; thinking?: string } }).delta;
    if (!delta) return;
    if (delta.type === "text_delta" && delta.text) {
      ctx.onTextDelta(delta.text);
    } else if (delta.type === "thinking_delta" && delta.thinking) {
      ctx.onThinkingDelta(delta.thinking);
    }
  } else if (eventType === "content_block_start") {
    const contentBlock = (event as { content_block?: { type?: string } }).content_block;
    if (contentBlock?.type === "text") {
      // Text block started — no action needed, deltas will follow
    } else if (contentBlock?.type === "thinking") {
      // Thinking block started
    }
  }
}

function handleAssistantMessage(
  msg: SDKAssistantMessage,
  callbacks: EventMapperCallbacks,
  ctx: {
    currentAssistantBuffer: string;
    assistantTexts: string[];
    toolMetas: Array<{ toolName: string; meta?: string }>;
    onFlush: () => void;
  },
) {
  void callbacks.onAssistantMessageStart?.();

  const message = msg.message;
  if (!message) return;

  // Extract text content from the BetaMessage
  const content = message.content;
  if (!Array.isArray(content)) return;

  let fullText = "";
  for (const block of content) {
    if (block.type === "text") {
      fullText += (block as { text: string }).text;
    } else if (block.type === "tool_use") {
      const toolUse = block as { name?: string; id?: string; input?: unknown };
      ctx.toolMetas.push({
        toolName: toolUse.name ?? "unknown",
        meta: toolUse.name,
      });
      void callbacks.onAgentEvent?.({
        stream: "tool",
        data: {
          phase: "start",
          name: toolUse.name ?? "unknown",
          toolCallId: toolUse.id ?? "",
        },
      });
    }
  }

  if (fullText.trim()) {
    const text = fullText.trim();
    if (!ctx.assistantTexts.includes(text)) {
      ctx.assistantTexts.push(text);
    }
    void callbacks.onBlockReply?.({ text });
  }

  // Check for errors
  if (msg.error) {
    void callbacks.onBlockReply?.({
      text: `Error: ${msg.error}`,
    });
  }

  ctx.onFlush();
}

function handleToolSummary(
  msg: SDKToolUseSummaryMessage,
  callbacks: EventMapperCallbacks,
  toolMetas: Array<{ toolName: string; meta?: string }>,
) {
  void callbacks.onToolResult?.({ text: msg.summary });
  // Tool summaries may reference multiple tool use IDs
  for (const id of msg.preceding_tool_use_ids) {
    if (!toolMetas.some((m) => m.toolName === id)) {
      toolMetas.push({ toolName: "tool", meta: msg.summary });
    }
  }
}

function handleToolProgress(
  msg: SDKToolProgressMessage,
  callbacks: EventMapperCallbacks,
) {
  void callbacks.onAgentEvent?.({
    stream: "tool",
    data: {
      phase: "update",
      name: msg.tool_name,
      toolCallId: msg.tool_use_id,
      elapsedSeconds: msg.elapsed_time_seconds,
    },
  });
}
