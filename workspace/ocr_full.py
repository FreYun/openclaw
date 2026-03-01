import base64
import subprocess
import os

# 切换到目标目录
os.chdir(r'D:\虚拟人\人设集合\大厂搬砖工')

# 获取第一个 jpg 文件
files = [f for f in os.listdir('.') if f.endswith('.jpg')]
if not files:
    print('No jpg files found')
    exit(1)

target_file = files[0]
print(f'Target file: {target_file}')

# 读取图片
with open(target_file, 'rb') as f:
    image_data = f.read()

print(f'Image size: {len(image_data)} bytes')

# 转 base64
b64_data = base64.b64encode(image_data).decode('ascii')
print(f'Base64 length: {len(b64_data)}')

# 构建 data URL
data_url = f'data:image/jpeg;base64,{b64_data}'

# 调用 mcporter
cmd = 'mcporter call image-recognition.recognize_image image_data="{}"'.format(data_url)
result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

print("=== RESULT ===")
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
