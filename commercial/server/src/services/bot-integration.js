import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { getDb } from "../db.js";
import * as tunnel from "../tunnel/client-api.js";
import { OPENCLAW_DIR } from "../paths.js";

const __bot_int_dirname = path.dirname(fileURLToPath(import.meta.url));
const COMMERCIAL_RULES_PATH = path.resolve(__bot_int_dirname, "../../COMMERCIAL_MODE_RULES.md");
// Per-order "live draft" snapshot. Written right before every refine call
// so the bot can Read it on demand to see the most up-to-date state of the
// draft (including any inline edits the client made in the UI between turns).
// The path is stable per order so the prompt that references it stays
// byte-identical across turns — the prefix remains cache-friendly.
const DRAFT_LIVE_DIR = path.join(OPENCLAW_DIR, "commercial", "draft-live");

function writeCurrentDraftSnapshot(orderId) {
  try {
    if (!fs.existsSync(DRAFT_LIVE_DIR)) {
      fs.mkdirSync(DRAFT_LIVE_DIR, { recursive: true });
    }
    const db = getDb();
    const latest = db
      .prepare(
        `SELECT version, status, title, content, card_text, fact_check, tags, image_style,
                generated_at, revision_note
         FROM drafts
         WHERE order_id = ?
         ORDER BY version DESC
         LIMIT 1`
      )
      .get(orderId);
    const snapshot = latest
      ? {
          order_id: orderId,
          version: latest.version,
          status: latest.status,
          title: latest.title,
          content: latest.content,
          card_text: latest.card_text,
          fact_check: latest.fact_check || "",
          tags: (() => { try { return JSON.parse(latest.tags || "[]"); } catch { return []; } })(),
          image_style: latest.image_style,
          generated_at: latest.generated_at,
          last_client_instruction: latest.revision_note || null,
          written_at: new Date().toISOString(),
          note: "This is the live current draft as stored in the commercial DB. If the client has inline-edited any field in the UI, those edits are reflected here. Prefer this over your own session memory for the current state.",
        }
      : {
          order_id: orderId,
          version: 0,
          status: "none",
          note: "No draft has been generated yet for this order.",
          written_at: new Date().toISOString(),
        };
    const filePath = path.join(DRAFT_LIVE_DIR, `${orderId}.json`);
    fs.writeFileSync(filePath, JSON.stringify(snapshot, null, 2));
    return filePath;
  } catch (err) {
    console.error(`[bot-integration] Failed to write draft-live snapshot for order ${orderId}:`, err.message);
    return null;
  }
}

/**
 * Load the commercial-mode system rules from the MD file on every call.
 * Editing COMMERCIAL_MODE_RULES.md takes effect on the next order invocation —
 * no server restart needed.
 *
 * If the file is missing or unreadable, fall back to a minimal safe ruleset
 * so orders still run without leaking memory / triggering publishes.
 */
function loadSkillContext(botId, skillId) {
  if (!skillId) return "";
  const wsDir = path.join(OPENCLAW_DIR, `workspace-${botId}`);
  const skillMdPath = path.join(wsDir, "skills", skillId, "SKILL.md");

  let skillContent = "";
  try {
    skillContent = fs.readFileSync(skillMdPath, "utf8");
  } catch {
    return "";
  }

  return `\n【指定服务 Skill】\n本订单指定了 skill: ${skillId}\n请先执行 Read("skills/${skillId}/SKILL.md") 读取完整的 Skill 工作流，然后严格按照其中的分步流程逐步执行。\n⚠️ 不要跳过任何步骤，每个 "现在读" 标记的文件都必须实际 Read。\n\n---\n`;
}

function loadCommercialRules(botId) {
  if (botId) {
    const botSpecificPath = path.resolve(__bot_int_dirname, `../../COMMERCIAL_MODE_RULES_${botId.toUpperCase()}.md`);
    try {
      return fs.readFileSync(botSpecificPath, "utf8").trim();
    } catch {}
  }
  try {
    return fs.readFileSync(COMMERCIAL_RULES_PATH, "utf8").trim();
  } catch (err) {
    console.error(`[bot-integration] Failed to load COMMERCIAL_MODE_RULES.md: ${err.message}. Using fallback rules.`);
    return `【商单模式 · 降级规则】
1. 禁止写入长期 memory(MEMORY.md / 日记 / 专题文件)
2. 禁止提及其他客户信息
3. 禁止调用任何发布类工具(publish_content 等)
4. 禁止 Bash / Write / Edit / Task / 小红书 MCP
5. 只产出 JSON 草稿`;
  }
}

function buildGuidanceSection(order) {
  const parts = [];
  if (order.guidance) parts.push(order.guidance);
  if (parts.length === 0) return "";
  return `【运营指导方案 — 运营部为本单制定的创作指引,请严格遵照执行】\n${parts.join("\n\n")}\n\n`;
}

function buildClientSysPromptSection(clientId) {
  const db = getDb();
  const client = db.prepare("SELECT sys_prompt FROM clients WHERE id = ?").get(clientId);
  if (!client?.sys_prompt) return "";
  return `【客户公司规范 — 该客户所属公司的额外要求】\n${client.sys_prompt}\n\n`;
}

const GZH_BOTS = new Set(["bot9"]);

