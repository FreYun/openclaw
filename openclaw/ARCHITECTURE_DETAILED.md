# OpenClaw 详细架构与实现文档

> 本文档深入分析 OpenClaw 的系统架构和具体实现细节
> 
> 生成时间: 2026-02-06
> 版本: 2026.2.4

## 目录

1. [系统架构概览](#系统架构概览)
2. [Gateway 核心实现](#gateway-核心实现)
3. [WebSocket 协议](#websocket-协议)
4. [消息路由机制](#消息路由机制)
5. [Agent 执行流程](#agent-执行流程)
6. [工具调用系统](#工具调用系统)
7. [插件系统](#插件系统)
8. [技能系统](#技能系统)
9. [渠道集成](#渠道集成)
10. [会话管理实现](#会话管理实现)
11. [数据流与状态管理](#数据流与状态管理)

---

## 系统架构概览

### 1. 整体架构

OpenClaw 采用**中心化 Gateway 架构**，所有组件通过 Gateway 进行协调：

```
┌─────────────────────────────────────────────────────────────┐
│                      Gateway Server                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ WebSocket    │  │ HTTP Server  │  │ Canvas Host  │     │
│  │ Server       │  │              │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Channel Manager (渠道管理器)                │   │
│  │  WhatsApp │ Telegram │ Slack │ Discord │ ...        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Agent Runtime (智能体运行时)                │   │
│  │  Session Manager │ Memory Search │ Tool Execution   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Plugin System (插件系统)                    │   │
│  │  Plugin Registry │ Hook System │ Service Discovery │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ CLI Client   │    │ macOS App    │    │ Web UI       │
│ (WebSocket)  │    │ (WebSocket)  │    │ (WebSocket)  │
└──────────────┘    └──────────────┘    └──────────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                    WebSocket 连接 (ws://127.0.0.1:18789)
```

### 2. 核心组件

#### 2.1 Gateway Server

**位置**: `src/gateway/server.impl.ts`

Gateway 是系统的核心，负责：

- **WebSocket 服务器**: 处理客户端连接和消息
- **HTTP 服务器**: 提供 REST API 和静态资源
- **渠道管理**: 维护与各种消息平台的连接
- **Agent 调度**: 管理智能体的执行和资源
- **事件广播**: 向所有连接的客户端推送事件

#### 2.2 Channel Manager

**位置**: `src/gateway/server-channels.ts`

管理所有消息渠道的生命周期：

- 启动和停止渠道连接
- 处理入站消息
- 路由出站消息
- 管理渠道状态

#### 2.3 Agent Runtime

**位置**: `src/agents/`

智能体的执行环境：

- **Session Manager**: 管理会话状态
- **Memory Search**: 记忆检索系统
- **Tool Execution**: 工具调用执行
- **Model Integration**: LLM 模型集成

---

## Gateway 核心实现

### 1. 服务器启动流程

**位置**: `src/gateway/server.impl.ts`

```typescript
async function startGatewayServer(port = 18789, opts = {}) {
  // 1. 加载和验证配置
  let configSnapshot = await readConfigFileSnapshot();
  migrateLegacyConfig(configSnapshot.parsed);
  
  // 2. 解析运行时配置
  const runtimeConfig = resolveGatewayRuntimeConfig({
    config: configSnapshot.parsed,
    opts
  });
  
  // 3. 创建运行时状态
  const runtimeState = await createGatewayRuntimeState({
    cfg: configSnapshot.parsed,
    bindHost: runtimeConfig.bindHost,
    port,
    // ... 其他配置
  });
  
  // 4. 启动渠道管理器
  const channelManager = createChannelManager({
    cfg: configSnapshot.parsed,
    runtime: defaultRuntime,
    // ...
  });
  
  // 5. 加载插件
  const pluginRegistry = await loadGatewayPlugins({
    config: configSnapshot.parsed,
    // ...
  });
  
  // 6. 启动各种服务
  startGatewayDiscovery();
  startGatewayCronService();
  startGatewayMaintenanceTimers();
  
  // 7. 返回服务器实例
  return {
    close: async () => { /* 清理资源 */ }
  };
}
```

### 2. WebSocket 服务器实现

**位置**: `src/gateway/server/ws-connection.ts`

#### 2.1 连接处理

```typescript
wss.on("connection", (socket, upgradeReq) => {
  const connId = randomUUID();
  const remoteAddr = socket._socket?.remoteAddress;
  
  // 1. 解析请求头
  const requestHost = upgradeReq.headers.host;
  const requestOrigin = upgradeReq.headers.origin;
  const forwardedFor = upgradeReq.headers["x-forwarded-for"];
  
  // 2. 创建连接状态
  let client: GatewayWsClient | null = null;
  let handshakeState: "pending" | "connected" | "failed" = "pending";
  
  // 3. 附加消息处理器
  attachGatewayWsMessageHandler({
    socket,
    upgradeReq,
    connId,
    // ... 配置
  });
  
  // 4. 处理连接关闭
  socket.on("close", (code, reason) => {
    // 清理资源
  });
});
```

#### 2.2 消息处理

**位置**: `src/gateway/server/ws-connection/message-handler.ts`

```typescript
socket.on("message", async (data) => {
  const text = rawDataToString(data);
  const parsed = JSON.parse(text);
  
  // 1. 解析帧类型
  const frameType = parsed.type;  // "req" | "event"
  const frameMethod = parsed.method;
  const frameId = parsed.id;
  
  // 2. 处理握手
  if (!client) {
    if (frameType === "req" && frameMethod === "connect") {
      // 执行连接握手
      await handleConnect(parsed.params);
    }
    return;
  }
  
  // 3. 处理请求
  if (frameType === "req") {
    await handleRequest({
      method: frameMethod,
      params: parsed.params,
      id: frameId,
      respond: (ok, payload, error) => {
        send({ type: "res", id: frameId, ok, payload, error });
      }
    });
  }
  
  // 4. 处理事件订阅
  if (frameType === "event") {
    handleEventSubscription(parsed);
  }
});
```

### 3. HTTP 服务器实现

**位置**: `src/gateway/server-http.ts`

Gateway 同时提供 HTTP 服务：

#### 3.1 路由

```typescript
function createGatewayHttpServer(opts) {
  const app = express();
  
  // 1. Control UI (管理界面)
  if (opts.controlUiEnabled) {
    app.use(opts.controlUiBasePath, serveControlUi());
  }
  
  // 2. OpenAI 兼容 API
  if (opts.openAiChatCompletionsEnabled) {
    app.post("/v1/chat/completions", handleOpenAiHttpRequest);
  }
  
  // 3. OpenResponses API
  if (opts.openResponsesEnabled) {
    app.post("/v1/responses", handleOpenResponsesHttpRequest);
  }
  
  // 4. Hooks 端点
  app.post("/hooks/*", handleHooksRequest);
  
  // 5. 插件 HTTP 端点
  app.use("/plugins/*", handlePluginRequest);
  
  return app;
}
```

### 4. 运行时状态管理

**位置**: `src/gateway/server-runtime-state.ts`

Gateway 维护多个运行时状态：

```typescript
type GatewayRuntimeState = {
  // WebSocket 连接
  clients: Set<GatewayWsClient>;
  wss: WebSocketServer;
  
  // Agent 执行状态
  agentRunSeq: Map<string, number>;  // sessionKey -> sequence
  chatRunState: ChatRunState;
  chatAbortControllers: Map<string, AbortController>;
  
  // 工具事件
  toolEventRecipients: ToolEventRecipientRegistry;
  
  // 去重缓存
  dedupe: Map<string, DedupeEntry>;
  
  // 广播函数
  broadcast: (event: string, payload: unknown) => void;
};
```

---

## WebSocket 协议

### 1. 协议格式

OpenClaw 使用基于 JSON 的 WebSocket 协议：

#### 1.1 请求帧

```typescript
{
  type: "req",
  method: "agent" | "send" | "status" | ...,
  params: { /* 方法参数 */ },
  id: "request-id"
}
```

#### 1.2 响应帧

```typescript
{
  type: "res",
  id: "request-id",
  ok: boolean,
  payload?: unknown,
  error?: { code: string, message: string }
}
```

#### 1.3 事件帧

```typescript
{
  type: "event",
  event: "agent" | "chat" | "presence" | ...,
  payload: { /* 事件数据 */ }
}
```

### 2. 连接握手

**位置**: `src/gateway/server/ws-connection/message-handler.ts`

```typescript
async function handleConnect(params: ConnectParams) {
  // 1. 验证认证
  const authResult = validateAuth(params.auth);
  if (!authResult.ok) {
    send({ type: "res", id: params.id, ok: false, error: authResult.error });
    return;
  }
  
  // 2. 创建客户端对象
  const client: GatewayWsClient = {
    id: randomUUID(),
    role: params.client?.role ?? "client",
    mode: params.client?.mode,
    connectedAt: Date.now(),
    // ...
  };
  
  // 3. 注册客户端
  clients.add(client);
  setClient(client);
  
  // 4. 发送连接成功响应
  send({
    type: "res",
    id: params.id,
    ok: true,
    payload: {
      clientId: client.id,
      serverInfo: { /* ... */ }
    }
  });
  
  // 5. 发送初始状态事件
  broadcast("presence", { clients: Array.from(clients) });
  broadcast("health", getHealthSnapshot());
}
```

### 3. 方法处理

**位置**: `src/gateway/server-methods.ts`

Gateway 提供的方法：

```typescript
const coreGatewayHandlers: GatewayRequestHandlers = {
  // Agent 相关
  agent: handleAgentRequest,
  "agent.wait": handleAgentWaitRequest,
  
  // 消息相关
  send: handleSendRequest,
  
  // 会话相关
  sessions: handleSessionsRequest,
  "sessions.send": handleSessionsSendRequest,
  
  // 状态相关
  status: handleStatusRequest,
  health: handleHealthRequest,
  
  // 节点相关
  "nodes.invoke": handleNodeInvokeRequest,
  
  // 系统相关
  "system.presence": handleSystemPresenceRequest,
  "system.reload": handleSystemReloadRequest,
};
```

### 4. 事件系统

Gateway 向客户端推送多种事件：

```typescript
// Agent 事件
{
  event: "agent",
  payload: {
    stream: "assistant" | "tool" | "lifecycle",
    data: { /* 事件数据 */ },
    runId: string,
    sessionKey: string
  }
}

// 聊天事件
{
  event: "chat",
  payload: {
    sessionKey: string,
    message: { /* 消息内容 */ }
  }
}

// 健康状态事件
{
  event: "health",
  payload: {
    version: number,
    status: { /* 健康状态 */ }
  }
}
```

---

## 消息路由机制

### 1. 路由决策流程

**位置**: `src/routing/resolve-route.ts`

当消息到达时，Gateway 需要决定：

1. **选择哪个 Agent**
2. **使用哪个 Session Key**
3. **如何路由回复**

```typescript
export function resolveAgentRoute(input: ResolveAgentRouteInput): ResolvedAgentRoute {
  const { channel, accountId, peer, guildId, teamId } = input;
  
  // 1. 获取所有绑定规则
  const bindings = listBindings(input.cfg);
  
  // 2. 按优先级匹配
  // 优先级 1: 精确对端匹配
  if (peer) {
    const peerMatch = bindings.find(b => matchesPeer(b.match, peer));
    if (peerMatch) {
      return choose(peerMatch.agentId, "binding.peer");
    }
  }
  
  // 优先级 2: Guild 匹配 (Discord)
  if (guildId) {
    const guildMatch = bindings.find(b => matchesGuild(b.match, guildId));
    if (guildMatch) {
      return choose(guildMatch.agentId, "binding.guild");
    }
  }
  
  // 优先级 3: Team 匹配 (Slack)
  if (teamId) {
    const teamMatch = bindings.find(b => matchesTeam(b.match, teamId));
    if (teamMatch) {
      return choose(teamMatch.agentId, "binding.team");
    }
  }
  
  // 优先级 4: 账户匹配
  const accountMatch = bindings.find(b => matchesAccount(b.match, accountId));
  if (accountMatch) {
    return choose(accountMatch.agentId, "binding.account");
  }
  
  // 优先级 5: 渠道匹配
  const channelMatch = bindings.find(b => matchesChannel(b.match, channel));
  if (channelMatch) {
    return choose(channelMatch.agentId, "binding.channel");
  }
  
  // 默认: 使用默认 Agent
  return choose(resolveDefaultAgentId(input.cfg), "default");
}
```

### 2. Session Key 生成

**位置**: `src/routing/session-key.ts`

Session Key 用于隔离不同的对话上下文：

```typescript
function buildAgentSessionKey(params: {
  agentId: string;
  channel: string;
  accountId?: string;
  peer?: RoutePeer;
  dmScope?: "main" | "per-peer" | "per-channel-peer";
}): string {
  const { agentId, channel, peer, dmScope } = params;
  
  // 私信模式
  if (peer?.kind === "dm") {
    switch (dmScope) {
      case "main":
        return `agent:${agentId}:main`;
      case "per-peer":
        return `agent:${agentId}:dm:${peer.id}`;
      case "per-channel-peer":
        return `agent:${agentId}:${channel}:dm:${peer.id}`;
    }
  }
  
  // 群组模式
  if (peer?.kind === "group") {
    return `agent:${agentId}:${channel}:group:${peer.id}`;
  }
  
  // 频道模式
  if (peer?.kind === "channel") {
    return `agent:${agentId}:${channel}:channel:${peer.id}`;
  }
  
  // 默认主会话
  return `agent:${agentId}:main`;
}
```

### 3. 回复路由

**位置**: `src/auto-reply/reply/route-reply.ts`

回复消息时，Gateway 需要将回复发送回原始渠道：

```typescript
export async function routeReply(params: RouteReplyParams): Promise<RouteReplyResult> {
  const { payload, channel, to, accountId, threadId } = params;
  
  // 1. 规范化渠道 ID
  const channelId = normalizeChannelId(channel);
  if (!channelId) {
    return { ok: false, error: `Unknown channel: ${channel}` };
  }
  
  // 2. 规范化回复载荷
  const normalized = normalizeReplyPayload(payload);
  
  // 3. 调用渠道发送函数
  const results = await deliverOutboundPayloads({
    cfg,
    channel: channelId,
    to,
    accountId,
    payloads: [normalized],
    replyToId,
    threadId,
    // 镜像到会话记录
    mirror: {
      sessionKey: params.sessionKey,
      agentId: resolveSessionAgentId(params.sessionKey),
      text: normalized.text,
      mediaUrls: normalized.mediaUrls
    }
  });
  
  return { ok: true, messageId: results[0]?.messageId };
}
```

---

## Agent 执行流程

### 1. Agent 命令处理

**位置**: `src/gateway/server-methods/agent.ts`

当客户端调用 `agent` 方法时：

```typescript
export const agentHandlers: GatewayRequestHandlers = {
  agent: async ({ params, respond, context }) => {
    // 1. 验证参数
    if (!validateAgentParams(params)) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "invalid params"));
      return;
    }
    
    // 2. 解析会话
    const sessionKey = resolveSessionKey(params);
    const sessionEntry = loadSessionEntry(sessionKey);
    
    // 3. 生成运行 ID
    const runId = randomUUID();
    const acceptedAt = Date.now();
    
    // 4. 立即返回（异步执行）
    respond(true, { runId, acceptedAt });
    
    // 5. 异步执行 Agent
    agentCommand({
      message: params.message,
      sessionKey,
      runId,
      deliver: params.deliver ?? true,
      // ...
    }, defaultRuntime, deps)
      .then(result => {
        // 发送完成事件
        broadcast("agent", {
          stream: "lifecycle",
          data: { phase: "end", runId }
        });
      })
      .catch(error => {
        // 发送错误事件
        broadcast("agent", {
          stream: "lifecycle",
          data: { phase: "error", runId, error: error.message }
        });
      });
  }
};
```

### 2. Agent 执行核心

**位置**: `src/commands/agent.ts`

```typescript
export async function agentCommand(params: AgentCommandParams, runtime: RuntimeEnv, deps: CliDeps) {
  const { message, sessionKey, runId } = params;
  
  // 1. 解析 Agent 配置
  const agentId = resolveSessionAgentId(sessionKey);
  const agentDir = resolveAgentDir(agentId);
  const workspaceDir = resolveAgentWorkspaceDir(agentId);
  
  // 2. 加载会话管理器
  const sessionManager = SessionManager.open(sessionFile);
  
  // 3. 构建技能快照
  const skillSnapshot = buildWorkspaceSkillSnapshot(workspaceDir, {
    config: cfg,
    skillFilter: params.skillFilter
  });
  
  // 4. 运行嵌入式 Pi Agent
  const result = await runEmbeddedPiAgent({
    message,
    sessionManager,
    skillSnapshot,
    workspaceDir,
    agentDir,
    model: resolveModel(cfg, agentId),
    // ...
  });
  
  // 5. 处理结果
  if (result.payloads && params.deliver) {
    await deliverReplies(result.payloads, sessionKey);
  }
  
  return result;
}
```

### 3. 嵌入式 Pi Agent

**位置**: `src/agents/pi-embedded-runner.ts`

OpenClaw 使用 `@mariozechner/pi-coding-agent` 作为 Agent 运行时：

```typescript
export async function runEmbeddedPiAgent(params: EmbeddedPiRunParams): Promise<EmbeddedPiRunResult> {
  const { message, sessionManager, skillSnapshot, workspaceDir } = params;
  
  // 1. 序列化执行（每个 sessionKey 一个队列）
  const lane = resolveEmbeddedSessionLane(params.sessionKey);
  await queueEmbeddedPiMessage(lane, async () => {
    
    // 2. 创建 Pi Session
    const piSession = await createPiSession({
      model: params.model,
      sessionManager,
      workspaceDir,
      // ...
    });
    
    // 3. 订阅事件
    const unsubscribe = piSession.subscribe((event) => {
      // 转发事件到 Gateway
      emitAgentEvent({
        runId: params.runId,
        stream: mapPiEventToStream(event),
        data: mapPiEventToData(event)
      });
    });
    
    // 4. 执行 Agent 循环
    const result = await piSession.run({
      message,
      tools: createOpenClawTools({
        workspaceDir,
        agentDir: params.agentDir,
        // ...
      }),
      skills: skillSnapshot,
      // ...
    });
    
    // 5. 清理
    unsubscribe();
    return result;
  });
}
```

### 4. Agent 循环生命周期

```
用户消息
    │
    ▼
[1] 初始化会话状态
    ├─ 检查会话重置条件
    ├─ 加载或创建会话
    └─ 构建上下文
    │
    ▼
[2] 构建 Agent 上下文
    ├─ 加载记忆搜索
    ├─ 加载技能快照
    ├─ 构建系统提示
    └─ 准备工具列表
    │
    ▼
[3] 调用 LLM
    ├─ 构建消息历史
    ├─ 调用模型 API
    └─ 流式接收响应
    │
    ▼
[4] 处理工具调用
    ├─ 解析工具调用
    ├─ 执行工具
    └─ 返回结果
    │
    ▼
[5] 生成最终回复
    ├─ 收集所有文本块
    ├─ 格式化回复
    └─ 发送到渠道
    │
    ▼
[6] 持久化会话
    ├─ 保存消息到 JSONL
    ├─ 更新会话元数据
    └─ 触发记忆同步
```

---

## 工具调用系统

### 1. 工具定义

**位置**: `src/agents/pi-tools.ts`

OpenClaw 提供多种内置工具：

```typescript
export function createOpenClawTools(options?: OpenClawToolsOptions): AnyAgentTool[] {
  return [
    // 文件操作
    createReadTool({ workspaceDir: options.workspaceDir }),
    createWriteTool({ workspaceDir: options.workspaceDir }),
    createListTool({ workspaceDir: options.workspaceDir }),
    
    // 命令执行
    createExecTool({ 
      defaults: options.exec,
      sandbox: options.sandbox 
    }),
    
    // 消息发送
    createMessageTool({
      sessionKey: options.agentSessionKey,
      channel: options.agentChannel,
      to: options.agentTo
    }),
    
    // 网络请求
    createWebFetchTool(),
    
    // 记忆搜索
    createMemorySearchTool({
      agentId: resolveAgentIdFromSessionKey(options.agentSessionKey),
      workspaceDir: options.workspaceDir
    }),
    
    // ... 更多工具
  ];
}
```

### 2. 工具执行流程

**位置**: `src/agents/pi-embedded-subscribe.handlers.tools.ts`

```typescript
export async function handleToolExecutionStart(
  ctx: EmbeddedPiSubscribeContext,
  evt: AgentEvent & { toolName: string; toolCallId: string; args: unknown }
) {
  const { toolName, toolCallId, args } = evt;
  
  // 1. 发送工具开始事件
  emitAgentEvent({
    runId: ctx.params.runId,
    stream: "tool",
    data: {
      phase: "start",
      name: toolName,
      toolCallId,
      args: args as Record<string, unknown>
    }
  });
  
  // 2. 查找工具定义
  const tool = ctx.tools.find(t => t.name === toolName);
  if (!tool) {
    throw new Error(`Tool not found: ${toolName}`);
  }
  
  // 3. 执行工具
  try {
    const result = await tool.execute(toolCallId, args);
    
    // 4. 发送工具结果事件
    emitAgentEvent({
      runId: ctx.params.runId,
      stream: "tool",
      data: {
        phase: "result",
        name: toolName,
        toolCallId,
        result,
        isError: false
      }
    });
    
    return result;
  } catch (error) {
    // 5. 发送工具错误事件
    emitAgentEvent({
      runId: ctx.params.runId,
      stream: "tool",
      data: {
        phase: "result",
        name: toolName,
        toolCallId,
        result: error.message,
        isError: true
      }
    });
    
    throw error;
  }
}
```

### 3. 工具类型

#### 3.1 文件工具

```typescript
// 读取文件
createReadTool({
  workspaceDir: "/path/to/workspace"
})

// 写入文件
createWriteTool({
  workspaceDir: "/path/to/workspace"
})

// 列出目录
createListTool({
  workspaceDir: "/path/to/workspace"
})
```

#### 3.2 执行工具

```typescript
createExecTool({
  defaults: {
    timeout: 30000,
    cwd: workspaceDir
  },
  sandbox: {
    enabled: true,
    allowedPaths: [workspaceDir]
  }
})
```

#### 3.3 消息工具

```typescript
createMessageTool({
  sessionKey: "agent:main:main",
  channel: "telegram",
  to: "user123",
  accountId: "default"
})
```

### 4. 工具结果处理

工具执行结果会被添加到会话上下文，供后续 LLM 调用使用：

```typescript
// 工具结果格式
{
  type: "tool_result",
  toolCallId: "call_123",
  content: [
    {
      type: "text",
      text: "工具执行结果..."
    }
  ]
}
```

---

## 插件系统

### 1. 插件架构

**位置**: `src/plugins/`

OpenClaw 的插件系统支持：

- **扩展功能**: 添加新的渠道、工具、服务
- **Hook 系统**: 在关键事件点注入自定义逻辑
- **HTTP 端点**: 为插件提供 HTTP API
- **服务发现**: 插件可以注册和发现服务

### 2. 插件发现

**位置**: `src/plugins/discovery.ts`

```typescript
export async function discoverPlugins(params: {
  config: OpenClawConfig;
  stateDir: string;
}): Promise<PluginManifest[]> {
  const plugins: PluginManifest[] = [];
  
  // 1. 从扩展目录加载
  const extensionsDir = path.join(params.stateDir, "extensions");
  const extensionPlugins = await loadPluginsFromDir(extensionsDir);
  plugins.push(...extensionPlugins);
  
  // 2. 从配置的插件目录加载
  const extraDirs = params.config.plugins?.load?.extraDirs ?? [];
  for (const dir of extraDirs) {
    const dirPlugins = await loadPluginsFromDir(dir);
    plugins.push(...dirPlugins);
  }
  
  // 3. 验证插件清单
  return plugins.filter(plugin => validatePluginManifest(plugin));
}
```

### 3. 插件清单

**位置**: `src/plugins/manifest.ts`

```typescript
interface PluginManifest {
  id: string;
  name: string;
  version: string;
  description?: string;
  
  // 插件能力
  capabilities?: {
    channels?: string[];      // 支持的渠道
    tools?: string[];         // 提供的工具
    hooks?: string[];         // 注册的 Hook
    services?: string[];       // 提供的服务
  };
  
  // HTTP 路由
  http?: {
    routes?: Array<{
      path: string;
      method: "GET" | "POST" | "PUT" | "DELETE";
      handler: string;  // 导出函数名
    }>;
  };
  
  // 技能目录
  skills?: string[];
  
  // 配置模式
  configSchema?: JSONSchema;
}
```

### 4. 插件加载

**位置**: `src/plugins/loader.ts`

```typescript
export async function loadPlugin(manifest: PluginManifest): Promise<LoadedPlugin> {
  // 1. 加载插件模块
  const pluginModule = await import(manifest.entryPoint);
  
  // 2. 初始化插件
  const plugin = pluginModule.default ?? pluginModule;
  if (typeof plugin.initialize === "function") {
    await plugin.initialize({
      config: getPluginConfig(manifest.id),
      registerTool: (tool) => registerPluginTool(manifest.id, tool),
      registerHook: (hook) => registerPluginHook(manifest.id, hook),
      registerService: (service) => registerPluginService(manifest.id, service)
    });
  }
  
  // 3. 注册 HTTP 路由
  if (manifest.http?.routes) {
    for (const route of manifest.http.routes) {
      registerPluginRoute(manifest.id, route, pluginModule[route.handler]);
    }
  }
  
  return {
    manifest,
    instance: plugin,
    tools: getPluginTools(manifest.id),
    hooks: getPluginHooks(manifest.id)
  };
}
```

### 5. Hook 系统

**位置**: `src/plugins/hooks.ts`

Hook 允许插件在关键事件点执行自定义逻辑：

```typescript
// Hook 类型
type HookEvent = 
  | "before-agent-run"
  | "after-agent-run"
  | "before-tool-call"
  | "after-tool-call"
  | "before-message-send"
  | "after-message-send";

// 注册 Hook
registerHook({
  event: "before-agent-run",
  handler: async (context) => {
    // 修改上下文
    context.extraSystemPrompt = "Custom prompt";
    return context;
  }
});
```

---

## 技能系统

### 1. 技能加载

**位置**: `src/agents/skills/workspace.ts`

技能从多个位置加载，按优先级合并：

```typescript
function loadSkillEntries(workspaceDir: string, opts?: LoadSkillOptions): SkillEntry[] {
  // 1. 从扩展目录加载（最低优先级）
  const extraSkills = loadSkillsFromDir(extraDirs);
  
  // 2. 从内置目录加载
  const bundledSkills = loadSkillsFromDir(bundledSkillsDir);
  
  // 3. 从托管目录加载
  const managedSkills = loadSkillsFromDir(managedSkillsDir);
  
  // 4. 从工作区目录加载（最高优先级）
  const workspaceSkills = loadSkillsFromDir(workspaceSkillsDir);
  
  // 5. 合并（高优先级覆盖低优先级）
  const merged = new Map<string, Skill>();
  for (const skill of [...extraSkills, ...bundledSkills, ...managedSkills, ...workspaceSkills]) {
    merged.set(skill.name, skill);
  }
  
  return Array.from(merged.values()).map(skill => ({
    skill,
    frontmatter: parseFrontmatter(skill.filePath),
    metadata: resolveOpenClawMetadata(frontmatter),
    invocation: resolveSkillInvocationPolicy(frontmatter)
  }));
}
```

### 2. 技能结构

每个技能是一个目录，包含：

```
skill-name/
├── SKILL.md          # 技能说明（YAML frontmatter + Markdown）
├── scripts/          # 可执行脚本（可选）
├── assets/           # 资源文件（可选）
└── ...
```

**SKILL.md 示例**:

```markdown
---
name: github
description: Interact with GitHub using the `gh` CLI
metadata:
  openclaw:
    emoji: "🐙"
    homepage: "https://github.com"
requires:
  binary: ["gh"]
---

# GitHub Skill

Use this skill to interact with GitHub repositories, issues, and pull requests.

## Commands

- `gh issue list` - List issues
- `gh pr create` - Create a pull request
...
```

### 3. 技能快照

**位置**: `src/agents/skills/workspace.ts`

技能快照包含所有可用技能的元数据和指令：

```typescript
export function buildWorkspaceSkillSnapshot(
  workspaceDir: string,
  opts?: BuildSkillSnapshotOptions
): SkillSnapshot {
  const entries = opts?.entries ?? loadSkillEntries(workspaceDir, opts);
  
  // 过滤技能（基于配置、环境、二进制存在性）
  const filtered = entries.filter(entry => 
    shouldIncludeSkill({ entry, config: opts?.config })
  );
  
  // 构建快照
  return {
    prompt: buildSkillPrompt(filtered),
    skills: filtered.map(entry => ({
      name: entry.skill.name,
      description: entry.skill.description,
      filePath: entry.skill.filePath,
      baseDir: entry.skill.baseDir
    }))
  };
}
```

### 4. 技能调用

**位置**: `src/auto-reply/reply/get-reply-inline-actions.ts`

当 Agent 决定使用技能时：

```typescript
async function handleSkillInvocation(params: {
  skillInvocation: SkillInvocation;
  tools: AnyAgentTool[];
}) {
  const { skillInvocation, tools } = params;
  
  // 1. 检查是否有直接工具分发
  if (skillInvocation.command.dispatch?.kind === "tool") {
    const tool = tools.find(t => t.name === skillInvocation.command.dispatch.toolName);
    if (tool) {
      const result = await tool.execute(toolCallId, skillInvocation.args);
      return { kind: "reply", reply: { text: extractTextFromToolResult(result) } };
    }
  }
  
  // 2. 否则，将技能指令注入到消息中
  const promptParts = [
    `Use the "${skillInvocation.command.skillName}" skill for this request.`,
    skillInvocation.args ? `User input:\n${skillInvocation.args}` : null
  ];
  const rewrittenBody = promptParts.filter(Boolean).join("\n\n");
  
  // 3. 重新处理消息（Agent 会读取技能文件）
  return await processMessageWithSkill(rewrittenBody, skillInvocation.command.skillName);
}
```

---

## 渠道集成

### 1. 渠道架构

每个渠道是一个独立的扩展，实现统一的接口：

```typescript
interface ChannelPlugin {
  id: string;
  name: string;
  
  // 启动渠道
  start: (config: ChannelConfig) => Promise<ChannelRuntime>;
  
  // 停止渠道
  stop: () => Promise<void>;
  
  // 发送消息
  send: (params: SendParams) => Promise<SendResult>;
  
  // 状态查询
  status: () => ChannelStatus;
}
```

### 2. 渠道管理器

**位置**: `src/gateway/server-channels.ts`

```typescript
export function createChannelManager(params: {
  cfg: OpenClawConfig;
  runtime: RuntimeEnv;
}): ChannelManager {
  const channels = new Map<string, ChannelRuntime>();
  
  return {
    // 启动所有配置的渠道
    async start() {
      const channelConfigs = listChannelConfigs(params.cfg);
      for (const config of channelConfigs) {
        const plugin = loadChannelPlugin(config.channel);
        const runtime = await plugin.start(config);
        channels.set(config.channel, runtime);
      }
    },
    
    // 停止所有渠道
    async stop() {
      for (const [id, runtime] of channels) {
        await runtime.stop();
      }
    },
    
    // 获取渠道运行时
    get(channelId: string): ChannelRuntime | undefined {
      return channels.get(channelId);
    }
  };
}
```

### 3. 消息处理流程

当渠道收到消息时：

```typescript
// 1. 渠道接收消息
channel.on("message", async (rawMessage) => {
  
  // 2. 解析消息
  const parsed = parseChannelMessage(rawMessage);
  
  // 3. 路由到 Agent
  const route = resolveAgentRoute({
    cfg,
    channel: parsed.channel,
    accountId: parsed.accountId,
    peer: { kind: parsed.chatType, id: parsed.peerId }
  });
  
  // 4. 构建消息上下文
  const ctx = buildInboundContext({
    Body: parsed.text,
    From: parsed.from,
    To: parsed.to,
    SessionKey: route.sessionKey,
    Channel: parsed.channel,
    // ...
  });
  
  // 5. 处理消息（触发 Agent 或命令）
  await handleInboundMessage(ctx, route);
});
```

### 4. 渠道实现示例

以 Telegram 为例：

**位置**: `src/telegram/`

```typescript
// 使用 grammY 库
import { Bot, Context } from "grammy";

export function createTelegramChannel(config: TelegramConfig): ChannelPlugin {
  const bot = new Bot(config.botToken);
  
  // 监听消息
  bot.on("message", async (ctx: Context) => {
    const message = ctx.message;
    
    // 构建消息上下文
    const inboundCtx = {
      Body: message.text ?? "",
      From: `telegram:user:${message.from.id}`,
      To: message.chat.type === "private" 
        ? `telegram:user:${message.from.id}`
        : `telegram:group:${message.chat.id}`,
      SessionKey: buildSessionKey(message.chat),
      Channel: "telegram",
      // ...
    };
    
    // 路由到 Agent
    await routeToAgent(inboundCtx);
  });
  
  return {
    id: "telegram",
    start: async () => {
      await bot.start();
      return { bot, status: "connected" };
    },
    stop: async () => {
      await bot.stop();
    },
    send: async (params) => {
      await bot.api.sendMessage(params.to, params.text);
      return { ok: true };
    }
  };
}
```

---

## 会话管理实现

### 1. 会话初始化

**位置**: `src/auto-reply/reply/session.ts`

```typescript
export async function initSessionState(params: {
  ctx: MsgContext;
  cfg: OpenClawConfig;
}): Promise<SessionInitResult> {
  const { ctx, cfg } = params;
  
  // 1. 解析会话键
  const sessionKey = resolveSessionKey(ctx);
  const agentId = resolveSessionAgentId(sessionKey);
  
  // 2. 加载会话存储
  const storePath = resolveStorePath(cfg.session?.store, { agentId });
  const sessionStore = loadSessionStore(storePath);
  
  // 3. 检查重置条件
  const resetTriggers = cfg.session?.resetTriggers ?? DEFAULT_RESET_TRIGGERS;
  const shouldReset = evaluateSessionFreshness({
    entry: sessionStore[sessionKey],
    resetTriggers,
    now: Date.now()
  });
  
  // 4. 创建或加载会话
  let sessionEntry: SessionEntry;
  let isNewSession = false;
  
  if (shouldReset || !sessionStore[sessionKey]) {
    // 创建新会话
    const sessionId = crypto.randomUUID();
    sessionEntry = {
      sessionId,
      updatedAt: Date.now(),
      systemSent: false,
      // ...
    };
    isNewSession = true;
  } else {
    // 使用现有会话
    sessionEntry = sessionStore[sessionKey];
  }
  
  // 5. 更新会话存储
  updateSessionStore(storePath, {
    [sessionKey]: sessionEntry
  });
  
  // 6. 解析会话文件路径
  const sessionFile = resolveSessionFilePath(sessionEntry.sessionId, sessionEntry);
  
  return {
    sessionKey,
    sessionId: sessionEntry.sessionId,
    sessionEntry,
    isNewSession,
    storePath,
    sessionFile,
    // ...
  };
}
```

### 2. 会话记录格式

**位置**: `src/config/sessions/`

会话记录使用 JSONL 格式（每行一个 JSON 对象）：

```jsonl
{"type":"session","id":"abc123","timestamp":"2026-02-06T10:00:00Z","cwd":"/workspace"}
{"type":"message","id":"msg1","parentId":null,"message":{"role":"user","content":"Hello"}}
{"type":"message","id":"msg2","parentId":"msg1","message":{"role":"assistant","content":"Hi!"}}
{"type":"tool_call","id":"tool1","parentId":"msg2","toolCallId":"call_123","name":"read","args":{"path":"file.txt"}}
{"type":"tool_result","id":"tool1_result","parentId":"tool1","toolCallId":"call_123","content":[{"type":"text","text":"file content"}]}
{"type":"compaction","id":"comp1","firstKeptEntryId":"msg2","tokensBefore":5000,"summary":"Previous conversation summary"}
```

### 3. 会话压缩

当会话上下文过长时，OpenClaw 会自动压缩：

```typescript
async function compactSession(sessionManager: SessionManager): Promise<void> {
  // 1. 检查是否需要压缩
  const contextTokens = sessionManager.getContextTokens();
  if (contextTokens < COMPACTION_THRESHOLD) {
    return;
  }
  
  // 2. 选择保留的消息数量
  const keepMessages = 10;  // 保留最近 10 条消息
  
  // 3. 生成压缩摘要
  const summary = await generateCompactionSummary({
    messages: sessionManager.getOldMessages(keepMessages),
    model: resolveModel(cfg)
  });
  
  // 4. 写入压缩记录
  sessionManager.addCompaction({
    firstKeptEntryId: sessionManager.getMessageId(keepMessages),
    tokensBefore: contextTokens,
    summary
  });
  
  // 5. 删除旧消息（保留在 JSONL 中，但标记为已压缩）
  sessionManager.markAsCompacted(keepMessages);
}
```

---

## 数据流与状态管理

### 1. 消息流

```
[渠道] 收到消息
    │
    ▼
[Channel Manager] 解析消息
    │
    ▼
[Routing] 路由到 Agent
    │
    ▼
[Session Manager] 初始化/加载会话
    │
    ▼
[Agent Runtime] 执行 Agent
    │
    ├─→ [Memory Search] 检索相关记忆
    ├─→ [LLM] 生成响应
    ├─→ [Tool Execution] 执行工具调用
    └─→ [Response Generation] 生成最终回复
    │
    ▼
[Reply Router] 路由回复
    │
    ▼
[Channel] 发送消息
```

### 2. 事件流

Gateway 使用事件系统进行组件间通信：

```typescript
// 1. Agent 事件
onAgentEvent((event) => {
  // 广播到所有连接的客户端
  broadcast("agent", {
    stream: event.stream,
    data: event.data,
    runId: event.runId,
    sessionKey: event.sessionKey
  });
});

// 2. 聊天事件
onChatEvent((event) => {
  broadcast("chat", {
    sessionKey: event.sessionKey,
    message: event.message
  });
});

// 3. 健康事件
onHealthEvent((event) => {
  broadcast("health", {
    version: incrementHealthVersion(),
    status: event.status
  });
});
```

### 3. 状态同步

Gateway 维护多个状态缓存：

```typescript
// 健康状态缓存
const healthCache = {
  version: 0,
  status: {
    gateway: "running",
    channels: { /* ... */ },
    agents: { /* ... */ }
  }
};

// 存在状态缓存
const presenceCache = {
  version: 0,
  clients: new Set<GatewayWsClient>()
};

// 定期刷新
setInterval(() => {
  refreshGatewayHealthSnapshot();
  incrementPresenceVersion();
}, 5000);
```

### 4. 并发控制

OpenClaw 使用会话队列确保同一会话的请求串行执行：

```typescript
// 会话队列
const sessionQueues = new Map<string, PromiseQueue>();

async function queueAgentRun(sessionKey: string, run: () => Promise<void>) {
  let queue = sessionQueues.get(sessionKey);
  if (!queue) {
    queue = new PromiseQueue();
    sessionQueues.set(sessionKey, queue);
  }
  
  return queue.enqueue(run);
}
```

---

## 总结

OpenClaw 的架构设计体现了以下特点：

### 核心设计原则

1. **中心化 Gateway**: 所有组件通过 Gateway 协调，简化了系统复杂度
2. **事件驱动**: 使用 WebSocket 事件进行实时通信
3. **插件化**: 渠道、工具、服务都通过插件系统扩展
4. **本地优先**: 数据默认存储在本地，保护隐私
5. **多智能体**: 支持多个独立的智能体实例

### 技术亮点

- **WebSocket 协议**: 类型化的请求/响应/事件协议
- **混合搜索**: 结合向量搜索和关键词搜索的记忆系统
- **会话管理**: 智能的会话隔离和压缩机制
- **工具系统**: 丰富的内置工具和扩展能力
- **技能系统**: 灵活的技能加载和调用机制

### 扩展性

- **插件系统**: 可以轻松添加新的渠道、工具、服务
- **技能系统**: 通过 Markdown 文件定义技能，易于创建和分享
- **Hook 系统**: 在关键事件点注入自定义逻辑
- **多智能体**: 支持复杂的多智能体场景

---

**文档版本**: 1.0  
**最后更新**: 2026-02-06  
**维护者**: 基于源代码分析生成

