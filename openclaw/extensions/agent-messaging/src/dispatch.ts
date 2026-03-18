import type { PluginRuntime } from "openclaw/plugin-sdk";
import type { RouteDecision } from "./trace.js";

const DISPATCH_TIMEOUT_MS = 120_000; // 2 minutes

/**
 * Wake a target agent by shelling out to `openclaw agent`.
 * Uses the gateway's runCommandWithTimeout for process lifecycle management.
 */
export async function dispatchMessage(
  runtime: PluginRuntime,
  route: RouteDecision,
  messageId: string,
  fromAgent: string,
  content: string,
): Promise<{ ok: boolean; error?: string }> {
  try {
    if (route.kind === "wake_agent") {
      // Intermediate relay or new message — just wake the agent
      const argv = [
        "openclaw",
        "agent",
        "--agent",
        route.agent,
        "--message",
        `[MSG:${messageId}] from=${fromAgent}: ${content}`,
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