function getRefineTaskLine(botId) {
  if (GZH_BOTS.has(botId)) {
    return "【商单任务】你正在为一个商单客户撰写公众号文章。客户每一次发来的消息都是对当前文章的新需求或修改意见。你必须严格按 JSON 契约输出一份完整文章(不是对话,不是解释)。";
  }
  return "【商单任务】你正在为一个商单客户迭代小红书草稿。客户每一次发来的消息都是对当前草稿的新需求或修改意见。你必须严格按 JSON 契约输出一份完整草稿(不是对话,不是解释)。";
}

function getInitialTaskLine(botId) {
  if (GZH_BOTS.has(botId)) {
    return "你收到了一个商单任务。请以你的人设风格撰写一篇公众号文章。";
  }
  return "你收到了一个商单任务。请以你的人设风格生成一篇小红书帖子。";
}

function getDraftJsonTemplate(botId) {
  if (GZH_BOTS.has(botId)) {
    return `{
  "title": "文章标题(≤30字)",
  "content": "文章正文(Markdown 格式,含完整可发布内容 + 风险提示)",
  "card_text": "引用来源 + 自检报告(不发布,供审稿参考)",
  "fact_check": "数据核查报告(逐条核实文中数据和事实,表格形式)"
}`;
  }
  return `{
  "title": "标题(不超过20字)",
  "content": "正文内容",
  "card_text": "如果是 text_to_image 模式,这里写卡片文字,否则留空",
  "tags": ["标签1", "标签2", "标签3"],
  "image_style": "基础"
}`;
}

function getFactCheckGate(botId, skillId) {
  if (!GZH_BOTS.has(botId) || !skillId) return "";
  return `

⛔ 输出 JSON 前的必经门禁 —— fact-check 是一个独立 Skill
写完文章后、输出上面 JSON 之前，你必须：
(1) 执行 Read("skills/fact-check/SKILL.md") 读取 fact-check 技能的完整流程
(2) 严格按照该 Skill 的步骤逐条执行（含工具调用）
fact-check 不是脑子里想想就行的"自检"——它是一个有独立 SKILL.md 文件的技能，需要真实的工具调用。
没有 Read 过 fact-check/SKILL.md、没有执行其中工具调用的 fact_check 字段 = 伪造，产出无效。`;
}

// ============================================================================
// Two-pass fact-check enforcement
//
// After the bot outputs its JSON, we scan the session JSONL for evidence that
// fact-check verification tool calls actually happened. If not, we send a
// second message in the same session forcing the bot to execute fact-check.
// ============================================================================

const FACT_CHECK_VERIFICATION_TOOLS = new Set([
  "market_overview", "get_ashares_gvix",
  "get_fund_comprehensive_analysis",
  "research_search",
]);

function needsFactCheckEnforcement(botId, skillId) {
  return GZH_BOTS.has(botId) && !!skillId;
}

/**
 * Scan a session JSONL file for fact-check tool calls.
 * Returns { readSkill: boolean, hasVerificationCalls: boolean }.
 *
 * "readSkill" = bot read skills/fact-check/SKILL.md
 * "hasVerificationCalls" = after reading the skill, bot made at least one
 *   verification tool call (research-mcp market data, web_fetch, curl, etc.)
 */
function scanSessionForFactCheck(sessionJsonlPath) {
  const result = { readSkill: false, hasVerificationCalls: false };
  let content;
  try {
    if (tunnel.isConnected()) {
      return result; // tunnel mode: fall back to stdout-based detection
    }
    content = fs.readFileSync(sessionJsonlPath, "utf8");
  } catch {
    return result;
  }

  const lines = content.split("\n").filter(Boolean);
  let factCheckReadSeen = false;

  for (const line of lines) {
    let evt;
    try { evt = JSON.parse(line); } catch { continue; }
    if (evt?.type !== "message") continue;
    const msg = evt.message;
    if (!msg || msg.role !== "assistant" || !Array.isArray(msg.content)) continue;

    for (const item of msg.content) {
      if (item?.type !== "toolCall") continue;

      // Detect Read("skills/fact-check/SKILL.md")
      if (!factCheckReadSeen && item.name === "Read") {
        const fp = item.arguments?.file_path || item.arguments?.filePath || "";
        if (fp.includes("fact-check") && fp.includes("SKILL.md")) {
          factCheckReadSeen = true;
          result.readSkill = true;
        }
      }

      // After reading fact-check skill, look for verification tool calls
      if (factCheckReadSeen) {
        const toolName = (item.name || "").toLowerCase();
        // research-mcp tools
        if (FACT_CHECK_VERIFICATION_TOOLS.has(item.name)) {
          result.hasVerificationCalls = true;
        }
        // web_fetch / webfetch
        if (toolName === "webfetch" || toolName === "web_fetch") {
          result.hasVerificationCalls = true;
        }
        // curl via Bash
        if (toolName === "bash") {
          const cmd = item.arguments?.command || "";
          if (cmd.includes("curl") || cmd.includes("pdftotext")) {
            result.hasVerificationCalls = true;
          }
        }
      }
    }
  }

  return result;
}

const FACT_CHECK_FORCE_MESSAGE = `⛔ 你刚才输出了文章 JSON，但 fact-check 验证步骤没有执行。

你的 session 中没有出现 fact-check 所需的验证工具调用（research-mcp / web_fetch / curl 等）。
现在你必须补做 fact-check：

1. Read("skills/fact-check/SKILL.md") — 如果你还没读过
2. 严格按照 fact-check Skill 的流程逐步执行验证（含真实的工具调用）
3. 验证完成后，输出修正后的完整 JSON（同样的 JSON 格式，包含更新后的 fact_check 字段）

⛔ 这是最后一次机会。如果这次还不执行 fact-check 工具调用，产出将被标记为无效。`;

