# 🔍 上下文扫描（Context Scan）

> 写 prompt 前必做。闭眼写 prompt 是低质量 prompt 的根源。

---

## 为什么要扫描

- 不知道项目结构 → prompt 指错文件路径 → Claude Code 找不到或改错文件
- 不知道已有改动 → prompt 覆盖别人的修改 → 功能回退
- 不知道分支状态 → 在错误的分支上改 → 合并冲突

---

## 扫描步骤

收到需求后，依次执行（这些是允许直接跑的只读命令）：

### Step 1: 项目结构概览

```bash
# 一键扫描（推荐，输出可直接粘贴到 prompt 的 Context 段）
python3 /home/rooot/.openclaw/workspace-coder/scripts/project-tree.py /path/to/project --git --context

# 或手动：
tree -L 2 /path/to/project
ls -la /path/to/project/specific-dir/
```

### Step 2: Git 状态

```bash
cd /path/to/project

# 当前分支 + 未提交文件
git status

# 已有改动概览（哪些文件改了、改了多少行）
git diff --stat

# 与主分支的差异（看这个分支总共做了什么）
git diff --stat origin/main...HEAD

# 最近提交历史（理解上下文）
git log --oneline -10
```

### Step 3: 需求相关文件预览

```bash
# 如果需求涉及特定文件，先看一眼结构和关键部分
head -50 /path/to/file
wc -l /path/to/file

# 如果需要了解函数签名或接口定义
grep -n "func \|type \|interface " /path/to/file.go
grep -n "export \|function \|class " /path/to/file.ts
```

---

## 输出：Context Summary

扫描完后，写一段 Context Summary。这段文字会直接嵌入发给 Claude Code 的 prompt。

**格式：**

```
Context:
- Branch: main, clean / has uncommitted changes
- Modified files: publish.go (+45 -12), types.go (+3 -0)
- Target file: publish.go (287 lines, has pending changes — do NOT overwrite lines 45-89)
- Project structure: Go project, main entry at cmd/main.go, business logic in xiaohongshu/
```

**要点：**

- 如果目标文件有未提交改动 → 必须在 Context 里注明，让 Claude Code 知道不要覆盖
- 如果目标文件很大（>500行） → 在 Context 里注明关键函数的行号范围
- 如果项目有特殊构建方式 → 在 Context 里注明（如 `go run .` 而不是 `go build`）

---

## 什么时候可以跳过

- 需求只涉及新建文件（不需要了解已有代码）
- 在同一个 session 内对同一个项目的连续需求（状态已知，增量检查即可）
- Admin 已经给出完整的文件路径和行号
