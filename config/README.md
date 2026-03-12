# OpenClaw 全局配置

## MCP 全局合并

- **`mcporter-global.json`**：所有 agent 共享的 MCP 配置（仅 `mcpServers`）。
- 各 workspace 的 `config/mcporter.json` 中**同名的 server 会覆盖**全局配置；不同名的会与全局合并。

### 使用

1. 编辑 `~/.openclaw/config/mcporter-global.json`，增减共享的 `mcpServers`。
2. 执行合并脚本，将全局配置合并到所有 workspace：

```bash
~/.openclaw/scripts/merge-mcp-global.sh
```

或从任意目录：

```bash
OPENCLAW_STATE_DIR=~/.openclaw ~/.openclaw/scripts/merge-mcp-global.sh
```

3. 各 workspace 里**仅改本 workspace 独有**的 MCP（如各 bot 不同端口的 xiaohongshu-mcp），改完再跑一次上面的脚本即可把最新全局配置合并进去。