/**
 * Run a second agent pass in the same session to force fact-check execution.
 * Returns { stdout } or { error }.
 */
async function runFactCheckPass(botId, sessionId, timeoutMs = 600000) {
  const agentArgs = [
    "agent",
    "--agent", botId,
    "--session-id", sessionId,
    "-m", FACT_CHECK_FORCE_MESSAGE,
    "--json",
    "--timeout", "600",
  ];

  console.log(`[bot-integration] fact-check enforcement: sending second pass for session=${sessionId}`);

  if (tunnel.isConnected()) {
    try {
      const res = await tunnel.exec("openclaw", agentArgs, { timeout: timeoutMs });
      if (res.error) return { error: res.error };
      return res.code === 0 ? { stdout: res.stdout } : { error: res.stderr || `exit ${res.code}` };
    } catch (err) {
      return { error: err.message };
    }
  }

  return new Promise((resolve) => {
    const child = spawn("openclaw", agentArgs, {
      stdio: ["ignore", "pipe", "pipe"],
      detached: true,
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));
    let done = false;
    const timer = setTimeout(() => {
      if (done) return;
      done = true;
      try { process.kill(-child.pid, "SIGKILL"); } catch {}
      resolve({ error: "timeout" });
    }, timeoutMs);
    child.on("close", (code) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      resolve(code === 0 ? { stdout } : { error: stderr || `exit ${code}` });
    });
    child.unref();
  });
}

function getLiveDraftHint(botId) {
  if (GZH_BOTS.has(botId)) {
    return `- 上面这个 JSON 文件里存着客户侧最新的文章状态(包括客户在前端直接手改的标题/正文/tags)。
- 如果你记得上一轮自己输出的内容跟客户本轮指令不冲突,可以直接基于对话记忆改,不必 Read。
- 如果客户本轮指令暗示了"上次你给的 XX 我改了...""现在标题是 XX""保留我改过的那段"等 ——
  说明客户手动改过文章,**必须先用 Read 工具读这个文件**,以文件里的内容为当前版本基准再改,
  而不是以你 session 记忆里上一轮吐出的版本为基准。`;
  }
  return `- 上面这个 JSON 文件里存着客户侧最新的草稿状态(包括客户在前端直接手改的标题/正文/tags/card_text)。
- 如果你记得上一轮自己输出的内容跟客户本轮指令不冲突,可以直接基于对话记忆改,不必 Read。
- 如果客户本轮指令暗示了"上次你给的 XX 我改了...""现在标题是 XX""保留我改过的那段"等 ——
  说明客户手动改过草稿,**必须先用 Read 工具读这个文件**,以文件里的内容为当前版本基准再改,
  而不是以你 session 记忆里上一轮吐出的版本为基准。`;
}

/**
 * Spawn `openclaw agent` and return stdout/stderr.
 * When tunnel is connected, delegates execution to the office machine.
 * Falls back to local spawn for development/debugging.
 */
function runAgent(args, timeoutMs = 600000) {
  if (tunnel.isConnected()) {
    return tunnel.exec("openclaw", args, { timeout: timeoutMs })
      .then((res) => {
        if (res.error) return { error: res.error, stderr: (res.stderr || "").slice(0, 500) };
        return res.code === 0
          ? { stdout: res.stdout }
          : { error: (res.stderr || `exit ${res.code}`).slice(0, 500) };
      })
      .catch((err) => ({ error: err.message }));
  }

  return new Promise((resolve) => {
    const child = spawn("openclaw", args, {
      stdio: ["ignore", "pipe", "pipe"],
      detached: true,
    });

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));

    let done = false;
    const finish = (result) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      try {
        process.kill(-child.pid, "SIGKILL");
      } catch {}
      resolve(result);
    };

    const timer = setTimeout(() => {
      finish({ error: "timeout", stderr: stderr.slice(0, 500) });
    }, timeoutMs);

    child.on("close", (code) => {
      finish(
        code === 0
          ? { stdout }
          : { error: (stderr || `exit ${code}`).slice(0, 500) }
      );
    });

    child.unref();
  });
}

/**
 * Read materials and return { texts, imagePaths }.
 * - Text files: content is read inline
 * - Image files: absolute path is returned so the bot can Read them
 */
function readMaterials(orderId, snapshot) {
  const materials = snapshot?.materials || getDb()
    .prepare("SELECT * FROM order_materials WHERE order_id = ? ORDER BY sort_order ASC, id ASC")
    .all(orderId);
  const texts = [];
  const imagePaths = [];
  for (const material of materials) {
    if (material.file_type.startsWith("text/")) {
      if (typeof material.text_content === "string" && material.text_content.length > 0) {
        texts.push(material.text_content);
        continue;
      }
      try {
        texts.push(fs.readFileSync(material.file_path, "utf8"));
      } catch {}
    } else if (material.file_type.startsWith("image/")) {
      imagePaths.push(material.file_path);
    }
  }
  return { texts, imagePaths };
}

