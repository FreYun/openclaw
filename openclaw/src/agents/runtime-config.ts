import type { OpenClawConfig } from "../config/types.js";

export type AgentRuntimeType = "pi" | "claude-sdk";

/**
 * Resolve which agent runtime to use for a given agent.
 * Check order: agent-level override → global default → "pi".
 */
export function resolveAgentRuntime(
  config?: OpenClawConfig,
  agentId?: string,
): AgentRuntimeType {
  if (agentId) {
    const agentCfg = config?.agents?.list?.find((a) => a.id === agentId);
    if (agentCfg?.runtime === "claude-sdk" || agentCfg?.runtime === "pi") {
      return agentCfg.runtime;
    }
  }
  return "pi";
}
