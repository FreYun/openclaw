$ErrorActionPreference = 'Continue'
$headers = @{Accept='application/json,text/event-stream'}

# 初始化会话
$body = '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}'
$null = Invoke-RestMethod -Uri 'http://localhost:18060/mcp' -Method Post -ContentType 'application/json' -Headers $headers -Body $body -ErrorAction SilentlyContinue

# 发送 initialized 通知
$null = Invoke-RestMethod -Uri 'http://localhost:18060/mcp' -Method Post -ContentType 'application/json' -Headers $headers -Body '{"jsonrpc":"2.0","method":"notifications/initialized"}' -ErrorAction SilentlyContinue

# 获取二维码
$resp = Invoke-WebRequest -Uri 'http://localhost:18060/mcp' -Method Post -ContentType 'application/json' -Headers $headers -Body '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_login_qrcode","arguments":{}}}'

# 保存原始响应
$resp.Content | Out-File -FilePath "D:\.openclaw\workspace\mcp_raw.txt" -Encoding utf8
Write-Host "原始响应已保存"

# 解析并提取图片
$json = $resp.Content | ConvertFrom-Json
foreach ($item in $json.result.content) {
  if ($item.type -eq 'image' -and $item.data) {
    Write-Host "找到图片，长度: $($item.data.Length)"
    $bytes = [Convert]::FromBase64String($item.data)
    [IO.File]::WriteAllBytes("D:\.openclaw\workspace\qrcode.png", $bytes)
    Write-Host "二维码已保存到 qrcode.png"
  }
  if ($item.type -eq 'text') {
    Write-Host "文本: $($item.text)"
  }
}