// ============================================================================
// Streaming helpers — tail the openclaw session JSONL file and emit user-facing
// tool-call events so the commercial UI can show a live "正在调用 X" status.
//
// OpenClaw has no --stream CLI mode, but it writes every toolCall/toolResult
// to agents/<botId>/sessions/<sessionUUID>.jsonl as it happens. The mapping
// from our sessionKey (agent:botN:commercial:order:<uuid>) to the actual
// sessionUUID lives in agents/<botId>/sessions/sessions.json (keyed by the
// full sessionKey).
// ============================================================================

const SESSIONS_JSON_WAIT_MS = 4000;
const TAIL_POLL_INTERVAL_MS = 200;

export async function waitForSessionJsonlPath(botId, sessionKey, timeoutMs = SESSIONS_JSON_WAIT_MS) {
  const sessionsDir = path.join(OPENCLAW_DIR, "agents", botId, "sessions");
  const storeFile = path.join(sessionsDir, "sessions.json");
  const deadline = Date.now() + timeoutMs;

  const readStoreFile = async () => {
    if (tunnel.isConnected()) {
      try {
        const res = await tunnel.readFile(storeFile);
        return JSON.parse(res.content);
      } catch { return null; }
    }
    try { return JSON.parse(fs.readFileSync(storeFile, "utf8")); } catch { return null; }
  };

  while (Date.now() < deadline) {
    const store = await readStoreFile();
    const entry = store?.[sessionKey];
    if (entry) {
      if (entry.sessionFile) return entry.sessionFile;
      if (entry.sessionId) return path.join(sessionsDir, `${entry.sessionId}.jsonl`);
    }
    await new Promise((r) => setTimeout(r, 150));
  }
  return null;
}

export function buildToolPreview(name, args) {
  if (!args || typeof args !== "object") return "";
  try {
    const lname = String(name || "").toLowerCase();
    if (lname === "read") {
      const p = args.file_path || args.filePath || args.path || "";
      if (!p) return "";
      // Show parent-dir/filename so skill SKILL.md reads are distinguishable
      // (e.g. "research-stock/SKILL.md" instead of just "SKILL.md").
      const parts = p.split("/").filter(Boolean);
      return parts.length >= 2 ? parts.slice(-2).join("/") : parts[0] || "";
    }
    if (lname === "grep" || lname === "glob") return args.pattern || "";
    if (lname === "websearch" || lname === "web_search") return args.query || "";
    if (lname === "webfetch" || lname === "web_fetch") return args.url || "";
    if (lname === "todowrite") return "规划任务";
    if (lname === "skill") return args.skill || args.name || "";
    for (const v of Object.values(args)) {
      if (typeof v === "string" && v.length > 0 && v.length < 120) return v;
    }
    return "";
  } catch {
    return "";
  }
}

export function handleJsonlLine(line, onEvent) {
  let evt;
  try { evt = JSON.parse(line); } catch { return; }
  if (evt?.type !== "message") return;
  const msg = evt.message;
  if (!msg || msg.role !== "assistant" || !Array.isArray(msg.content)) return;
  for (const item of msg.content) {
    if (item?.type === "toolCall" && item.name) {
      onEvent({
        type: "tool_use",
        tool: item.name,
        preview: buildToolPreview(item.name, item.arguments),
      });
    }
  }
}

export function tailSessionJsonl(filePath, onEvent) {
  // Tunnel mode: delegate file tailing to the office machine
  if (tunnel.isConnected()) {
    return tunnel.tailFile(filePath, (line) => {
      handleJsonlLine(line, onEvent);
    });
  }

  // Local mode
  let lastSize = 0;
  try { lastSize = fs.statSync(filePath).size; } catch { lastSize = 0; }
  let buffer = "";
  let stopped = false;

  const drainOnce = () => {
    let stat;
    try { stat = fs.statSync(filePath); } catch { return; }
    if (stat.size <= lastSize) return;
    let fd;
    try {
      fd = fs.openSync(filePath, "r");
      const len = stat.size - lastSize;
      const buf = Buffer.alloc(len);
      fs.readSync(fd, buf, 0, len, lastSize);
      lastSize = stat.size;
      buffer += buf.toString("utf8");
    } catch { return; }
    finally { if (fd !== undefined) { try { fs.closeSync(fd); } catch {} } }

    let idx;
    while ((idx = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 1);
      if (line) handleJsonlLine(line, onEvent);
    }
  };

  const interval = setInterval(() => {
    if (stopped) return;
    drainOnce();
  }, TAIL_POLL_INTERVAL_MS);

  return () => {
    stopped = true;
    clearInterval(interval);
    drainOnce();
  };
}

/**
 * Streaming variant of refineDraftViaChat. Same behavior and return shape
 * ({ draft } | { error }), but emits live tool-call events via the onEvent
 * callback while the bot is running. Used by the SSE /refine endpoint.
 */
