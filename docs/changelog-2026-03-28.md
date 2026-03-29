# OpenClaw 更新日志 — 2026-03-28

## 一、生图 MCP 参考图功能

**目标**：支持传入参考图片来引导生图风格。

### 改动
- `generate_image` 新增可选参数 `reference_image`（传本地图片路径）
- 新增 `_load_image_as_data_url()` 辅助函数
- 有参考图时用多模态消息格式，无参考图时行为不变

### 已更新 Skill
- bot7 laok-style 生图调用示例
- bot13 alex-cover-style 生图调用示例

---

## 二、Dashboard 界面改版

**目标**：提升信息密度，减少操作步骤。

### 角色卡片
- 点击名字直接改名（移除笔形图标），改名时高亮提示
- MCP 状态从页面底部移到卡片区，用宝石明暗表示运行/停止
- 弹窗统一为手动关闭（不再鼠标移走自动消失）

### 会话管理
- 新增会话按钮：按时间查看 agent 所有会话 ID 并跳转
- 新建会话按钮
- 右上角显示当前活跃对话数

### 消息时间线
- Session ID 橙色高亮显示在 content 列上方
- 每行加边框，from/to 列宽限制溢出省略

### 折叠与布局
- 会话管理、消息流向、定时任务、系统服务默认折叠
- 编辑部展开时右侧消息线联动展开（高度限制防拉伸）
- 会话管理和消息流合并为一行

---

## 三、装备系统重构

**目标**：减少 bot 启动时读取的文件数量，提升上下文利用率。

### 启动文件精简
- 从 7-8 个文件 → **5 个**：SOUL.md / AGENTS.md / EQUIPPED_SKILLS.md / TOOLS.md / 当日日记
- 工种类 skill 内联注入 AGENTS.md，不再单独引用
- SOUL.md 内联 role 内容，TOOLS.md 内联 TOOLS_COMMON

### Dashboard 装备 UI
- 工种/职业/策略：只能选一个，直接显示图标+名字
- 风格/通用技能/研究技能：显示类别名+已装备个数
- 头像居中，左右分列布局；Agent MD / Soul MD 放头像正上方（橙色边框）
- Plugin 和 MCP gem 横向排列
- 点击装备出现「装备」和「详情」两个按钮，子技能包含在主名称框内
- Sub-type 筛选按钮

### 权限控制
- 工种替换需管理员密码验证

---

## 四、技能进化系统

**目标**：让 skill 可以自主进化，同时保证质量可控。

### Diff 可视化
- 进化完成后自动跑 `diff -ruN` 生成 `DIFF.patch` 保存到沙盒目录
- 已为 8 个 skill 生成 patch：compliance-review、frontline、management、ops、record-insight、research-stock、stock-watcher、technical-analyst

### A/B 对比测试
- A 组用线上原版 skill 执行任务，B 组用沙盒进化版执行同样任务
- 用 technical-analyst skill 完成首次 A/B 验证

### 审批流程
```
进化完成 → pending 目录 → 飞书群通知 + Dashboard 展示
    ↓
研究部审批 → 批准：替换线上版（保留上版备份）
           → 驳回：沙盒回退与线上一致
```

### Dashboard 进化池
- 弹窗展示，不遮挡角色卡
- 三种状态：待进化 / 已进化 / 待审批
- Diff 展示维度：token 消耗增减、优化描述、改动描述、效率改善
- 研究部可删除不想进化的技能，可编辑改进方向

---

## 五、合规流程重构

**目标**：合规前置到 bot 自身，印务局不再重复审核。

### 改动
| 文件 | 变更 |
|------|------|
| `submit-to-publisher.sh` | 新增 `-C` 参数标记合规已通过 |
| `post.md` frontmatter | 新增 `compliance_passed: true/false` |
| `publish-pipeline.md` Stage 5 | 简化为检查 `compliance_passed` 标记 |
| `xhs-op 投稿发布.md` | 改为三步：合规 → 提交 → 通知 |

### 部署
- 给所有 bot 创建 `compliance-review` skill symlink
- 印务局（sys2）不再需要知道合规流程的存在

---

## 六、其他变更

| 项目 | 说明 |
|------|------|
| Brave Web Search | 删除旧版工具 |
| System Prompt | 注入 EQUIPPED_SKILLS.md 优先级指令（Skill-first） |
| Subagent 分身 | 屏蔽该功能 |
| bot13 (Alex) | 重构核心文件：硅谷居士人设、美股复盘、内容/生图 skill |
| 日记冗余 | 清理 bot3/5/11/12 的"今天+昨天"日记冗余 |
