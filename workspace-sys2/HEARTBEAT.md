# HEARTBEAT.md - 技能部心跳巡检

- **09:00** — 新增播报（检查 `memory/changelog.md` 最近 7 天变更，有则播报，无则静默）
- **12:00** — skill 状态巡检 + 上报魏忠贤（mag1）
- **19:00** — skill 状态巡检 + 上报魏忠贤（mag1）

---

## 09:00 新增播报

### 检查最近 7 天变更

读取 `memory/changelog.md`，筛选最近 7 天的条目。

- **有新增**：向 mag1 发送播报摘要，包含新增的 MCP/Skill/Tool 名称、影响的角色和 bot
- **无新增**：静默，回复 `HEARTBEAT_OK`

### 处理权限申请

检查是否有待处理的权限申请（通过飞书或其他渠道收到的消息）。如有，按 AGENTS.md 第 7 条流程处理。

---

## 12:00 / 19:00 巡检流程

### 第一步：刷新 skill 目录

```bash
python3 ~/.openclaw/workspace-sys2/scripts/update-inventory.py
```

### 第二步：检查 symlink 同步状态

```bash
python3 -c "
import os
src = '/home/rooot/.openclaw/workspace/skills'
skills = sorted(s for s in os.listdir(src) if os.path.isdir(os.path.join(src, s)))
missing = {}
for skill in skills:
    bots = [f'bot{i}' for i in range(1,11)
            if not os.path.exists(f'/home/rooot/.openclaw/workspace-bot{i}/skills/{skill}')]
    if bots:
        missing[skill] = bots
print(f'共有 skill：{len(skills)} 个')
print(f'有缺失的 skill：{len(missing)} 个')
for s, bots in missing.items():
    print(f'  ❌ {s} 缺失于：{bots}')
if not missing:
    print('  ✅ 全部 bot 的 symlink 完整')
"
```

### 第三步：统计私有 skill

```bash
python3 -c "
import os
for i in range(1, 11):
    d = f'/home/rooot/.openclaw/workspace-bot{i}/skills'
    if not os.path.isdir(d): continue
    private = [s for s in os.listdir(d)
               if not os.path.islink(os.path.join(d, s)) and os.path.isdir(os.path.join(d, s))]
    if private:
        print(f'bot{i} 私有 skill：{private}')
"
```

### 第四步：上报魏忠贤

将以上结果整理后，通过 gateway 发送给 mag1：

```bash
openclaw agent --agent mag1 --message "【技能部日报】HH:MM 巡检完成
📦 共有 skill：N 个
🔗 symlink 状态：全部完整 / N 个有缺失（详见下方）
🔒 私有 skill：botX(skill名), ...
❌ 缺失项（如有）：skill名 缺失于 [botX, botY]
"
```

---

## 铁律

- **只汇报，不自行修复**：发现缺失 symlink 只上报，不擅自创建（除非魏忠贤或研究部明确授权）
- **上报后回复 `HEARTBEAT_OK`**，不等待 mag1 的回复
- 如果 `update-inventory.py` 执行失败，将错误信息一并上报
