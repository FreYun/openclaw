import fs from "fs";
import path from "path";

const IMAGE_GEN_MCP_URL = "http://localhost:18085/mcp";
const OPENCLAW_DIR = "/home/rooot/.openclaw";

// Qwen 3.5 via zai-coding-plan (OpenAI-compatible)
const QWEN_BASE_URL = "https://dd-ai-api.eastmoney.com/v1";
const QWEN_API_KEY = "XFEyNVb9Hmdkl77H5fD76aB1552046Cc9cC5667f3cEd3c69";
const QWEN_MODEL = "qwen3.5-plus-2026-02-15";

/**
 * Split content into N image-generation prompts for multi-image cover generation.
 * Uses Qwen 3.5 to extract N distinct key points from the draft, each as a short
 * headline suitable for a bold-text poster cover image.
 *
 * @param {string} title - Draft title
 * @param {string} content - Full draft content
 * @param {number} count - Number of image prompts to produce
 * @param {string|null} styleDoc - Bot's full image style document (SKILL.md content)
 * @returns {Promise<string[]>} Array of image content prompts, one per image
 */
export async function splitContentForImages(title, content, count, styleDoc) {
  // Extract the CONTENT template from the bot's style doc so Qwen knows the
  // expected output format. Fall back to a generic poster instruction.
  let contentTemplate = "";
  if (styleDoc) {
    const templateRe = /\*\*CONTENT\s*模板\*\*\s*\n+\s*```[^\n]*\n([\s\S]*?)\n\s*```/i;
    const m = styleDoc.match(templateRe);
    if (m) contentTemplate = m[1].trim();
  }
  if (!contentTemplate) {
    contentTemplate =
      'Large bold Chinese title text "[核心观点]" prominently displayed as the main visual element.';
  }

  const res = await fetch(`${QWEN_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${QWEN_API_KEY}`,
    },
    body: JSON.stringify({
      model: QWEN_MODEL,
      messages: [
        {
          role: "system",
          content:
            "你是封面图内容拆分助手。用户给你一篇小红书笔记和需要的封面图张数N。\n" +
            "你的任务：从文章中提取N个不同的核心观点/关键论点，每个观点生成一段 image content prompt。\n\n" +
            "要求：\n" +
            "1. 每张图的 content prompt 必须遵循以下模板格式（只替换方括号内的变量部分）：\n" +
            "```\n" + contentTemplate + "\n```\n" +
            "2. 每张图突出文章不同段落的核心观点，观点之间不重叠\n" +
            "3. 标题文字要短而有力（10-20字），是那段内容的精华提炼，不要照搬原文长句\n" +
            "4. 装饰元素可以根据该段内容主题微调\n\n" +
            "严格按JSON数组返回N个 content prompt 字符串，不要输出其他内容。",
        },
        {
          role: "user",
          content: `标题：${title}\n\n正文：${content}\n\n请生成 ${count} 张封面图的 content prompt。`,
        },
      ],
      temperature: 0.3,
      max_tokens: 4000,
    }),
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Qwen 段落划分失败 (${res.status}): ${body.slice(0, 200)}`);
  }

  const data = await res.json();
  let text = (data.choices?.[0]?.message?.content || "").trim();

  // Strip ```json fences and <think> blocks if present
  text = text.replace(/<think>[\s\S]*?<\/think>/g, "").trim();
  text = text.replace(/^```(?:json)?\s*\n?/i, "").replace(/\n?\s*```$/i, "").trim();

  try {
    const segments = JSON.parse(text);
    if (Array.isArray(segments) && segments.length > 0) {
      return segments.map(String).slice(0, count);
    }
  } catch {}

  // Fallback: return the original content as a single segment
  return [title ? `标题:${title}\n\n${content}` : content];
}

/**
 * Read a bot's image style definition from its workspace skills.
 * Checks for IMAGE_STYLE.md, SKILL.md in visual/art related skill directories.
 */
export function getBotImageStyle(botId) {
  const wsPath = path.join(OPENCLAW_DIR, `workspace-${botId}`);
  const skillsPath = path.join(wsPath, "skills");

  if (!fs.existsSync(skillsPath)) return null;

  // Look for image style files in known skill directories
  const styleFiles = [
    "visual-first-content/IMAGE_STYLE.md",
    "laok-style/SKILL.md",
    "mp-cover-art/SKILL.md",
    "nailong-cover/SKILL.md",
    "report-to-image/SKILL.md",
  ];

  for (const rel of styleFiles) {
    const fullPath = path.join(skillsPath, rel);
    if (fs.existsSync(fullPath)) {
      return fs.readFileSync(fullPath, "utf8");
    }
  }

  // Fallback: scan for any IMAGE_STYLE.md or art-related SKILL.md
  try {
    const skills = fs.readdirSync(skillsPath);
    for (const skill of skills) {
      const imgStyle = path.join(skillsPath, skill, "IMAGE_STYLE.md");
      if (fs.existsSync(imgStyle)) {
        return fs.readFileSync(imgStyle, "utf8");
      }
    }
  } catch {}

  return null;
}

/**
 * Pull the first real STYLE template out of a bot's image-style skill file.
 *
 * Looks for a "STYLE" marker (bold **STYLE...** or a heading) and returns the
 * contents of the first fenced code block that follows it. Falls back to null
 * if no such block is found, so the caller can use a sensible default.
 */
