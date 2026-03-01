#!/usr/bin/env python3
"""
DuckDuckGo Search MCP Server
免费网页搜索，无需 API Key
"""
import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False


class DDGSearchServer:
    """DuckDuckGo 搜索 MCP 服务器"""
    
    def __init__(self):
        self.tools = {
            "web_search": self.handle_web_search,
        }
    
    async def run(self):
        """主循环：读取 stdin 的 JSON-RPC 请求"""
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                request = json.loads(line.strip())
                response = await self.handle_request(request)
                if response:
                    print(json.dumps(response), flush=True)
                    
            except json.JSONDecodeError:
                continue
            except Exception as e:
                self.send_error(None, -32603, str(e))
    
    async def handle_request(self, request: Dict) -> Optional[Dict]:
        """处理 JSON-RPC 请求"""
        method = request.get("method")
        req_id = request.get("id")
        params = request.get("params", {})
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "ddg-search",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "web_search",
                            "description": "使用 DuckDuckGo 搜索网页（免费，无需 API Key）。返回搜索结果列表，包含标题、URL 和摘要。",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "搜索关键词"
                                    },
                                    "max_results": {
                                        "type": "integer",
                                        "description": "最大返回结果数（1-20，默认10）",
                                        "minimum": 1,
                                        "maximum": 20,
                                        "default": 10
                                    },
                                    "region": {
                                        "type": "string",
                                        "description": "地区代码（如 'cn' 中国, 'us' 美国, 'wt-wt' 全球）",
                                        "default": "wt-wt"
                                    }
                                },
                                "required": ["query"]
                            }
                        }
                    ]
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name in self.tools:
                result = await self.tools[tool_name](arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": result
                }
            else:
                return self.send_error(req_id, -32601, f"Tool not found: {tool_name}")
        
        return None
    
    async def handle_web_search(self, args: Dict) -> Dict:
        """执行 DuckDuckGo 搜索"""
        if not DDGS_AVAILABLE:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "错误：未安装 ddgs 库。请运行: pip install ddgs"
                    }
                ],
                "isError": True
            }
        
        query = args.get("query", "").strip()
        if not query:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "错误：搜索关键词不能为空"
                    }
                ],
                "isError": True
            }
        
        max_results = min(max(args.get("max_results", 10), 1), 20)
        region = args.get("region", "wt-wt")
        
        try:
            # 在线程中运行同步的 DDGS
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._search_sync,
                query,
                max_results,
                region
            )
            
            if not results:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "未找到相关结果。建议：换用英文关键词或简化搜索词。"
                        }
                    ]
                }
            
            # 格式化结果
            lines = [f"搜索: {query}\n找到 {len(results)} 条结果:\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "")
                url = r.get("href", "")
                snippet = r.get("body", "")
                lines.append(f"{i}. {title}\n   URL: {url}\n   {snippet}\n")
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "\n".join(lines)
                    }
                ]
            }
            
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"搜索失败: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    def _search_sync(self, query: str, max_results: int, region: str) -> List[Dict]:
        """同步搜索方法（在线程池中运行）"""
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
                    "href": r.get("href", ""),
                    "body": r.get("body", "")
                })
                if len(results) >= max_results:
                    break
            return results
    
    def send_error(self, req_id: Any, code: int, message: str) -> Dict:
        """发送错误响应"""
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": code,
                "message": message
            }
        }


if __name__ == "__main__":
    server = DDGSearchServer()
    asyncio.run(server.run())
