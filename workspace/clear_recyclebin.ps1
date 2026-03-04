# 清空回收站
$ErrorActionPreference = "Stop"
Clear-RecycleBin -Force -ErrorAction SilentlyContinue

# 如果上面不行，尝试用 COM 对象
if ($LASTEXITCODE -ne 0) {
    $sh = New-Object -ComObject Shell.Application
    $bin = $sh.Namespace(10)  # 10 = 回收站
    foreach ($item in $bin.Items()) {
        $item.InvokeVerb("delete")
    }
}
Write-Host "回收站清空完成"
