/**
 * Claude Agent SDK runner — drop-in alternative to runEmbeddedPiAgent().
 *
 * Uses Claude Agent SDK (the Claude Code engine) to execute agent turns,
 * producing the same EmbeddedPiRunResult interface so the rest of OpenClaw
 * (gateway, cron, channels, dashboard) needs zero changes.
 */
import fs from "node:fs/promises";
import { query, type Options as SdkOptions } from "@anthropic-ai/claude-agent-sdk";
import type { RunEmbeddedPiAgentParams } from "../pi-embedded-runner/run/params.js";
import type { EmbeddedPiAgentMeta, EmbeddedPiRunResult } from "../pi-embedded-runner/types.js";
import { resolveUserPath } from "../../utils.js";
import { resolveOpenClawAgentDir } from "../agent-paths.js";
import { DEFAULT_MODEL, DEFAULT_PROVIDER } from "../defaults.js";
import { FailoverError } from "../failover-error.js";
import {
  ensureAuthProfileStore,
  getApiKeyForModel,
  resolveAuthProfileOrder,
} from "../model-auth.js";
import { resolveModel } from "../pi-embedded-runner/model.js";
import { ensureOpenClawModelsJson } from "../models-config.js";
import { buildEmbeddedRunPayloads } from "../pi-embedded-runner/run/payloads.js";
import { createOpenClawTools } from "../openclaw-tools.js";
import { buildAgentSystemPrompt } from "../system-prompt.js";
import { wrapOpenClawToolsAsSdkMcp } from "./tool-adapter.js";
import { mapSdkEventsToCallbacks } from "./event-mapper.js";

const log = {
  info: (...args: unknown[]) => console.log("[claude-sdk-runner]", ...args),
  warn: (...args: unknown[]) => console.warn("[claude-sdk-runner]", ...args),
  debug: (...args: unknown[]) => {},
};

/**
 * Known Anthropic-compatible API bases for non-Claude providers.
 * These endpoints accept Anthropic Messages API format directly.
 */
const ANTHROPIC_COMPAT_BASES: Record<string, string> = {
  zhipu: "https://open.bigmodel.cn/api/anthropic",
};

