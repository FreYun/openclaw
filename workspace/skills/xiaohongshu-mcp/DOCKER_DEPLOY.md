# 小红书 MCP Docker 部署指南

在 Linux 上通过 Docker 部署小红书 MCP 服务，支持多实例隔离运行（一个容器对应一个小红书账号）。

## 环境要求

- Docker 28+
- 当前用户在 `docker` 组中（`sudo usermod -aG docker $USER`，需重新登录生效）
- 约 2GB 磁盘空间（镜像含 Chrome 浏览器）

## 一、构建镜像

### 1.1 获取源码

```bash
git clone https://github.com/xpzouying/xiaohongshu-mcp.git
cd xiaohongshu-mcp
```

### 1.2 预下载 Chrome（国内网络必须）

Dockerfile 中 Chrome 从本地 COPY 进镜像，需要先在宿主机下载：

```bash
mkdir -p .docker-cache
wget -q "https://cdn.npmmirror.com/binaries/chrome-for-testing/131.0.6778.204/linux64/chrome-linux64.zip" \
  -O .docker-cache/chrome.zip
```

> 约 158MB，下载速度取决于网络。如果 npmmirror 也很慢，可以用代理下载后放到 `.docker-cache/chrome.zip`。

### 1.3 构建镜像

```bash
docker build -t xiaohongshu-mcp:latest .
```

构建过程：
1. Go 1.23 编译应用二进制（使用 goproxy.cn 加速）
2. 基于 Ubuntu 22.04 安装 Chrome 运行时依赖
3. COPY 预下载的 Chrome 并解压
4. 最终镜像约 1.5GB

如果遇到 `apt-get` Hash Sum mismatch 错误，加 `--no-cache` 重试：

```bash
docker build --no-cache -t xiaohongshu-mcp:latest .
```

## 二、启动容器

### 2.1 单实例启动

```bash
mkdir -p docker/data docker/images

docker run -d \
  --name xiaohongshu-mcp \
  --init \
  -p 18060:18060 \
  -v $(pwd)/docker/data:/app/data \
  -v $(pwd)/docker/images:/app/images \
  -e COOKIES_PATH=/app/data/cookies.json \
  xiaohongshu-mcp:latest
```

### 2.2 多实例启动（多账号隔离）

每个实例使用不同的端口和数据目录，实现账号完全隔离：

```bash
# 实例 2：端口 18061，独立数据目录
mkdir -p docker/data2 docker/images2

docker run -d \
  --name xiaohongshu-mcp-2 \
  --init \
  -p 18061:18060 \
  -v $(pwd)/docker/data2:/app/data \
  -v $(pwd)/docker/images2:/app/images \
  -e COOKIES_PATH=/app/data/cookies.json \
  xiaohongshu-mcp:latest
```

更多实例以此类推，只需改 `--name`、`-p` 端口、`-v` 数据目录。

### 2.3 验证启动

```bash
# 查看容器状态
docker ps --filter name=xiaohongshu-mcp

# 健康检查
curl http://localhost:18060/health
curl http://localhost:18061/health
```

## 三、登录

每个容器独立维护登录态。首次使用需扫码登录，登录后 cookies 持久化在宿主机数据目录中，重启容器不丢失。

### 3.1 脚本方式（推荐）

```bash
cd /path/to/skills/xiaohongshu-mcp

# 登录实例 1（默认 18060）
python3 save_qrcode.py

# 登录实例 2
python3 save_qrcode.py --url http://localhost:18061
```

打开生成的 `qrcode.png`，用小红书 App 扫码。二维码有效期约 4 分钟。

### 3.2 mcporter 方式

```bash
npx mcporter call xiaohongshu-mcp.check_login_status       # 检查状态
npx mcporter call xiaohongshu-mcp.get_login_qrcode          # 获取二维码
```

### 3.3 curl 方式（MCP JSON-RPC）

