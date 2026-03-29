# 小红书合规审核 — compliance-mcp

## 概述

独立的合规审核服务，内置 Claude Sonnet 作为审核引擎，自动检查小红书帖子和评论是否符合平台规则。

**发帖前必须调用此服务进行合规审核，审核通过后才能发布。**

## 可用工具

### `review_content` — 审核帖子内容

发布帖子前调用，检查标题、正文、话题标签是否合规。

```bash
npx mcporter call "compliance-mcp.review_content(title: '标题', content: '正文内容', tags: '话题1,话题2')"
```

**参数：**
| 参数 | 必填 | 说明 |
|------|------|------|
| `title` | 是 | 帖子标题 |
| `content` | 是 | 帖子正文 |
| `tags` | 否 | 话题标签，逗号分隔 |
| `content_type` | 否 | 内容类型：图文/视频/长文（默认图文）|
| `bot_identity` | 否 | Bot 人设简述，用于检查人设一致性 |

### `review_comment` — 审核评论/回复

发表评论前调用，检查评论内容是否合规。

```bash
npx mcporter call "compliance-mcp.review_comment(comment: '评论内容')"
```

**参数：**
| 参数 | 必填 | 说明 |
|------|------|------|
| `comment` | 是 | 评论/回复内容 |
| `context` | 否 | 原帖内容，提供上下文以便更准确审核 |

## 返回格式

```json
{
  "passed": true,
  "score": 92,
  "violations": [],
  "summary": "内容合规，可以发布"
}
```

- `passed`: 是否通过审核
- `score`: 合规评分（0-100）
- `violations`: 违规项列表，每项包含 `level`（critical/warning/info）、`category`、`detail`、`suggestion`
- `summary`: 一句话总结

## 使用流程

1. 准备好帖子内容（标题、正文、话题）
2. 调用 `review_content` 获取审核结果
3. 如果 `passed: false`，根据 `violations` 中的 `suggestion` 修改内容
4. 修改后重新审核，直到 `passed: true`
5. 审核通过后调用 `xiaohongshu-mcp.publish_content` 发布

## 注意事项

- 审核服务使用 Claude Sonnet，每次调用会消耗 token
- 审核结果仅供参考，最终发布责任由 bot 承担
- 金融类内容会被执行最严格的审核标准
- 不要跳过审核直接发布