export async function runEmbeddedClaudeAgent(
  params: RunEmbeddedPiAgentParams,
): Promise<EmbeddedPiRunResult> {
  const started = Date.now();
  const resolvedWorkspace = resolveUserPath(params.workspaceDir);
  await fs.mkdir(resolvedWorkspace, { recursive: true });

  const provider = (params.provider ?? DEFAULT_PROVIDER).trim() || DEFAULT_PROVIDER;
  const modelId = (params.model ?? DEFAULT_MODEL).trim() || DEFAULT_MODEL;
  const agentDir = params.agentDir ?? resolveOpenClawAgentDir();

  // ---- Model & auth resolution (reuse existing OpenClaw infra) ----
  await ensureOpenClawModelsJson(params.config, agentDir);
  const { model, error, authStorage } = resolveModel(provider, modelId, agentDir, params.config);
  if (!model) {
    throw new Error(error ?? `Unknown model: ${provider}/${modelId}`);
  }

  const authStore = ensureAuthProfileStore(agentDir, { allowKeychainPrompt: false });
  const profileOrder = resolveAuthProfileOrder({
    cfg: params.config,
    store: authStore,
    provider,
    preferredProfile: params.authProfileId?.trim(),
  });

  let apiKey: string | undefined;
  for (const candidate of profileOrder.length > 0 ? profileOrder : [undefined]) {
    try {
      const info = await getApiKeyForModel({
        model,
        cfg: params.config,
        profileId: candidate,
        store: authStore,
        agentDir,
      });
      apiKey = info.apiKey;
      if (apiKey) break;
    } catch {
      continue;
    }
  }
  if (!apiKey) {
    throw new FailoverError(`No API key resolved for provider "${provider}".`, {
      reason: "auth",
      provider,
      model: modelId,
    });
  }

  // ---- System prompt (reuse existing builder) ----
  const systemPromptText = buildAgentSystemPrompt({
    workspaceDir: resolvedWorkspace,
    defaultThinkLevel: params.thinkLevel,
    reasoningLevel: params.reasoningLevel,
    extraSystemPrompt: params.extraSystemPrompt,
    ownerNumbers: params.ownerNumbers,
    promptMode: "full",
  });

  // ---- Tools ----
  const openclawTools = createOpenClawTools({
    agentSessionKey: params.sessionKey,
    agentAccountId: params.agentAccountId,
    agentDir,
    workspaceDir: resolvedWorkspace,
    config: params.config,
  });
  const mcpServer = wrapOpenClawToolsAsSdkMcp(openclawTools);

  // ---- Resolve API config for SDK ----
  const env: Record<string, string | undefined> = { ...process.env };
  env.ANTHROPIC_API_KEY = apiKey;

  // For non-Anthropic providers, set API base URL
  const compatBase = ANTHROPIC_COMPAT_BASES[provider];
  if (compatBase) {
    env.ANTHROPIC_BASE_URL = compatBase;
  } else if (provider !== "anthropic") {
    // For providers without known Anthropic-compat endpoint,
    // check config for a litellm proxy URL
    const litellmProxy = (params.config?.agents?.defaults as Record<string, unknown> | undefined)
      ?.litellmProxy as string | undefined;
    if (litellmProxy) {
      env.ANTHROPIC_BASE_URL = litellmProxy;
    } else {
      // Try to use the model's baseUrl directly
      const baseUrl = (model as { baseUrl?: string }).baseUrl;
      if (baseUrl) {
        env.ANTHROPIC_BASE_URL = baseUrl;
      }
    }
  }

  // ---- SDK options ----
  const abortController = new AbortController();
  if (params.abortSignal) {
    params.abortSignal.addEventListener("abort", () => abortController.abort());
  }

  const sdkOptions: SdkOptions = {
    abortController,
    cwd: resolvedWorkspace,
    model: modelId,
    systemPrompt: systemPromptText,
    env,
    permissionMode: "bypassPermissions",
    allowDangerouslySkipPermissions: true,
    persistSession: false,
    includePartialMessages: true,
    mcpServers: {
      "openclaw-tools": mcpServer,
    },
    // Disable built-in tools — we provide our own via MCP
    // Keep basic file/shell tools from Claude Code
    allowedTools: [
      "Read", "Edit", "Write", "Bash", "Glob", "Grep",
      "WebSearch", "WebFetch", "NotebookEdit",
      "mcp__openclaw-tools__*",
    ],
    thinking: params.thinkLevel === "off"
      ? { type: "disabled" as const }
      : { type: "adaptive" as const },
    maxTurns: 30,
    settingSources: [],
  };

  // ---- Execute ----
  log.info(
    `starting claude-sdk run: provider=${provider} model=${modelId} sessionId=${params.sessionId}`,
  );

  let eventResult;
  try {
    const sdkStream = query({ prompt: params.prompt, options: sdkOptions });
    eventResult = await mapSdkEventsToCallbacks(sdkStream, {
      onPartialReply: params.onPartialReply,
      onBlockReply: params.onBlockReply,
      onBlockReplyFlush: params.onBlockReplyFlush,
      onToolResult: params.onToolResult,
      onReasoningStream: params.onReasoningStream,
      onAgentEvent: params.onAgentEvent,
      onAssistantMessageStart: params.onAssistantMessageStart,
    });
  } catch (err) {
    const errorText = err instanceof Error ? err.message : String(err);
    log.warn(`claude-sdk run error: ${errorText}`);

    // Map SDK errors to FailoverError for model fallback
    if (
      /rate.?limit|429|quota|billing|unauthorized|401|403/i.test(errorText)
    ) {
      throw new FailoverError(errorText, {
        reason: "rate_limit",
        provider,
        model: modelId,
      });
    }
    throw err;
  }

  // ---- Build result ----
  const agentMeta: EmbeddedPiAgentMeta = {
    sessionId: eventResult.sessionId || params.sessionId,
    provider,
    model: modelId,
    usage: eventResult.usage,
  };

  const payloads = buildEmbeddedRunPayloads({
    assistantTexts: eventResult.assistantTexts,
    toolMetas: eventResult.toolMetas,
    lastAssistant: undefined,
    lastToolError: undefined,
    config: params.config,
    sessionKey: params.sessionKey ?? params.sessionId,
    verboseLevel: params.verboseLevel,
    reasoningLevel: params.reasoningLevel,
    toolResultFormat: params.toolResultFormat ?? "markdown",
    inlineToolResultsAllowed: false,
  });

  log.info(
    `claude-sdk run done: durationMs=${Date.now() - started} texts=${eventResult.assistantTexts.length}`,
  );

  return {
    payloads: payloads.length > 0 ? payloads : undefined,
    meta: {
      durationMs: Date.now() - started,
      agentMeta,
      aborted: eventResult.aborted,
    },
    didSendViaMessagingTool: eventResult.messagingToolSentTexts.length > 0,
    messagingToolSentTexts: eventResult.messagingToolSentTexts,
    messagingToolSentTargets: eventResult.messagingToolSentTargets,
  };
}