```bash
# 初始化 Session
SESSION=$(curl -s -D - -X POST http://localhost:18060/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"cli","version":"1.0"}}}' \
  2>&1 | grep -i 'Mcp-Session-Id' | awk '{print $2}' | tr -d '\r')

# 获取二维码
curl -s -X POST http://localhost:18060/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_login_qrcode","arguments":{}}}'
```

## 四、Agent 接入

### 4.1 OpenClaw (mcporter)

在 `config/mcporter.json` 中添加：

```json
{
  "mcpServers": {
    "xiaohongshu-mcp": {
      "url": "http://localhost:18060/mcp"
    }
  }
}
```

调用示例：

```bash
npx mcporter call xiaohongshu-mcp.check_login_status
npx mcporter call xiaohongshu-mcp.search_feeds keyword="美食推荐"
npx mcporter call "xiaohongshu-mcp.publish_content(title: '测试', content: '内容', images: ['/app/images/test.png'], visibility: '仅自己可见')"
```

### 4.2 Cursor IDE

在 `.cursor/mcp.json` 中配置：

```json
{
  "mcpServers": {
    "xiaohongshu-mcp": {
      "url": "http://localhost:18060/mcp",
      "description": "小红书 MCP 服务 (Docker)"
    }
  }
}
```

### 4.3 其他 MCP 客户端

任何支持 MCP Streamable HTTP 协议的客户端都可以接入，端点地址为：

```
http://localhost:18060/mcp
```

同时也提供 REST API：

```
http://localhost:18060/api/v1/...
```

## 五、数据持久化

| 目录 | 容器内路径 | 说明 |
|------|-----------|------|
| `docker/data/` | `/app/data/` | cookies.json 登录态 |
| `docker/images/` | `/app/images/` | 发布用图片（挂载共享） |

- 要通过 MCP 发布本地图片，先将图片拷贝到 `docker/images/`，然后在 `images` 参数中使用 `/app/images/xxx.png`
- 登录后 cookies 自动保存，重启容器无需重新登录

## 六、常用运维命令

```bash
# 查看所有实例
docker ps --filter name=xiaohongshu-mcp

# 查看日志
docker logs -f xiaohongshu-mcp
docker logs -f xiaohongshu-mcp-2

# 重启
docker restart xiaohongshu-mcp

# 停止/启动
docker stop xiaohongshu-mcp
docker start xiaohongshu-mcp

# 删除并重建（保留数据目录即可）
docker rm -f xiaohongshu-mcp
docker run -d --name xiaohongshu-mcp --init -p 18060:18060 \
  -v $(pwd)/docker/data:/app/data \
  -v $(pwd)/docker/images:/app/images \
  -e COOKIES_PATH=/app/data/cookies.json \
  xiaohongshu-mcp:latest

# 进入容器调试
docker exec -it xiaohongshu-mcp bash
```

## 七、多实例隔离验证

已验证的隔离特性：

| 特性 | 说明 |
|------|------|
| 登录态隔离 | 每个容器独立 cookies，登录不同账号 |
| 浏览器隔离 | 每个容器独立 Chrome 实例 |
| 数据隔离 | 独立数据目录和图片目录 |
| 并行操作 | 两个容器可同时执行操作，互不阻塞 |

测试结果：两个容器各自登录不同账号后，并行发布图文（仅自己可见），均成功完成，耗时约 24 秒。

## 八、故障排查

| 问题 | 解决方案 |
|------|----------|
| 连接拒绝 | `docker start xiaohongshu-mcp` |
| 健康检查失败 | `docker logs xiaohongshu-mcp` 查看错误 |
| 二维码过期 | 重新调用 `get_login_qrcode`，4 分钟内扫码 |
| 图片发布失败 | 确认图片在 `docker/images/` 中，参数用 `/app/images/xxx` |
| apt Hash Sum mismatch | `docker build --no-cache` 重新构建 |
| Chrome 下载失败 | 先在宿主机下载到 `.docker-cache/chrome.zip` |
