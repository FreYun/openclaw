@echo off
rem OpenClaw Gateway (v2026.2.27)
set "HOME=C:\Users\想去利马"
set "TMPDIR=C:\Users\想去利马\AppData\Local\Temp"
set "PATH=D:\openclaw\node_modules\.bin;C:\Users\想去利马\AppData\Local\pnpm\.tools\pnpm\10.23.0_tmp_23752\node_modules\pnpm\dist\node-gyp-bin;D:\openclaw\node_modules\.bin;C:\Users\想去利马\AppData\Local\pnpm\.tools\pnpm\10.23.0\bin;C:\Python314\Scripts\;C:\Python314\;C:\Windows\system32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0\;C:\Windows\System32\OpenSSH\;C:\Program Files (x86)\NVIDIA Corporation\PhysX\Common;C:\Program Files\dotnet\;C:\Program Files\NVIDIA Corporation\NVIDIA App\NvDLISR;C:\Program Files\nodejs\;C:\ProgramData\chocolatey\bin;C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI\;C:\Users\想去利马\AppData\Local\Microsoft\WindowsApps;;D:\PyCharm Community Edition 2024.3\bin;;D:\Microsoft VS Code\bin;D:\cursor\resources\app\bin;C:\Users\想去利马\AppData\Roaming\npm"
set "OPENCLAW_GATEWAY_PORT=18789"
set "OPENCLAW_GATEWAY_TOKEN=da9cf2d75ec101f8b07c55dc381f019658a3c5e5cde62fd8"
set "OPENCLAW_SYSTEMD_UNIT=openclaw-gateway.service"
set "OPENCLAW_SERVICE_MARKER=openclaw"
set "OPENCLAW_SERVICE_KIND=gateway"
set "OPENCLAW_SERVICE_VERSION=2026.2.27"
"C:\Program Files\nodejs\node.exe" D:\openclaw\dist\index.js gateway --port 18789
