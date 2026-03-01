import http.server
import socketserver
import threading
import time
import subprocess
import os

# 切换到目标目录
os.chdir(r'D:\虚拟人\人设集合\大厂搬砖工')

# 获取第一个 jpg 文件
files = [f for f in os.listdir('.') if f.endswith('.jpg')]
target_file = files[0]
print(f'Target file: {target_file}')

# 启动简单的 HTTP 服务器
PORT = 8766
handler = http.server.SimpleHTTPRequestHandler

httpd = socketserver.TCPServer(("", PORT), handler)
server_thread = threading.Thread(target=httpd.serve_forever)
server_thread.daemon = True
server_thread.start()

print(f'HTTP server started on port {PORT}')
time.sleep(1)

# 调用 mcporter - 用 function-call 语法
image_url = f'http://localhost:{PORT}/{target_file}'
print(f'Image URL: {image_url}')

cmd = f'mcporter call "image-recognition.recognize_image(image_url: \\"{image_url}\\")"'
print(f'Running: {cmd}')
result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

print("=== RESULT ===")
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

httpd.shutdown()
print('Done')
