/**
 * Adapts OpenClaw's AnyAgentTool[] into a Claude Agent SDK in-process MCP server.
 *
 * Each AnyAgentTool has {name, description, parameters (JSON Schema), execute()}.
 * The SDK's `createSdkMcpServer` + `tool()` helper expects Zod schemas, but we
 * bypass that by constructing SdkMcpToolDefinition objects directly with raw
 * JSON Schema, which the underlying MCP server also accepts.
 */
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { createSdkMcpServer, type McpSdkServerConfigWithInstance } from "@anthropic-ai/claude-agent-sdk";
import type { AnyAgentTool } from "../tools/common.js";

/**
 * Wrap an array of OpenClaw tools into a single SDK MCP server instance.
 */
export function wrapOpenClawToolsAsSdkMcp(
  tools: AnyAgentTool[],
  serverName = "openclaw-tools",
): McpSdkServerConfigWithInstance {
  const sdkTools = tools.map((t) => ({
    name: t.name ?? "unknown",
    description: t.description ?? "",
    // The SDK accepts JSON Schema via the inputSchema field.
    // We pass the tool's parameters directly (already JSON Schema).
    inputSchema: t.parameters ?? {},
    handler: async (args: Record<string, unknown>): Promise<CallToolResult> => {
      try {
        const toolCallId = `call_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
        const result = await t.execute(toolCallId, args, undefined, undefined, undefined);
        return toolResultToCallToolResult(result);
      } catch (err) {
        return {
          content: [{ type: "text", text: `Error: ${err instanceof Error ? err.message : String(err)}` }],
          isError: true,
        };
      }
    },
  }));

  return createSdkMcpServer({
    name: serverName,
    version: "1.0.0",
    tools: sdkTools as Parameters<typeof createSdkMcpServer>[0]["tools"],
  });
}

/**
 * Convert Pi's AgentToolResult to MCP's CallToolResult.
 */
function toolResultToCallToolResult(result: unknown): CallToolResult {
  if (!result || typeof result !== "object") {
    return { content: [{ type: "text", text: String(result ?? "") }] };
  }

  const r = result as Record<string, unknown>;

  // Pi tool results typically have { output } or { content } or { text }
  if (typeof r.output === "string") {
    return {
      content: [{ type: "text", text: r.output }],
      isError: r.isError === true,
    };
  }
  if (typeof r.text === "string") {
    return {
      content: [{ type: "text", text: r.text }],
      isError: r.isError === true,
    };
  }
  if (typeof r.content === "string") {
    return {
      content: [{ type: "text", text: r.content }],
      isError: r.isError === true,
    };
  }
  // Array content (images, etc.)
  if (Array.isArray(r.content)) {
    return {
      content: r.content as CallToolResult["content"],
      isError: r.isError === true,
    };
  }
  // Fallback: JSON stringify
  return {
    content: [{ type: "text", text: JSON.stringify(r) }],
    isError: r.isError === true,
  };
}
