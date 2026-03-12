# Portfolio MCP 服务端部署指南

## 一、安装

```bash
# 1. 创建虚拟环境
cd portfolio-service
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 2. 安装依赖
pip install -e .
```

## 二、配置 Tushare Token

portfolio-mcp 依赖 tushare 获取实时行情，需要设置环境变量：

```bash
# Windows
setx TUSHARE_TOKEN "你的token"

# Linux/macOS
export TUSHARE_TOKEN="你的token"
```

## 三、启动服务

```bash
# 前台启动（调试用）
python run_service.py

# 指定端口
python run_service.py --port 18790

# 后台启动（Linux/macOS）
nohup python run_service.py &
```

服务默认监听 `0.0.0.0:18790`，SSE 端点为 `/sse`。

守护进程会在服务崩溃后 3 秒自动重启，日志写入 `data/service.log`。

## 四、可选：自定义数据库路径

默认数据库在 `data/portfolio.db`，可通过环境变量修改：

```bash
set PORTFOLIO_DB_DIR=D:\openclawdata\portfolio
```

## 五、客户端接入

在客户端 OpenClaw 的 `gateway/config.json` 中添加：

```json
"portfolio-mcp": {
  "type": "sse",
  "isActive": true,
  "url": "http://<服务器IP>:18790/sse",
  "description": "A股模拟炒股组合管理服务"
}
```

所有客户端共享服务端同一个数据库，持仓数据统一管理。

## 六、防火墙

确保服务器防火墙放行 18790 端口：

```powershell
# Windows
netsh advfirewall firewall add rule name="PortfolioMCP" dir=in action=allow protocol=TCP localport=18790

# Linux
sudo ufw allow 18790/tcp
```

## 七、每日自动更新

配置定时任务在交易日 15:05 执行：

```powershell
# Windows
schtasks /create /tn "PortfolioDailyUpdate" /tr "C:\路径\venv\Scripts\python.exe C:\路径\daily_update.py" /sc daily /st 15:05
```

## 依赖

- Python >= 3.10
- mcp[cli] >= 1.0.0
- tushare >= 1.4.0
