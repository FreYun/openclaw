import json, datetime
r = {
    'ts': datetime.datetime.now().astimezone().isoformat(),
    'reporter': 'bot2',
    'session_id': 'default',
    'level': 'ERROR',
    'type': 'MCP_ERROR',
    'message': 'tougu-portfolio-review任务失败：tougu-portfolio-mcp未注册，research-mcp返回502',
    'context': {'task': 'tougu-portfolio-review', 'missing_mcp': 'tougu-portfolio-mcp', 'broken_mcp': 'research-mcp'}
}
with open('/home/rooot/.openclaw/security/incidents.jsonl', 'a') as f:
    f.write(json.dumps(r, ensure_ascii=False) + '\n')
print('Incident logged')
