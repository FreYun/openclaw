# Web Search MCP Server

[![MCP](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io)
[![Docker](https://img.shields.io/badge/Docker-Ready-brightgreen)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-ready Model Context Protocol (MCP) server that provides web search capabilities through SearXNG. Designed for seamless integration with LLM agents, featuring HTTP/SSE transport and LLM-optimized response formatting.

## Features

- **Multi-Engine Search** - Aggregates results from Brave, DuckDuckGo, Startpage, and more
- **LLM-Optimized** - Three specialized tools with formatted responses for agent consumption
- **Knowledge Extraction** - Automatic extraction of structured facts from Wikidata
- **Real-Time Streaming** - MCP over HTTP/SSE for live agent integration
- **Docker Ready** - Fully containerized with docker-compose
- **Production Features** - Health checks, metrics, structured logging, request tracking

## Architecture

```
┌─────────────────────┐
│   LLM Agent         │
│  (MCP Client)       │
└──────────┬──────────┘
           │ MCP over HTTP/SSE
           ↓
┌─────────────────────┐
│  Web Search MCP     │  Port 8003
│     Server          │
│  - 3 Search Tools   │
│  - REST API         │
│  - Metrics          │
└──────────┬──────────┘
           │ HTTP
           ↓
┌─────────────────────┐
│     SearXNG         │  Port 8888
│  (Meta-Search)      │
│  - Brave            │
│  - DuckDuckGo       │
│  - Startpage        │
│  - Wikipedia        │
└─────────────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- (Optional) Python 3.11+ for local development

### 1. Clone and Start

```bash
git clone https://github.com/slinusc/web-search-mcp-server.git
cd web-search-mcp-server
docker compose up -d
```

This starts:
- **SearXNG** on port 8888 (search backend)
- **MCP Server** on port 8003 (agent interface)

### 2. Test the API

```bash
# Quick search (LLM-optimized)
curl -X POST http://localhost:8003/api/quick_search \
  -H "Content-Type: application/json" \
  -d '{"query": "latest developments in AI"}'

# Structured search (with facts)
curl -X POST http://localhost:8003/api/structured_search \
  -H "Content-Type: application/json" \
  -d '{"query": "climate change 2024"}'

# Health check
curl http://localhost:8003/healthz
```

### 3. Connect Your MCP Client

```json
{
  "mcpServers": {
    "websearch": {
      "url": "http://localhost:8003/sse"
    }
  }
}
```

## MCP Tools

### 1. `web_search`
**Comprehensive search with full metadata**

```python
{
  "query": "machine learning frameworks",
  "categories": "general",  # or "news", "images", "videos"
  "pageno": 1
}
```

Returns: Full SearXNG response with all engines, suggestions, and infoboxes.

### 2. `quick_search`
**Fast, LLM-optimized results**

```python
{
  "query": "who invented the internet",
  "categories": "general"
}
```

Returns: Top 10 ranked results with knowledge base, relevance scores, and source attribution.

### 3. `structured_search`
**Facts-focused with context**

```python
{
  "query": "Python programming language",
  "categories": "general"
}
```

Returns: Ranked results + Wikidata attributes + context snippets + suggestions.

## Response Format

### Quick Search Example

```json
{
  "ok": true,
  "request_id": "a1b2c3d4e5f6",
  "query": "Python programming",
  "total_results": 28,
  "knowledge_base": {
    "entity": "Python (programming language)",
    "description": "Python is a high-level, interpreted programming language...",
    "attributes": {
      "Developer": "Python Software Foundation",
      "First appeared": "1991",
      "Influenced by": "ABC, Modula-3, C"
    },
    "image": "https://upload.wikimedia.org/..."
  },
  "top_results": [
    {
      "rank": 1,
      "title": "Python.org",
      "url": "https://www.python.org/",
      "snippet": "Python is a programming language that lets you work quickly...",
      "score": 9.0,
      "engines": ["brave", "duckduckgo", "startpage"]
    }
  ],
  "engines_used": ["brave", "duckduckgo", "startpage", "wikipedia"]
}
```

## REST API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sse` | GET | MCP SSE stream (for agents) |
| `/messages` | POST | MCP client messages |
| `/api/search` | POST | General web search |
| `/api/quick_search` | POST | Quick LLM-optimized search |
| `/api/structured_search` | POST | Structured facts search |
| `/healthz` | GET | Health check |
| `/metrics` | GET | Performance metrics |
| `/tools` | GET | List available MCP tools |

## Configuration

### Environment Variables

```bash
# docker-compose.yml or .env
SEARXNG_URL=http://searxng:8080  # SearXNG backend URL
SEARXNG_TIMEOUT=10.0              # Request timeout (seconds)
```

### SearXNG Configuration

Edit `config/settings.yml` to:
- Enable/disable search engines
- Configure result formats
- Set rate limiting
- Customize search behavior

Key settings:
```yaml
search:
  formats:
    - html
    - json  # Required for MCP server

server:
  limiter: false  # Adjust for production
```

## Development

### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run server
python server.py
```

Server runs on `http://localhost:8003`

### Testing

```bash
# Test quick search
curl -X POST http://localhost:8003/api/quick_search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'

# Check metrics
curl http://localhost:8003/metrics

# List available tools
curl http://localhost:8003/tools | jq
```

## Docker

### Build

```bash
docker build -t mcp-server-websearch .
```

### Run Standalone

```bash
docker run -d \
  --name mcp-websearch \
  -p 8003:8003 \
  -e SEARXNG_URL=http://searxng:8080 \
  mcp-server-websearch
```

### Compose (Recommended)

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f mcp-websearch

# Stop services
docker compose down
```

## Monitoring

### Health Check

```bash
curl http://localhost:8003/healthz
# Response: ok
```

### Metrics

```bash
curl http://localhost:8003/metrics
```

Response:
```json
{
  "ok": true,
  "metrics": {
    "api_search_calls": 42,
    "api_quick_search_calls": 156,
    "api_structured_search_calls": 23,
    "mcp_call_tool_calls": 221,
    "searxng_requests": 221,
    "errors_total": 2
  }
}
```

## Agent Integration

### Generic MCP Client

The server exposes three MCP tools that are automatically available to any MCP-compatible agent:

- `web_search` - For comprehensive search with full details
- `quick_search` - For fast answers with top results
- `structured_search` - For research with structured facts

### LangChain Integration

```python
from langchain.tools import Tool

# Wrap the MCP tools
tools = [
    Tool(
        name="web_search",
        func=call_mcp_tool,  # Your MCP client wrapper
        description="Search the web for current information"
    )
]
```

## Use Cases

- **Question Answering** - Quick answers with source attribution
- **Research Assistants** - Deep research with structured facts
- **RAG Systems** - Retrieve current information for context
- **News Monitoring** - Track recent events and developments
- **Fact Checking** - Verify information across multiple sources

## Security Notes

- **Rate Limiting**: Configure SearXNG's `limiter.toml` for production
- **API Keys**: Not required (SearXNG is self-hosted)
- **CORS**: Currently allows all origins - restrict in production
- **Network**: Use Docker networks to isolate services

## Troubleshooting

### SearXNG returns 403 Forbidden

```bash
# Check if JSON format is enabled in config/settings.yml
docker exec searxng grep -A 3 "formats:" /etc/searxng/settings.yml

# Should show:
# formats:
#   - html
#   - json
```

### Connection refused errors

```bash
# Ensure services are running
docker compose ps

# Check logs
docker compose logs searxng
docker compose logs mcp-websearch
```

### No search results

```bash
# Test SearXNG directly
curl -X POST http://localhost:8888/search \
  -H "X-Forwarded-For: 127.0.0.1" \
  --data "q=test&format=json"
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- [SearXNG](https://github.com/searxng/searxng) - Privacy-respecting metasearch engine
- [Model Context Protocol](https://modelcontextprotocol.io) - Anthropic's MCP specification
- [Starlette](https://www.starlette.io/) - Lightweight ASGI framework

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## Support

- **Issues**: [GitHub Issues](https://github.com/slinusc/web-search-mcp-server/issues)
- **Discussions**: [GitHub Discussions](https://github.com/slinusc/web-search-mcp-server/discussions)
