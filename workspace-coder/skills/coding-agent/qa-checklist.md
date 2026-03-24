# ✅ QA 验收

> 未验收的代码是未完成的代码。

---

## 验收流程（3 步）

### Step 1: Diff 回顾（防多做）

Claude Code 跑完后，用它跑以下命令：

```
在 tmux 里让 Claude Code 执行：
git diff --stat     → 看改了哪些文件
git diff            → 看具体改动
```

**检查项：**

| 检查 | Pass 条件 | Fail 处理 |
|------|----------|----------|
| 文件范围 | 只改了 Scope 里列出的文件 | 有意外文件 → 立即 Fail，让 Claude Code revert 多余文件 |
| 改动内容 | 每一行改动都与需求相关 | 有格式化/重构/加注释等多余改动 → Fail |
| 新增文件 | Scope 里说了要新建才算 Pass | 意外新建文件 → Fail |

### Step 2: 完整性检查（防少做）

逐条对照原始需求：

```
需求说了 3 个点 → 输出必须覆盖 3 个点
需求说"修改 A 和 B" → A 和 B 都要有改动
需求说"跑测试" → Claude Code 输出里要有测试结果
```

**如果 Claude Code 只做了部分就停了** → 不算 Pass，按 Round 1 fail 处理。

### Step 3: 正确性检查

| 检查 | 方法 |
|------|------|
| 编译通过 | 让 Claude Code 跑 `go build .` 或 `npm run build` |
| 逻辑正确 | 看 diff 的代码逻辑是否符合需求意图 |
| 无副作用 | 没有改变已有行为（除非需求要求） |
| 安全 | 没有 hardcode secret、没有危险操作 |
| 风格一致 | 新代码与项目现有代码风格匹配 |

---

## 验收结论

### Pass

```
✅ QA Pass
- Files: publish.go (+12 -5)
- Scope match: 只改了 inputTags 函数
- Build: go build 通过
- Summary: tag 输入改为 CDP keyboard events
```

报告 Admin，记日记。

### Round 1 Fail

```
❌ QA Fail (Round 1)
- Problem: Claude Code 额外修改了 server.go 的日志格式
- Action: 修 prompt 加 "Do NOT modify server.go"，重试
```

修 prompt，从 Write & Send Prompt 重来。

### Round 2 Fail

```
🛑 QA Fail (Round 2) — 停止，报告 Admin
- 原始需求: [粘贴]
- Round 1 prompt: [粘贴]
- Round 1 问题: [描述]
- Round 2 prompt: [粘贴]
- Round 2 问题: [描述]
- 判断: prompt 问题 / 任务超出 Claude Code 能力 / 需要人工介入
```

**绝不磨过第 2 轮。**

---

## 常见 Fail 模式及对策

| 模式 | 症状 | 根因 | 对策 |
|------|------|------|------|
| 多做 | 改了需求没提的文件 | prompt 没有 Don't 条款 | 补上 `Do NOT modify any file other than X` |
| 多做 | 加了 docstring/注释 | Claude Code 默认行为 | 补上 `Do NOT add comments or docstrings` |
| 多做 | 顺手重构了代码 | prompt 目标太宽泛 | 缩小 Goal 范围，指定函数/行号 |
| 少做 | 只改了 2/3 个文件 | prompt 里没明确列 Files | 在 Files 段列出所有要改的文件 |
| 少做 | 改了但没跑测试 | Acceptance 没写 | 在 Acceptance 写明要跑什么 |
| 改错 | 用了错误的 API | Context 没给够 | 在 Context 里注明要用哪个 API 和调用方式 |
| 改错 | 覆盖了未提交改动 | 不知道文件有 pending changes | Context Scan 发现后在 prompt 里注明 |
