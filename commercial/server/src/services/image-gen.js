import fs from "fs";
import path from "path";

const IMAGE_GEN_MCP_URL = "http://localhost:18085/mcp";
const OPENCLAW_DIR = "/home/rooot/.openclaw";

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

  // Build style prompt — use bot's style doc or a sensible default
  let style;
  if (styleDoc) {
    // Extract the core style description (first template or main style section)
    // Look for "STYLE" or style-related content
    const styleMatch = styleDoc.match(/(?:style|风格|STYLE)[：:]\s*([\s\S]*?)(?=\n##|\n---|\n\n\n|$)/i);
    if (styleMatch) {
      style = styleMatch[1].trim().slice(0, 800);
    } else {
      // Use first meaningful chunk
      style = styleDoc
        .replace(/^#.*$/gm, "")
        .replace(/<!--[\s\S]*?-->/g, "")
        .trim()
        .slice(0, 800);
    }
  } else {
    style = "Professional, clean Chinese social media cover design. Warm cream beige background, clean line art, flat muted fills. 960x1280 vertical layout for Xiaohongshu. Modern financial education aesthetic with golden yellow accents.";
  }

  // Call image-gen-mcp via MCP protocol
  // Step 1: Initialize
  const initRes = await fetch(IMAGE_GEN_MCP_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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

  const sessionId = initRes.headers.get("mcp-session-id");

  // Step 2: Call generate_image
  const genRes = await fetch(IMAGE_GEN_MCP_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
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

  const genData = await genRes.json();

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