export async function refineDraftViaChatStreaming(order, sessionId, clientInstruction, { onEvent, snapshot = null } = {}) {
  const sourceOrder = snapshot?.order || order;
  const { texts, imagePaths } = readMaterials(order.id, snapshot);
  const refLinks = Array.isArray(sourceOrder.reference_links)
    ? sourceOrder.reference_links
    : JSON.parse(sourceOrder.reference_links || "[]");

  writeCurrentDraftSnapshot(order.id);

  let materialsSection = "";
  if (texts.length > 0) {
    materialsSection += `【文字素材】\n${texts.join("\n---\n")}\n\n`;
  }
  if (imagePaths.length > 0) {
    materialsSection += `【图片素材】\n请先用 Read 工具查看以下图片,了解素材内容后再创作:\n${imagePaths.map((p) => `- ${p}`).join("\n")}\n\n`;
  }

  const commercialRules = loadCommercialRules(order.bot_id);
  const skillContext = loadSkillContext(order.bot_id, sourceOrder.skill_id);
  const guidanceSection = buildGuidanceSection(sourceOrder);
  const clientSysPromptSection = buildClientSysPromptSection(order.client_id);
  const message = `${commercialRules}

---
${skillContext}
${getRefineTaskLine(order.bot_id)}

${clientSysPromptSection}${guidanceSection}【客户要求 (订单原始需求,整个对话期间不变)】
${sourceOrder.requirements}

${materialsSection}${refLinks.length > 0 ? `【参考链接】\n${refLinks.join("\n")}\n\n` : ""}【内容类型】${sourceOrder.content_type}

${clientInstruction.trim() !== sourceOrder.requirements?.trim() ? `【客户本轮指令】\n${clientInstruction}\n` : ""}
【硬性约束】
1. 必须严格输出以下 JSON 格式,不要包含其他任何文字、解释、前置语或寒暄,直接给 JSON。
2. 如果本轮是修改意见,请基于我们对话历史中最近一版草稿改,保留未被要求改动的部分。
3. 保持你一贯的人设风格。
4. 保持原文中的标点符号不变。如果 JSON 字符串内部出现 ASCII 双引号 “，用反斜杠转义为 \”。

${getDraftJsonTemplate(order.bot_id)}${getFactCheckGate(order.bot_id, sourceOrder.skill_id)}`;

  const agentArgs = [
    "agent",
    "--agent", order.bot_id,
    "--session-id", sessionId,
    "-m", message,
    "--json",
    "--timeout", "600",
  ];

  console.log(`[bot-integration] Refining (streaming) order=${order.id} session=${sessionId} tunnel=${tunnel.isConnected()}`);

  // Kick off session-file resolution + tailing in the background. Tail
  // failures are non-fatal: the main run still completes, we just miss
  // tool-call events.
  let stopTail = null;
  let eventCount = 0;
  const tailStartTime = Date.now();
  const tailPromise = waitForSessionJsonlPath(order.bot_id, sessionId)
    .then((filePath) => {
      if (!filePath) {
        console.error(`[bot-integration] stream: session file not registered in time for ${sessionId}`);
        return;
      }
      const resolveTimeMs = Date.now() - tailStartTime;
      console.error(`[bot-integration] stream: tail starting file=${path.basename(filePath)} resolveMs=${resolveTimeMs}`);
      stopTail = tailSessionJsonl(filePath, (evt) => {
        eventCount++;
        console.error(`[bot-integration] stream: tool_use #${eventCount} ${evt.tool} ${evt.preview?.slice(0, 40) || ""}`);
        try { onEvent && onEvent(evt); } catch (err) {
          console.error("[bot-integration] stream onEvent threw:", err);
        }
      });
    })
    .catch((err) => console.error("[bot-integration] stream tail setup error:", err));

  // Run agent via tunnel or locally
  let runResult;
  if (tunnel.isConnected()) {
    try {
      const res = await tunnel.exec("openclaw", agentArgs, { timeout: 600000 });
      if (res.error) {
        runResult = { error: res.error, stderr: (res.stderr || "").slice(0, 500) };
      } else {
        runResult = res.code === 0
          ? { stdout: res.stdout }
          : { error: (res.stderr || `exit ${res.code}`).slice(0, 500) };
      }
    } catch (err) {
      runResult = { error: err.message };
    }
  } else {
    const child = spawn("openclaw", agentArgs, {
      stdio: ["ignore", "pipe", "pipe"],
      detached: true,
    });

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));

    runResult = await new Promise((resolve) => {
      let done = false;
      const timer = setTimeout(() => {
        if (done) return;
        done = true;
        try { process.kill(-child.pid, "SIGKILL"); } catch {}
        resolve({ error: "timeout", stderr: stderr.slice(0, 500) });
      }, 600000);
      child.on("close", (code) => {
        if (done) return;
        done = true;
        clearTimeout(timer);
        resolve(
          code === 0
            ? { stdout }
            : { error: (stderr || `exit ${code}`).slice(0, 500) }
        );
      });
      child.unref();
    });
  }

  // Let tail setup promise settle (may be a no-op if already resolved),
  // then drain and detach.
  await tailPromise.catch(() => {});
  if (stopTail) stopTail();
  console.error(`[bot-integration] stream: finished, total events=${eventCount}`);

  if (runResult.error) {
    console.error("[bot-integration] Refine (streaming) error:", runResult.error);
    return { error: `生成失败: ${runResult.error}` };
  }
  try {
    let draft = parseAgentOutput(runResult.stdout);

    // Two-pass fact-check enforcement for GZH bots with skills
    if (needsFactCheckEnforcement(order.bot_id, sourceOrder.skill_id)) {
      const sessionJsonlPath = await waitForSessionJsonlPath(order.bot_id, sessionId, 2000);
      const fcResult = sessionJsonlPath
        ? scanSessionForFactCheck(sessionJsonlPath)
        : { readSkill: false, hasVerificationCalls: false };

      console.log(`[bot-integration] fact-check scan: readSkill=${fcResult.readSkill} hasVerification=${fcResult.hasVerificationCalls} file=${sessionJsonlPath ? path.basename(sessionJsonlPath) : "N/A"}`);

      if (!fcResult.hasVerificationCalls) {
        console.log(`[bot-integration] fact-check NOT executed — launching second pass`);
        try { onEvent?.({ type: "tool_use", tool: "fact-check-enforcement", preview: "fact-check 未执行，启动第二轮强制核查" }); } catch {}

        const pass2 = await runFactCheckPass(order.bot_id, sessionId);
        if (!pass2.error) {
          try {
            const draft2 = parseAgentOutput(pass2.stdout);
            console.log(`[bot-integration] fact-check second pass produced updated draft`);
            draft = draft2;
          } catch (e2) {
            console.error(`[bot-integration] fact-check second pass output unparseable: ${e2.message}. Keeping first draft.`);
          }
        } else {
          console.error(`[bot-integration] fact-check second pass failed: ${pass2.error}. Keeping first draft.`);
        }
      }
    }

    return { draft };
  } catch (err) {
    return { error: err.message || "无法解析 Bot 输出" };
  }
}

