#!/usr/bin/env python3
"""
DuckDuckGo Search HTTP Server
为 OpenClaw 提供免费的网页搜索服务

启动方式:
    python ddg_search_server.py
    
默认监听: http://127.0.0.1:18795

API:
    GET /search?q=关键词&max_results=10
    POST /search {"query": "关键词", "max_results": 10}
"""
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    print("警告: 未安装 ddgs 库。请运行: pip install ddgs")
    print("或者: pip install duckduckgo-search")

PORT = 18795
HOST = "127.0.0.1"


def search_ddg(query: str, max_results: int = 10, region: str = "wt-wt") -> list:
    """执行 DuckDuckGo 搜索"""
    if not DDGS_AVAILABLE:
        raise ImportError("需要安装 ddgs 库: pip install ddgs")
    
    with DDGS() as ddgs:
        results = []
        for r in ddgs.text(
            keywords=query,
            region=region,
            safesearch="moderate",
            max_results=max_results
        ):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", "")
            })
            if len(results) >= max_results:
                break
        return results


class SearchHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 简化日志输出
        print(f"[{self.log_date_time_string()}] {args[0]}")
    
    def do_GET(self):
        """处理 GET 请求"""
        parsed = urlparse(self.path)
        
        if parsed.path == "/search":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            max_results = int(params.get("max_results", ["10"])[0])
            
            self._do_search(query, max_results)
        elif parsed.path == "/health":
            self._send_json({"status": "ok", "ddgs_available": DDGS_AVAILABLE})
        else:
            self._send_error(404, "Not found")
    
    def do_POST(self):
        """处理 POST 请求"""
        parsed = urlparse(self.path)
        
        if parsed.path == "/search":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(body)
                query = data.get("query", "")
                max_results = data.get("max_results", 10)
                
                self._do_search(query, max_results)
            except json.JSONDecodeError:
                self._send_error(400, "Invalid JSON")
        else:
            self._send_error(404, "Not found")
    
    def _do_search(self, query: str, max_results: int):
        """执行搜索并返回结果"""
        if not query:
            self._send_error(400, "Query is required")
            return
        
        try:
            results = search_ddg(query, min(max_results, 20))
            self._send_json({
                "success": True,
                "query": query,
                "results_count": len(results),
                "results": results
            })
        except Exception as e:
            self._send_error(500, str(e))
    
    def _send_json(self, data: dict):
        """发送 JSON 响应"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))
    
    def _send_error(self, code: int, message: str):
        """发送错误响应"""
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({
            "success": False,
            "error": message
        }, ensure_ascii=False).encode('utf-8'))


def main():
    server = HTTPServer((HOST, PORT), SearchHandler)
    print(f"🦆 DuckDuckGo Search Server 启动成功!")
    print(f"   地址: http://{HOST}:{PORT}")
    print(f"   健康检查: http://{HOST}:{PORT}/health")
    print(f"   搜索示例: http://{HOST}:{PORT}/search?q=周星驰")
    print(f"\n按 Ctrl+C 停止服务\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在关闭服务...")
        server.shutdown()


if __name__ == "__main__":
    main()
