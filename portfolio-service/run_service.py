"""
Portfolio MCP SSE 服务守护进程。

用法：python run_service.py [--port 18790] [--host 0.0.0.0]

功能：
- 启动 portfolio-mcp SSE 服务
- 子进程崩溃后自动重启（间隔 3 秒）
- 日志写入 data/service.log
- Ctrl+C 优雅退出
"""

import argparse
import logging
import signal
import subprocess
import sys
import time
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "data"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "service.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("portfolio-service")

_running = True
_proc = None


def _stop(sig, frame):
    global _running, _proc
    log.info("收到停止信号，正在关闭服务...")
    _running = False
    if _proc and _proc.poll() is None:
        _proc.terminate()
        try:
            _proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _proc.kill()


def main():
    global _proc

    parser = argparse.ArgumentParser(description="Portfolio MCP 守护进程")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=18790)
    args = parser.parse_args()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    python = sys.executable
    cmd = [python, "-m", "portfolio_mcp", "--transport", "sse",
           "--host", args.host, "--port", str(args.port)]

    log.info(f"守护进程启动，服务地址: http://{args.host}:{args.port}/sse")
    log.info(f"命令: {' '.join(cmd)}")

    restart_count = 0

    while _running:
        log.info(f"启动服务进程 (第 {restart_count + 1} 次)...")
        _proc = subprocess.Popen(cmd, cwd=str(Path(__file__).resolve().parent))
        exit_code = _proc.wait()

        if not _running:
            log.info("服务已正常停止。")
            break

        restart_count += 1
        log.warning(f"服务进程退出 (exit code: {exit_code})，{3} 秒后重启...")
        time.sleep(3)

    log.info(f"守护进程退出。共重启 {restart_count} 次。")


if __name__ == "__main__":
    main()