/**
 * Produce a new draft version by sending a client instruction to the bot
 * inside a persistent per-order session.
 *
 * This is the SINGLE pipeline through which clients interact with the bot.
 * Each call must:
 *   - Include the client's new instruction (first request or refinement)
 *   - Always force the bot to emit the JSON draft contract
 *   - Rely on openclaw gateway session memory (via --session-id) so that
 *     "make the title more lively" on turn 2 can reference turn 1's draft
 *     without re-sending full context.
 *
 * Returns { draft } on success or { error } on failure. Does NOT throw.
 */
export async function refineDraftViaChat(order, sessionId, clientInstruction, snapshot = null) {
  const sourceOrder = snapshot?.order || order;
  const { texts, imagePaths } = readMaterials(order.id, snapshot);
  const refLinks = Array.isArray(sourceOrder.reference_links)
    ? sourceOrder.reference_links
    : JSON.parse(sourceOrder.reference_links || "[]");

  // Dump the current (post-inline-edit) draft to a stable path so the bot can
  // Read it on demand. We write this EVERY turn but only reference the path
  // in the prompt — keeps the prompt prefix byte-stable across turns.
  const liveDraftPath = writeCurrentDraftSnapshot(order.id);

  let materialsSection = "";
  if (texts.length > 0) {
    materialsSection += `【文字素材】\n${texts.join("\n---\n")}\n\n`;
  }
  if (imagePaths.length > 0) {
    materialsSection += `【图片素材】\n请先用 Read 工具查看以下图片,了解素材内容后再创作:\n${imagePaths.map((p) => `- ${p}`).join("\n")}\n\n`;
  }

  const commercialRules = loadCommercialRules(order.bot_id);
  const skillContext = loadSkillContext(order.bot_id, sourceOrder.skill_id);
  const guidanceSection = buildGuidanceSection(sourceOrder);
  const clientSysPromptSection = buildClientSysPromptSection(order.client_id);
  const message = `${commercialRules}

---
${skillContext}
${getRefineTaskLine(order.bot_id)}

${clientSysPromptSection}${guidanceSection}【客户要求 (订单原始需求,整个对话期间不变)】
${sourceOrder.requirements}

${materialsSection}${refLinks.length > 0 ? `【参考链接】\n${refLinks.join("\n")}\n\n` : ""}【内容类型】${sourceOrder.content_type}

【当前草稿实时状态文件】
${liveDraftPath || `(写入失败,请完全依赖对话记忆)`}
${getLiveDraftHint(order.bot_id)}

${clientInstruction.trim() !== sourceOrder.requirements?.trim() ? `【客户本轮指令】\n${clientInstruction}\n` : ""}
【硬性约束】
1. 必须严格输出以下 JSON 格式,不要包含其他任何文字、解释、前置语或寒暄,直接给 JSON。
2. 如果本轮是修改意见,请基于我们对话历史中最近一版草稿改,保留未被要求改动的部分。
3. 保持你一贯的人设风格。
4. 保持原文中的标点符号不变。如果 JSON 字符串内部出现 ASCII 双引号 “，用反斜杠转义为 \”。

${getDraftJsonTemplate(order.bot_id)}${getFactCheckGate(order.bot_id, sourceOrder.skill_id)}`;

  const args = [
    "agent",
    "--agent", order.bot_id,
    "--session-id", sessionId,
    "-m", message,
    "--json",
    "--timeout", "600",
  ];

  console.log(`[bot-integration] Refining draft order=${order.id} session=${sessionId}`);
  const result = await runAgent(args, 600000);
  if (result.error) {
    console.error(`[bot-integration] Refine error:`, result.error);
    return { error: `生成失败: ${result.error}` };
  }

  try {
    let draft = parseAgentOutput(result.stdout);

    // Two-pass fact-check enforcement
    if (needsFactCheckEnforcement(order.bot_id, sourceOrder.skill_id)) {
      const sessionJsonlPath = await waitForSessionJsonlPath(order.bot_id, sessionId, 2000);
      const fcResult = sessionJsonlPath
        ? scanSessionForFactCheck(sessionJsonlPath)
        : { readSkill: false, hasVerificationCalls: false };

      console.log(`[bot-integration] fact-check scan (non-stream): readSkill=${fcResult.readSkill} hasVerification=${fcResult.hasVerificationCalls}`);

      if (!fcResult.hasVerificationCalls) {
        console.log(`[bot-integration] fact-check NOT executed (non-stream) — launching second pass`);
        const pass2 = await runFactCheckPass(order.bot_id, sessionId);
        if (!pass2.error) {
          try {
            draft = parseAgentOutput(pass2.stdout);
            console.log(`[bot-integration] fact-check second pass (non-stream) produced updated draft`);
          } catch (e2) {
            console.error(`[bot-integration] fact-check second pass output unparseable: ${e2.message}. Keeping first draft.`);
          }
        } else {
          console.error(`[bot-integration] fact-check second pass failed: ${pass2.error}. Keeping first draft.`);
        }
      }
    }

    return { draft };
  } catch (err) {
    return { error: err.message || "无法解析 Bot 输出" };
  }
}

