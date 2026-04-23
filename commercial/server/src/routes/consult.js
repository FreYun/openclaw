import { Router } from "express";
import { spawn } from "child_process";
import { v4 as uuidv4 } from "uuid";
import fs from "fs";
import path from "path";
import { getDb } from "../db.js";
import { requireAuth } from "../auth.js";
import {
  waitForSessionJsonlPath,
  tailSessionJsonl,
} from "../services/bot-integration.js";
import * as tunnel from "../tunnel/client-api.js";

import { OPENCLAW_DIR } from "../paths.js";

const router = Router();
const CONSULT_TIMEOUT_MS = 120_000;

function buildBotCatalogContext() {
  const db = getDb();
  const bots = db
    .prepare("SELECT * FROM bot_profiles WHERE is_available = 1 ORDER BY bot_id")
    .all();

  const sections = bots.map((bot) => {
    const wsDir = path.join(OPENCLAW_DIR, `workspace-${bot.bot_id}`);
    let identitySnippet = "";
    try {
      identitySnippet = fs.readFileSync(path.join(wsDir, "IDENTITY.md"), "utf8").trim();
    } catch {}

    let soulSnippet = "";
    try {
      const soul = fs.readFileSync(path.join(wsDir, "SOUL.md"), "utf8");
      soulSnippet = soul.slice(0, 800).trim();
    } catch {}

    const specialties = JSON.parse(bot.specialties || "[]");

    return [
      "---",
      `bot_id: ${bot.bot_id}`,
      `display_name: ${bot.display_name}`,
      `description: ${bot.description}`,
      `style_summary: ${bot.style_summary}`,
      `specialties: ${specialties.join(", ")}`,
      `IDENTITY:\n${identitySnippet}`,
      `SOUL摘要:\n${soulSnippet}`,
      "---",
    ].join("\n");
  });

  return `【可选达人列表（共 ${bots.length} 位）】\n\n${sections.join("\n\n")}`;
}

function buildConsultPrompt(userMessage, botCatalog) {
  return `【商单咨询模式 — 单轮任务】

你是 OpenClaw 的运营部，现在接到了一个商单客户的内容需求咨询。

你的唯一任务：
1. 理解客户需求（主题、调性、目标受众）
2. 从下面的达人列表中推荐最合适的一位
3. 给出推荐理由（面向客户，简洁有说服力）
4. 生成一份具体的内容指导方案（guidance），达人拿到后可以直接执行

${botCatalog}

【客户需求描述】
${userMessage}

【安全约束】
1. 不要调用 send_message 或任何写入工具 — 这是只读咨询
2. 不要写工作日记、queue 或 memory — 这不是内部运营任务
3. 只输出 JSON 推荐结果，不要做排期、审稿等主编工作

【输出格式 — 严格 JSON，不要包含任何其他文字】
{
  "recommended_bot_id": "botN",
  "reason": "2-3句推荐理由（面向客户展示）",
  "content_type": "text_to_image 或 image 或 longform",
  "guidance": "内容指导方案：包含建议角度、关键要点、风格指引、注意事项等，达人可直接参照执行"
}`;
}

function parseConsultOutput(stdout) {
  let textToSearch = stdout;
  try {
    const wrapper = JSON.parse(stdout.trim());
    if (wrapper.result?.payloads) {
      const payloadTexts = wrapper.result.payloads
        .map((p) => p.text || "")
        .filter((t) => t.length > 10);
      textToSearch = payloadTexts.join("\n");
    } else if (wrapper.reply) {
      textToSearch = wrapper.reply;
    } else if (wrapper.recommended_bot_id && wrapper.guidance) {
      return wrapper;
    }
  } catch {}

  const codeBlockMatch = textToSearch.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (codeBlockMatch) {
    try {
      const parsed = JSON.parse(codeBlockMatch[1].trim());
      if (parsed.recommended_bot_id) return parsed;
    } catch {}
  }

  const jsonMatch = textToSearch.match(
    /\{[\s\S]*?"recommended_bot_id"\s*:\s*"[^"]*"[\s\S]*?"guidance"\s*:\s*"[\s\S]*?"\s*\}/
  );
  if (jsonMatch) {
    let str = jsonMatch[0];
    for (let i = str.length; i > 0; i--) {
      if (str[i - 1] === "}") {
        try {
          const parsed = JSON.parse(str.slice(0, i));
          if (parsed.recommended_bot_id) return parsed;
        } catch {}
      }
    }
  }

  const simpleMatch = textToSearch.match(/\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/g);
  if (simpleMatch) {
    for (const m of simpleMatch) {
      try {
        const parsed = JSON.parse(m);
        if (parsed.recommended_bot_id) return parsed;
      } catch {}
    }
  }

  throw new Error("无法解析 sys4 咨询输出");
}

