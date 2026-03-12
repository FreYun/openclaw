# 小红书 MCP Docker 运维手册

**完整版见：** `/home/rooot/xiaohongshu-mcp/docker-ops/DOCKER_运维手册.md`

---

## 快速参考

```bash
cd /home/rooot/xiaohongshu-mcp/docker-ops

./ctl.sh start-all        # 批量启动（从 ports.conf）
./ctl.sh stop-all         # 批量停止
./ctl.sh start 18061      # 单容器启动
./ctl.sh sync             # 同步 workspace-bot 的 mcporter + SKILL
```

**配置文件：** `docker-ops/ports.conf`（每行一个端口）