/**
 * Generate a draft by invoking `openclaw agent`.
 * Does NOT use --session-id (conflicts with gateway session routing).
 * Instead, includes full context in each message.
 */
export async function generateDraft(order, version, revisionNote, snapshot = null) {
  const sourceOrder = snapshot?.order || order;
  const { texts, imagePaths } = readMaterials(order.id, snapshot);
  const refLinks = Array.isArray(sourceOrder.reference_links)
    ? sourceOrder.reference_links
    : JSON.parse(sourceOrder.reference_links || "[]");

  // Build materials section
  let materialsSection = "";
  if (texts.length > 0) {
    materialsSection += `【文字素材】\n${texts.join("\n---\n")}\n\n`;
  }
  if (imagePaths.length > 0) {
    materialsSection += `【图片素材】\n请先用 Read 工具查看以下图片，了解素材内容后再创作：\n${imagePaths.map((p) => `- ${p}`).join("\n")}\n\n`;
  }

  const commercialRules = loadCommercialRules(order.bot_id);
  const skillContext = loadSkillContext(order.bot_id, sourceOrder.skill_id);
  const guidanceSection = buildGuidanceSection(sourceOrder);
  const clientSysPromptSection = buildClientSysPromptSection(order.client_id);
  let message;
  if (version === 1) {
    // Initial generation
    message = `${commercialRules}

---
${skillContext}
${getInitialTaskLine(order.bot_id)}

${clientSysPromptSection}${guidanceSection}【客户要求】
${sourceOrder.requirements}

${materialsSection}${refLinks.length > 0 ? `【参考链接】\n${refLinks.join("\n")}\n` : ""}
【内容类型】${sourceOrder.content_type}

请严格按以下 JSON 格式输出结果，不要包含其他文字：
${getDraftJsonTemplate(order.bot_id)}${getFactCheckGate(order.bot_id, sourceOrder.skill_id)}`;
  } else {
    // Revision: include previous draft for context + client feedback
    const db = getDb();
    const prevDraft = snapshot?.drafts?.find((draft) => draft.version === version - 1) || db.prepare(
      "SELECT title, content, card_text, tags FROM drafts WHERE order_id = ? AND version = ?"
    ).get(order.id, version - 1);

    message = `${commercialRules}

---
${skillContext}
你之前收到了一个商单任务，以下是上一版${GZH_BOTS.has(order.bot_id) ? "文章" : "草稿"}和客户的修改意见。

${clientSysPromptSection}${guidanceSection}【原始要求】
${sourceOrder.requirements}

【上一版${GZH_BOTS.has(order.bot_id) ? "文章" : "草稿"}】
标题：${prevDraft?.title || ""}
正文：${prevDraft?.content || ""}
${!GZH_BOTS.has(order.bot_id) && prevDraft?.card_text ? `卡片文字：${prevDraft.card_text}` : ""}

【客户修改意见】
${revisionNote}

请根据客户反馈修改内容，保持你的人设风格不变。输出修改后的完整内容，严格用以下 JSON 格式，不要包含其他文字：
${getDraftJsonTemplate(order.bot_id)}${getFactCheckGate(order.bot_id, sourceOrder.skill_id)}`;
  }

  const args = [
    "agent",
    "--agent", order.bot_id,
    "--message", message,
    "--json",
    "--timeout", "600",
  ];

  console.log(`[bot-integration] Generating draft v${version} for order ${order.id} with ${order.bot_id}`);
  const result = await runAgent(args, 600000);

  if (result.error) {
    console.error(`[bot-integration] Agent error:`, result.error);
    throw new Error(`Bot 生成失败: ${result.error}`);
  }

  console.log(`[bot-integration] Agent output (${result.stdout.length} chars)`);

  // Parse JSON from agent output
  return parseAgentOutput(result.stdout);
}

/**
 * Extract structured draft JSON from agent output.
 *
 * With `--json`, `openclaw agent` returns:
 * {
 *   "runId": "...",
 *   "status": "ok",
 *   "result": { "payloads": [{ "text": "...", "mediaUrl": null }] }
 * }
 *
 * The bot's actual text reply (which contains our target JSON) is in
 * result.payloads — usually the last payload with meaningful content.
 */
