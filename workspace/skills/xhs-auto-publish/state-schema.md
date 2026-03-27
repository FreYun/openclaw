# 当日状态文件格式 — auto-publish-state.json

> 文件位置：`memory/auto-publish-state.json`（各 bot 各自维护）

---

## 字段定义

```json
{
  "date": "2026-03-27",
  "posts_today": [
    {
      "note_id": "abc123def456",
      "title": "帖子标题",
      "published_at": "09:45",
      "reads": 350,
      "deleted": false
    }
  ],
  "total_posts": 2,
  "has_hit_500": false,
  "completed": false
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | string | 当前日期 `YYYY-MM-DD`。不是今天 → 重置整个状态 |
| `posts_today` | array | 今日通过本 skill 发布的笔记列表 |
| `posts_today[].note_id` | string | 笔记 ID。初始为 `"pending"`，回查时通过标题匹配更新为真实 ID；匹配失败则为 `"lost"` |
| `posts_today[].title` | string | 笔记标题 |
| `posts_today[].published_at` | string | 发布时间 `HH:MM` |
| `posts_today[].reads` | number | 最新阅读数。每次回查时更新 |
| `posts_today[].deleted` | boolean | 是否已被清理删除。默认 `false` |
| `total_posts` | number | 今日已发帖总数（0-5） |
| `has_hit_500` | boolean | 是否有帖子阅读 ≥ 500 |
| `completed` | boolean | 当日任务是否已结束 |

---

## 状态转换

```
初始状态（新的一天）
  date = today, posts_today = [], total_posts = 0,
  has_hit_500 = false, completed = false

发帖后
  → posts_today 追加新记录
  → total_posts += 1

回查后（Step 7）
  → 更新各帖 reads
  → 更新 note_id（pending → 真实 ID）
  → 判断 has_hit_500
  → 判断 completed

清理后（Step 8）
  → 被删除的帖子标记 deleted = true
  → completed = true

终止条件（任一满足 → completed = true）
  ① has_hit_500 == true
  ② total_posts >= 5
  ③ Step 8 清理完成
```

---

## 重置规则

每次读取状态文件时：
- 如果 `date` 不等于当天日期 → **整个文件重置为初始状态**
- 不保留昨天的数据（昨天的记录已在日记中存档）

---

## 注意事项

- `note_id: "pending"` 的帖子不能执行删除操作（没有真实 ID）
- `note_id: "lost"` 的帖子无法操作，在日记中标注即可
- 此文件由 bot 自主维护，不需要研究部审批
- 文件损坏或丢失时，视为初始状态（当天从头开始）