// POST /api/consult — spawn sys4 agent for bot recommendation (SSE streaming)
router.post("/", requireAuth, async (req, res) => {
  const { message } = req.body || {};
  if (!message || typeof message !== "string" || message.trim().length === 0) {
    return res.status(400).json({ error: "请输入内容需求描述" });
  }
  if (message.length > 4000) {
    return res.status(400).json({ error: "需求描述过长（上限 4000 字）" });
  }

  const botCatalog = buildBotCatalogContext();
  const prompt = buildConsultPrompt(message.trim(), botCatalog);
  const sessionId = `agent:sys4:commercial:consult:${uuidv4()}`;

  const agentArgs = [
    "agent",
    "--agent", "sys4",
    "--session-id", sessionId,
    "-m", prompt,
    "--json",
    "--timeout", "120",
  ];

  console.log(`[consult] Starting consultation session=${sessionId} msgLen=${message.length}`);

  // --- SSE branch ---
  const acceptsSse = (req.headers.accept || "").includes("text/event-stream");
  if (acceptsSse) {
    res.writeHead(200, {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    });
    if (typeof res.flushHeaders === "function") res.flushHeaders();

    let clientClosed = false;
    const sendEvent = (type, data) => {
      try {
        res.write(`event: ${type}\ndata: ${JSON.stringify(data)}\n\n`);
      } catch {}
    };

    const heartbeat = setInterval(() => {
      try { res.write(`: hb\n\n`); } catch {}
    }, 15000);

    res.on("close", () => { clientClosed = true; });

    sendEvent("start", { session_id: sessionId });

    let stopTail = null;
    const tailPromise = waitForSessionJsonlPath("sys4", sessionId)
      .then((filePath) => {
        if (!filePath) return;
        stopTail = tailSessionJsonl(filePath, (evt) => {
          if (clientClosed) return;
          if (evt?.type === "tool_use") sendEvent("tool_use", evt);
        });
      })
      .catch((err) => console.error("[consult] tail setup error:", err));

    let runResult;
    if (tunnel.isConnected()) {
      try {
        const res = await tunnel.exec("openclaw", agentArgs, { timeout: CONSULT_TIMEOUT_MS });
        if (res.error) {
          runResult = { error: res.error };
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
          resolve({ error: "咨询超时" });
        }, CONSULT_TIMEOUT_MS);
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

    await tailPromise.catch(() => {});
    if (stopTail) stopTail();
    clearInterval(heartbeat);

    if (runResult.error) {
      console.error("[consult] error:", runResult.error);
      sendEvent("error", { message: runResult.error });
      try { res.end(); } catch {}
      return;
    }

    try {
      const result = parseConsultOutput(runResult.stdout);

      const db = getDb();
      const validBotIds = ["text_to_image", "image", "longform"];
      if (!validBotIds.includes(result.content_type)) {
        result.content_type = "text_to_image";
      }

      const bot = db
        .prepare("SELECT bot_id, display_name, avatar_path FROM bot_profiles WHERE bot_id = ? AND is_available = 1")
        .get(result.recommended_bot_id);
      if (!bot) {
        sendEvent("error", { message: `推荐的达人 ${result.recommended_bot_id} 不可用` });
        try { res.end(); } catch {}
        return;
      }

      sendEvent("done", {
        recommended_bot_id: result.recommended_bot_id,
        bot_name: bot.display_name,
        bot_avatar: bot.avatar_path,
        reason: result.reason || "",
        content_type: result.content_type,
        guidance: result.guidance || "",
      });
    } catch (err) {
      console.error("[consult] parse error:", err.message);
      sendEvent("error", { message: err.message });
    }

    try { res.end(); } catch {}
    return;
  }

  // --- Non-SSE JSON branch ---
  let runResult;
  if (tunnel.isConnected()) {
    try {
      const res = await tunnel.exec("openclaw", agentArgs, { timeout: CONSULT_TIMEOUT_MS });
      if (res.error) {
        runResult = { error: res.error };
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
        resolve({ error: "咨询超时" });
      }, CONSULT_TIMEOUT_MS);
      child.on("close", (code) => {
        if (done) return;
        done = true;
        clearTimeout(timer);
        resolve(code === 0 ? { stdout } : { error: (stderr || `exit ${code}`).slice(0, 500) });
      });
      child.unref();
    });
  }

  if (runResult.error) {
    return res.status(500).json({ error: runResult.error });
  }

  try {
    const result = parseConsultOutput(runResult.stdout);
    const db = getDb();
    const bot = db
      .prepare("SELECT bot_id, display_name, avatar_path FROM bot_profiles WHERE bot_id = ? AND is_available = 1")
      .get(result.recommended_bot_id);
    if (!bot) return res.status(500).json({ error: `推荐的达人 ${result.recommended_bot_id} 不可用` });

    res.json({
      recommended_bot_id: result.recommended_bot_id,
      bot_name: bot.display_name,
      bot_avatar: bot.avatar_path,
      reason: result.reason || "",
      content_type: result.content_type || "text_to_image",
      guidance: result.guidance || "",
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