function extractStyleTemplate(styleDoc) {
  if (!styleDoc) return null;

  // 1) Preferred: look for the first **STYLE...** bold marker followed by a
  //    fenced code block. Handles English and 中文 parentheses.
  const boldRe = /\*\*\s*STYLE[^\n*]*\*\*\s*\n+\s*```[^\n]*\n([\s\S]*?)\n\s*```/i;
  const boldMatch = styleDoc.match(boldRe);
  if (boldMatch) {
    return boldMatch[1].trim().slice(0, 1200);
  }

  // 2) Fallback: first `## STYLE` heading followed by a fenced block.
  const headingRe = /^##+\s+STYLE[^\n]*\n+\s*```[^\n]*\n([\s\S]*?)\n\s*```/im;
  const headingMatch = styleDoc.match(headingRe);
  if (headingMatch) {
    return headingMatch[1].trim().slice(0, 1200);
  }

  // 3) Last resort: the first fenced block in the whole file that looks like
  //    an art prompt (contains typical art-style keywords). Avoids picking up
  //    example generate_image() code blocks which have `style:` inside them.
  const fencedRe = /```[^\n]*\n([\s\S]*?)\n\s*```/g;
  let m;
  while ((m = fencedRe.exec(styleDoc)) !== null) {
    const body = m[1].trim();
    if (/generate_image|mcp\./i.test(body)) continue; // skip code example blocks
    if (body.length < 30) continue;
    if (/poster|background|color|style|illustration|冷色|暖色|配色|像素|aesthetic/i.test(body)) {
      return body.slice(0, 1200);
    }
  }

  return null;
}

/**
 * Generate a cover image via image-gen-mcp.
 *
 * Uses MCP protocol over HTTP:
 * 1. Initialize session
 * 2. Call generate_image tool
 */
export async function generateCoverImage(botId, contentDescription) {
  const wsPath = path.join(OPENCLAW_DIR, `workspace-${botId}`);

  // Get bot's art style
  const styleDoc = getBotImageStyle(botId);

  // Extract the real STYLE template from the skill file.
  //
  // Convention (see workspace-bot7/skills/laok-style/SKILL.md etc):
  //   **STYLE（直接复制）**
  //   ```
  //   Bold Chinese title text poster, clean modern layout...
  //   ```
  //
  // We look for the first fenced code block that appears right after a
  // "STYLE" marker (bold or heading). The old regex "(?:style|风格|STYLE)[:：]"
  // accidentally matched the `style: "{placeholder}"` line inside example
  // generate_image() code blocks and fed garbage to the model.
  let style = extractStyleTemplate(styleDoc);
  if (!style) {
    style = "Professional, clean Chinese social media cover design. Warm cream beige background, clean line art, flat muted fills. 960x1280 vertical layout for Xiaohongshu. Modern financial education aesthetic with golden yellow accents.";
  }

  // MCP Streamable HTTP 协议要求客户端声明同时接受 JSON 和 SSE
  const MCP_HEADERS = {
    "Content-Type": "application/json",
    Accept: "application/json, text/event-stream",
  };

  // 响应可能是纯 JSON,也可能是 SSE 流(text/event-stream)。统一解析。
  async function readMcpResponse(res) {
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("text/event-stream")) {
      const text = await res.text();
      // SSE 帧格式: `event: message\ndata: {json...}\n\n`。
      // 每个 data 行是完整 JSON,取第一条 data 行的剩余部分到行尾。
      const match = text.match(/^data:\s*(.+)$/m);
      if (!match) throw new Error(`MCP SSE 响应解析失败: ${text.slice(0, 200)}`);
      return JSON.parse(match[1]);
    }
    return res.json();
  }

  // Step 1: Initialize
  const initRes = await fetch(IMAGE_GEN_MCP_URL, {
    method: "POST",
    headers: MCP_HEADERS,
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "commercial-order", version: "1.0" },
      },
    }),
  });

  if (!initRes.ok) {
    const body = await initRes.text().catch(() => "");
    throw new Error(`image-gen MCP 初始化失败 (${initRes.status}): ${body.slice(0, 200)}`);
  }
  // 消费掉响应体,避免连接挂起
  await readMcpResponse(initRes).catch(() => null);

  const sessionId = initRes.headers.get("mcp-session-id");

  // Step 2: Call generate_image
  const genRes = await fetch(IMAGE_GEN_MCP_URL, {
    method: "POST",
    headers: {
      ...MCP_HEADERS,
      ...(sessionId ? { "Mcp-Session-Id": sessionId } : {}),
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 2,
      method: "tools/call",
      params: {
        name: "generate_image",
        arguments: {
          style,
          content: contentDescription,
          model: "banana2",
          size: "960x1280",
          workspace: wsPath,
        },
      },
    }),
  });

  if (!genRes.ok) {
    const body = await genRes.text().catch(() => "");
    throw new Error(`图片生成失败 (${genRes.status}): ${body.slice(0, 200)}`);
  }

  const genData = await readMcpResponse(genRes);

  if (genData.error) {
    throw new Error(`图片生成失败: ${genData.error.message || JSON.stringify(genData.error)}`);
  }

  // Parse result — image-gen-mcp returns content with text containing the output
  const resultContent = genData.result?.content;
  if (!resultContent) {
    throw new Error("图片生成返回空结果");
  }

  // Find the text content that has file paths
  const textResult = resultContent.find((c) => c.type === "text");
  if (!textResult) {
    throw new Error("图片生成无文本结果");
  }

  // Parse the JSON result from the text
  try {
    const imgResult = JSON.parse(textResult.text);
    return {
      outputDir: imgResult.output_dir,
      files: imgResult.files || [],
      model: imgResult.model,
    };
  } catch {
    // Maybe it's just a path
    return { outputDir: textResult.text.trim(), files: [], model: "banana2" };
  }
}
