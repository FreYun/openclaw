# 不用 Docker 时本地启动 web-search-mcp-server（使用公网 SearXNG）
# 用法：PowerShell 里执行 .\start-web-search-mcp.ps1，保持窗口不关；然后 OpenClaw 即可使用 websearch 的 3 个工具。

$ErrorActionPreference = "Stop"
$ServerDir = $PSScriptRoot
$VenvPath = Join-Path $ServerDir "venv"

# 默认用 DuckDuckGo（免 API、国内可用）；要改用公网 SearXNG 可设 SEARCH_BACKEND=searxng
$env:SEARCH_BACKEND = "duckduckgo"
$env:SEARXNG_URL = "https://searx.nixnet.services"
$env:SEARXNG_TIMEOUT = "30.0"

Set-Location $ServerDir

if (-not (Test-Path (Join-Path $VenvPath "Scripts\python.exe"))) {
    Write-Host "Creating venv and installing dependencies..."
    python -m venv venv
}
# 确保依赖已安装（含 duckduckgo-search）
& $VenvPath\Scripts\pip.exe install -r requirements.txt -q

$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "Error: venv not found. Install Python 3.11+ and run again."
    exit 1
}

Write-Host "Web Search MCP Server: http://localhost:8003 (Backend: $env:SEARCH_BACKEND)"
Write-Host "Press Ctrl+C to stop."
$env:SEARCH_BACKEND = "duckduckgo"
$env:SEARXNG_URL = "https://searx.nixnet.services"
$env:SEARXNG_TIMEOUT = "30.0"
& $PythonExe -c "import os; os.environ['SEARCH_BACKEND'] = os.environ.get('SEARCH_BACKEND', 'duckduckgo'); os.environ['SEARXNG_URL'] = os.environ.get('SEARXNG_URL', 'https://searx.nixnet.services'); os.environ['SEARXNG_TIMEOUT'] = os.environ.get('SEARXNG_TIMEOUT', '30.0'); import runpy; runpy.run_path('server.py', run_name='__main__')"
