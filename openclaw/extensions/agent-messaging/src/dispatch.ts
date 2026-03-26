import type { PluginRuntime } from "openclaw/plugin-sdk";
import type { MessageStore } from "./store.js";
import type { RouteDecision } from "./trace.js";
import type { AgentMessage } from "./types.js";

const DISPATCH_TIMEOUT_MS = 120_000; // 2 minutes
const HISTORY_LIMIT = 5;
const SUMMARY_MAX_CHARS = 80;

/**
 * Format conversation history as a compact digest.
 * Each message is truncated to a short summary line.
 * The agent can call `get_message(message_id)` for full content.
 */
function formatHistory(history: AgentMessage[], fromAgent: string, targetAgent: string): string {
  if (history.length === 0) return "";
  const lines = history.map((m) => {
    const firstLine = m.content.split("\n")[0] ?? "";
    const summary = firstLine.length > SUMMARY_MAX_CHARS
      ? firstLine.slice(0, SUMMARY_MAX_CHARS) + "…"
      : firstLine;
    return `  ${m.from} (${m.created_at}): ${summary}  [id:${m.message_id}]`;
  });
  return (
    `[Conversation history with ${fromAgent} — last ${history.length} messages, use get_message(message_id) for details]\n` +
    lines.join("\n") +
    "\n\n"
  );
}

/**
 * Wake a target agent by shelling out to `openclaw agent`.
 * Uses the gateway's runCommandWithTimeout for process lifecycle management.
 *
 * When a MessageStore is provided, conversation history between the two agents
 * is fetched from Redis and injected into the message so the target agent has
 * context from prior exchanges.
 */
export async function dispatchMessage(
  runtime: PluginRuntime,
  route: RouteDecision,
  messageId: string,
  fromAgent: string,
  content: string,
  store?: MessageStore,
): Promise<{ ok: boolean; error?: string }> {
  try {
    if (route.kind === "wake_agent") {
      // Fetch conversation history from Redis if store is available
      let historyPrefix = "";
      if (store) {
        try {
          const history = await store.listConversation(fromAgent, route.agent, HISTORY_LIMIT);
          historyPrefix = formatHistory(history, fromAgent, route.agent);
        } catch {
          // Non-fatal: proceed without history
        }
      }

      const fullMessage = historyPrefix
        ? `${historyPrefix}[MSG:${messageId}] from=${fromAgent}: ${content}`
        : `[MSG:${messageId}] from=${fromAgent}: ${content}`;

      const argv = [
        "openclaw",
        "agent",
        "--agent",
        route.agent,
        "--message",
        fullMessage,
      ];
      if (route.session_id) {
        argv.push("--session-id", route.session_id);
      } else {
        // Route to a per-peer agent session so agent-to-agent messages
        // don't pollute the main session. All communication between two
        // agents shares one session (e.g. agent:bot7:agent:bot1).
        argv.push("--session-key", `agent:${route.agent}:agent:${fromAgent}`);
      }
      await runtime.system.runCommandWithTimeout(argv, DISPATCH_TIMEOUT_MS);
    } else {
      // Origin — deliver directly to external user via `openclaw message send`.
      // Do NOT use `openclaw agent --deliver` — that runs a full LLM turn first
      // and delivers the agent's *response*, not our message.
      const argv = [
        "openclaw",
        "message",
        "send",
        "--channel",
        route.reply_channel,
        "--target",
        route.reply_to,
        "--account",
        route.reply_account,
        "--message",
        content,
      ];
      await runtime.system.runCommandWithTimeout(argv, DISPATCH_TIMEOUT_MS);
    }
    return { ok: true };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { ok: false, error: message };
  }
}
