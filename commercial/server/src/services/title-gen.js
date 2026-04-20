// 与 image-gen.js 同样硬编码,不跨文件 import,保持服务文件自包含
const QWEN_BASE_URL = "https://dd-ai-api.eastmoney.com/v1";
const QWEN_API_KEY = "XFEyNVb9Hmdkl77H5fD76aB1552046Cc9cC5667f3cEd3c69";
const QWEN_MODEL = "qwen3.5-plus-2026-02-15";
const TITLE_MAX_CHARS = 30;
const REQUEST_TIMEOUT_MS = 15000;
const CONTENT_SLICE_CHARS = 2000;

/**
 * 根据草稿 title + 正文,调 Qwen 3.5 总结一个 ≤30 字的中文订单标题。
 * 失败时抛错,由调用方决定怎么处理(目前 fire-and-forget,只打 log)。
 */
export async function generateOrderTitle(draftTitle, draftContent) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
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
              "你是订单命名助手。根据下方小红书草稿,生成一个不超过 30 字的中文订单标题,简洁概括主题。\n" +
              "要求:\n" +
              "1. 不要带引号、书名号、emoji\n" +
              "2. 不要前缀(如'订单:'、'标题:')\n" +
              "3. 直接返回标题字符串本身,不要任何解释",
          },
          {
            role: "user",
            content: `草稿标题:${draftTitle || "(无)"}\n\n草稿正文:\n${(draftContent || "").slice(0, CONTENT_SLICE_CHARS)}`,
          },
        ],
        temperature: 0.3,
        max_tokens: 80,
      }),
      signal: controller.signal,
    });

    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`Qwen 标题生成失败 (${res.status}): ${body.slice(0, 200)}`);
    }

    const data = await res.json();
    let text = (data.choices?.[0]?.message?.content || "").trim();
    text = text.replace(/<think>[\s\S]*?<\/think>/g, "").trim();
    text = text.replace(/^["「『《]+|["」』》]+$/g, "").trim();
    text = text.replace(/^标题[:：]\s*/, "").trim();

    if (!text) throw new Error("Qwen 返回空标题");

    const chars = [...text];
    if (chars.length > TITLE_MAX_CHARS) {
      text = chars.slice(0, TITLE_MAX_CHARS).join("");
    }
    return text;
  } finally {
    clearTimeout(timer);
  }
}
