# ✏️ Prompt 工程

> Prompt 是工程，不是聊天。每个 prompt 必须有明确的边界。

---

## Scope Lock（写 prompt 前必做）

收到需求后，先输出一行 Scope：

> **Scope:** 在 publish.go 的 inputTags 函数中，把 Element.Input() 改为 CDP keyboard events。只改这个函数，不动其他文件。

**Admin 确认后再写 prompt。** 以下情况可跳过确认直接执行：
- 需求本身已指定了文件和改法
- Fix 类任务，症状和目标文件明确

### Scope 三不原则

| 不做 | 含义 | 举例 |
|------|------|------|
| **不重构** | 只改需求涉及的代码 | 不"顺手"改周边函数命名、不拆文件 |
| **不补全** | 不加需求没要求的东西 | 不加 docstring、type annotation、error handling |
| **不升级** | 不改基础设施 | 不升级依赖、不改构建配置、不改 linter 规则 |

---

## Prompt 模板

每个发给 Claude Code 的 prompt **必须包含以下 6 段**：

```
1. Goal     — 一句话说清要做什么
2. Files    — 要修改的文件路径（已知时列出）
3. Context  — 从 Context Scan 得到的项目状态（粘贴 Context Summary）
4. Constraint — 具体的实现约束（如用什么 API、遵循什么模式）
5. Don't    — 明确说不要做什么（最关键的一段）
6. Acceptance — 怎么验证做对了
```

### 示例：Fix 类

```
Goal: Fix tag input in publish.go — use CDP keyboard events instead of Element.Input().

Files: xiaohongshu/publish.go (relative to sandbox root)

Context:
- Sandbox: /tmp/sandbox-fix-tag-input (worktree from main)
- inputTags function at line 156-198

Constraint:
- Use page.KeyActions() with input.Key() for each character
- Keep the existing tag splitting logic (split by space)

Don't:
- Do NOT modify any file other than xiaohongshu/publish.go
- Do NOT refactor surrounding functions
- Do NOT add comments or docstrings
- Do NOT change the function signature
- Do NOT run git commit

Acceptance: Run `go build .` — should compile without errors.
```

### 示例：Feature 类

```
Goal: Add a health check endpoint that returns MCP version and uptime.

Files:
- server.go (add handler)
- version.go (new file, version const)

Context:
- Sandbox: /tmp/sandbox-add-version-endpoint (worktree from main)
- Existing health endpoint at /health returns {"status":"ok"}
- Server uses net/http, handler registered in main()

Constraint:
- New endpoint: GET /version
- Return JSON: {"version": "x.y.z", "uptime_seconds": N}
- Use the existing http.HandleFunc pattern in main()

Don't:
- Do NOT modify the existing /health endpoint
- Do NOT add dependencies
- Do NOT change the server startup logic
- Do NOT add tests (will do separately)

Acceptance: `go build .` succeeds.
```

### 示例：Explore 类（无需沙盒）

```
Goal: Read and analyze the comment loading logic — I need to understand how comments
are fetched and paginated before deciding how to fix the timeout issue.

Files: xiaohongshu/feed_detail.go

Context:
- Project: /home/rooot/MCP/xiaohongshu-mcp (read-only, no sandbox needed)
- Users report comments sometimes timeout on posts with 500+ comments

Constraint:
- Read-only analysis. Output a summary of:
  1. How comments are loaded (lazy scroll? click "show more"? API call?)
  2. What triggers pagination
  3. Where the timeout is set and what value
  4. Your recommendation for fixing the timeout

Don't:
- Do NOT modify any files
- Do NOT run any tests
- Do NOT make any code changes

Acceptance: A clear written analysis with file paths and line numbers.
```

---

## 负面约束速查（Don't 条款常用清单）

每个 prompt **至少包含 3 条** Don't：

| 场景 | 必选 Don't |
|------|-----------|
| 所有场景 | `Do NOT modify any file other than [X]` |
| 所有场景 | `Do NOT run git commit` |
| Fix | `Do NOT refactor surrounding code` |
| Fix | `Do NOT add comments or docstrings` |
| Feature | `Do NOT add tests (will do separately)` 或 `Run tests after implementation` |
| Feature | `Do NOT change existing API signatures` |
| Explore | `Do NOT modify any files` |
| Go 项目 | `Do NOT add new dependencies` |
| TS 项目 | `Do NOT change tsconfig or package.json` |

---

## Prompt 长度控制

- **Fix:** 10-20 行，精准定位
- **Feature:** 20-40 行，包含完整 Context
- **Explore:** 10-15 行，重点在问题而非指令

如果一个 prompt 超过 50 行，说明任务太大，需要拆分成多个独立 prompt。
