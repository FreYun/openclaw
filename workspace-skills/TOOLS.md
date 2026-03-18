# TOOLS.md - 技能部工具配置

## 身份

- **Agent ID：** `skills`
- **职能：** Skill 与 MCP 插件目录管理

---

## 关键路径

| 路径 | 说明 |
|------|------|
| `/home/rooot/.openclaw/workspace/skills/` | 共有 skill 源目录 |
| `/home/rooot/.openclaw/workspace-botN/skills/` | 各 bot 的 skill 目录（含 symlink）|
| `memory/shared-skills.md` | 共有 skill 目录（自动生成）|
| `memory/private-skills.md` | 私有 skill 目录（自动生成）|
| `memory/plugins.md` | MCP 插件配置清单（自动生成）|
| `memory/sync-status.md` | symlink 同步状态（自动生成）|

---

## 刷新目录

```bash
python3 ~/.openclaw/workspace-skills/scripts/update-inventory.py
```

---

## 常用查询命令

```bash
# 列出所有共有 skill
ls /home/rooot/.openclaw/workspace/skills/

# 检查 symlink 完整性（哪些 bot 缺少哪些 skill）
python3 -c "
import os
src = '/home/rooot/.openclaw/workspace/skills'
skills = [s for s in os.listdir(src) if os.path.isdir(os.path.join(src, s))]
for skill in sorted(skills):
    missing = [f'bot{i}' for i in range(1,11)
               if not os.path.exists(f'/home/rooot/.openclaw/workspace-bot{i}/skills/{skill}')]
    if missing: print(f'[缺失] {skill}: {missing}')
"

# 新增共有 skill 的 symlink（所有 bot）
SKILL=新skill名
for i in 1 2 3 4 5 6 7 8 9 10; do
  ln -s ../../workspace/skills/$SKILL /home/rooot/.openclaw/workspace-bot${i}/skills/$SKILL
done
```

---

## MCP 插件查询

```bash
# 查看某 bot 的 MCP 插件配置
cat /home/rooot/.openclaw/workspace-botN/config/mcporter.json
```

---

## Skill 网关（主网关）

技能部拥有并维护一个 MCP 聚合网关，所有 bot 通过它访问研究数据等共享工具。

| 项目 | 值 |
|------|------|
| 代码目录 | `/home/rooot/.openclaw/research-gateway/` |
| 端口 | `18080` |
| 权限配置 | `/home/rooot/.openclaw/research-gateway/permissions.yaml` |
| 日志 | `/tmp/research-gateway.log` |
| PID | `/tmp/research-gateway.pid` |

### 网关管理

```bash
# 启动/停止/重启/状态/日志
bash /home/rooot/.openclaw/research-gateway/run.sh start
bash /home/rooot/.openclaw/research-gateway/run.sh stop
bash /home/rooot/.openclaw/research-gateway/run.sh restart
bash /home/rooot/.openclaw/research-gateway/run.sh status
bash /home/rooot/.openclaw/research-gateway/run.sh log

# 健康检查
curl -s http://localhost:18080/health | python3 -m json.tool

# 查看所有 bot 路由
curl -s http://localhost:18080/
```

### 权限管理

编辑 `permissions.yaml`，修改角色定义或 bot→角色映射。配置变更在**下一次网关重启时生效**（无需立即重启）：

```bash
vim /home/rooot/.openclaw/research-gateway/permissions.yaml
# 配置保存后，下次网关重启自动加载
# 如需立即生效：bash /home/rooot/.openclaw/research-gateway/run.sh restart
```

各 bot 连接方式（已自动配置到 mcporter.json）：
```
http://localhost:18080/mcp/{bot_id}
```

### 当前角色

| 角色 | 工具数 | bot |
|------|--------|-----|
| full_access | 10 | bot7, bot8 |
| content_creator | 4 | bot1-4, bot6, bot9-10 |
| fund_advisor | 8 | bot5 |
| admin | 11 | bot_main, skills |

### 权限申请处理

```bash
# 查看 bot 当前权限信息
bash ~/.openclaw/workspace-skills/scripts/handle-permission-request.sh <bot_id> <tool1,tool2>

# 修改权限后重启网关
vim /home/rooot/.openclaw/research-gateway/permissions.yaml
bash /home/rooot/.openclaw/research-gateway/run.sh restart
```

### 变更记录

变更日志：`memory/changelog.md`
权限申请记录：`memory/permission-requests.md`
