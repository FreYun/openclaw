$ErrorActionPreference = 'Stop'
$headers = @{Accept='application/json,text/event-stream'}

# Initialize session
$body = @{
    jsonrpc = '2.0'
    id = 0
    method = 'initialize'
    params = @{
        protocolVersion = '2024-11-05'
        capabilities = @{}
        clientInfo = @{name='test';version='1.0.0'}
    }
} | ConvertTo-Json -Compress

$null = Invoke-RestMethod -Uri 'http://localhost:18060/mcp' -Method Post -ContentType 'application/json' -Headers $headers -Body $body

# Send initialized notification
$null = Invoke-RestMethod -Uri 'http://localhost:18060/mcp' -Method Post -ContentType 'application/json' -Headers $headers -Body '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# Call get_login_qrcode
$response = Invoke-RestMethod -Uri 'http://localhost:18060/mcp' -Method Post -ContentType 'application/json' -Headers $headers -Body @{
    jsonrpc = '2.0'
    id = 1
    method = 'tools/call'
    params = @{
        name = 'get_login_qrcode'
        arguments = @{}
    }
} | ConvertTo-Json -Depth 10

Write-Host "Response:"
Write-Host $response

# Extract image data
$result = $response | ConvertFrom-Json
if ($result.result -and $result.result.content) {
    foreach ($item in $result.result.content) {
        if ($item.type -eq 'image' -and $item.data) {
            Write-Host "`nFound image data!"
            Write-Host "Length: $($item.data.Length) chars"
            # Save to file
            $bytes = [Convert]::FromBase64String($item.data)
            [IO.File]::WriteAllBytes("D:\.openclaw\workspace\qrcode.png", $bytes)
            Write-Host "Saved to D:\.openclaw\workspace\qrcode.png"
        }
        if ($item.type -eq 'text') {
            Write-Host "`nText: $($item.text)"
        }
    }
}
