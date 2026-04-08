import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import { getDb } from "../db.js";

const OPENCLAW_DIR = "/home/rooot/.openclaw";

/**
 * Spawn `openclaw agent` and return stdout/stderr.
 * Follows the same pattern as dashboard server.js runAgent().
 */
function runAgent(args, timeoutMs = 300000) {
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
    .prepare("SELECT * FROM order_materials WHERE order_id = ?")
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

  let message;
  if (version === 1) {
    // Initial generation
    message = `你收到了一个商单任务。请以你的人设风格生成一篇小红书帖子。

【客户要求】
${sourceOrder.requirements}

${materialsSection}${refLinks.length > 0 ? `【参考链接】\n${refLinks.join("\n")}\n` : ""}
【内容类型】${sourceOrder.content_type}

请严格按以下 JSON 格式输出结果，不要包含其他文字：
{
  "title": "标题(不超过20字)",
  "content": "正文内容",
  "card_text": "如果是text_to_image模式，这里写卡片文字，否则留空",
  "tags": ["标签1", "标签2", "标签3"],
  "image_style": "基础"
}`;
  } else {
    // Revision: include previous draft for context + client feedback
    const db = getDb();
    const prevDraft = snapshot?.drafts?.find((draft) => draft.version === version - 1) || db.prepare(
      "SELECT title, content, card_text, tags FROM drafts WHERE order_id = ? AND version = ?"
    ).get(order.id, version - 1);

    message = `你之前收到了一个商单任务，以下是上一版草稿和客户的修改意见。

【原始要求】
${sourceOrder.requirements}

【上一版草稿】
标题：${prevDraft?.title || ""}
正文：${prevDraft?.content || ""}
${prevDraft?.card_text ? `卡片文字：${prevDraft.card_text}` : ""}

【客户修改意见】
${revisionNote}

请根据客户反馈修改内容，保持你的人设风格不变。输出修改后的完整内容，严格用以下 JSON 格式，不要包含其他文字：
{
  "title": "标题(不超过20字)",
  "content": "修改后的正文内容",
  "card_text": "卡片文字(如有)",
  "tags": ["标签1", "标签2", "标签3"],
  "image_style": "基础"
}`;
  }

  const args = [
    "agent",
    "--agent", order.bot_id,
    "--message", message,
    "--json",
    "--timeout", "300",
  ];

  console.log(`[bot-integration] Generating draft v${version} for order ${order.id} with ${order.bot_id}`);
  const result = await runAgent(args, 300000);

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
    try {
      const parsed = JSON.parse(codeBlockMatch[1].trim());
      if (parsed.title && parsed.content) return parsed;
    } catch {}
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

  // Log what we got for debugging
  console.error(`[bot-integration] Cannot parse output (${textToSearch.length} chars):\n${textToSearch.slice(0, 800)}`);
  throw new Error("无法解析 Bot 的输出结果");
}