function parseAgentOutput(stdout) {
  // Step 1: unwrap the openclaw agent --json wrapper
  let textToSearch = stdout;
  try {
    const wrapper = JSON.parse(stdout.trim());
    if (wrapper.result?.payloads) {
      // Concatenate all payload texts (skip error messages)
      const payloadTexts = wrapper.result.payloads
        .map((p) => p.text || "")
        .filter((t) => t.length > 20); // skip short error blurbs
      textToSearch = payloadTexts.join("\n");
      console.log(`[bot-integration] Unwrapped ${wrapper.result.payloads.length} payloads, searching ${textToSearch.length} chars`);
    } else if (wrapper.reply) {
      textToSearch = wrapper.reply;
    } else if (wrapper.title && wrapper.content) {
      return wrapper; // Already the target JSON
    }
  } catch {
    // Not valid JSON wrapper — search raw text
  }

  // Step 2: try to extract from code block
  const codeBlockMatch = textToSearch.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (codeBlockMatch) {
    const inner = codeBlockMatch[1].trim();
    try {
      const parsed = JSON.parse(inner);
      if (parsed.title && parsed.content) return parsed;
    } catch {}
    // Forgiving fallback: bot often emits unescaped ASCII quotes inside
    // content/card_text. Use next-key boundaries instead of strict JSON.
    const lenient = lenientParseDraftJson(inner);
    if (lenient && lenient.title && lenient.content) return lenient;
  }

  // Step 3: find a JSON object that has both "title" and "content" keys
  // Use a greedy approach: find the outermost { ... } containing both keys
  const matches = textToSearch.matchAll(/\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/g);
  for (const m of matches) {
    try {
      const parsed = JSON.parse(m[0]);
      if (parsed.title && parsed.content) return parsed;
    } catch {}
  }

  // Step 4: try a more aggressive regex for nested JSON
  const jsonMatch = textToSearch.match(/\{[\s\S]*?"title"\s*:\s*"[^"]*"[\s\S]*?"content"\s*:\s*"[\s\S]*?"\s*[\s\S]*?\}/);
  if (jsonMatch) {
    // Try to find valid JSON boundaries
    let str = jsonMatch[0];
    // Trim to the last }
    for (let end = str.length; end > 0; end--) {
      if (str[end - 1] === "}") {
        try {
          const parsed = JSON.parse(str.slice(0, end));
          if (parsed.title && parsed.content) return parsed;
        } catch {}
      }
    }
  }

  // Step 5: lenient parse directly on the raw search text
  const lenient = lenientParseDraftJson(textToSearch);
  if (lenient && lenient.title && lenient.content) return lenient;

  // Log what we got for debugging
  console.error(`[bot-integration] Cannot parse output (${textToSearch.length} chars):\n${textToSearch.slice(0, 800)}`);
  throw new Error("无法解析 Bot 的输出结果");
}

/**
 * Forgiving parser for the draft JSON contract. Uses the next-key sentinel as
 * a boundary instead of relying on strict string escaping, so it tolerates the
 * very common failure mode of the bot emitting unescaped ASCII quotes inside
 * content/card_text.
 *
 * Expected schema (order-sensitive — bot always emits keys in this order):
 *   title → content → card_text → tags → image_style
 */
function lenientParseDraftJson(text) {
  if (!text || typeof text !== "string") return null;

  // Clamp to the first { and its matching-ish closing } to keep the search
  // focused. We can't trust brace matching (quotes may confuse it), so just
  // take from first { to last }.
  const firstBrace = text.indexOf("{");
  const lastBrace = text.lastIndexOf("}");
  if (firstBrace === -1 || lastBrace === -1 || lastBrace <= firstBrace) return null;
  const body = text.slice(firstBrace + 1, lastBrace);

  // Strip a possible \n sequences (the bot emits literal \n inside strings —
  // we want to restore them as real newlines for display).
  const unescape = (s) =>
    s
      .replace(/\\n/g, "\n")
      .replace(/\\r/g, "")
      .replace(/\\t/g, "\t")
      .replace(/\\"/g, '"')
      .replace(/\\\\/g, "\\");

  // Grab a string field that runs until the next `",\n  "nextKey"` sentinel.
  // `nextKey` may also be the closing `}`.
  const grabString = (key, nextKeys) => {
    // Build a non-capturing alternation of sentinels. Each sentinel starts
    // with a `"` then whitespace/comma then the next quoted key name, OR the
    // final `}`.
    const nextPart =
      nextKeys.length > 0
        ? nextKeys.map((k) => `"\\s*,\\s*"${k}"`).join("|") + "|\"\\s*\\}?\\s*$"
        : "\"\\s*\\}?\\s*$";
    const re = new RegExp(`"${key}"\\s*:\\s*"([\\s\\S]*?)(?:${nextPart})`, "");
    const m = body.match(re);
    if (!m) return "";
    return unescape(m[1]);
  };

  const title = grabString("title", ["content", "card_text", "tags", "image_style"]);
  const content = grabString("content", ["card_text", "tags", "image_style"]);
  const cardText = grabString("card_text", ["tags", "image_style"]);

  // tags is an array — match until the closing ]
  let tags = [];
  const tagsMatch = body.match(/"tags"\s*:\s*\[([\s\S]*?)\]/);
  if (tagsMatch) {
    tags = Array.from(tagsMatch[1].matchAll(/"([^"]*)"/g)).map((m) => m[1]);
  }

  // image_style is a simple string, typically no inner quotes
  let imageStyle = "基础";
  const styleMatch = body.match(/"image_style"\s*:\s*"([^"]*)"/);
  if (styleMatch) imageStyle = styleMatch[1];

  if (!title && !content) return null;

  console.log(`[bot-integration] lenient parse rescued draft (title="${title.slice(0, 30)}")`);
  return {
    title,
    content,
    card_text: cardText,
    tags,
    image_style: imageStyle,
  };
}
