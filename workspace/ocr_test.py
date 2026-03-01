import base64
import subprocess
import json

# 读取 base64 数据
with open(r'D:\.openclaw\.openclaw\workspace\temp_image.txt', 'r') as f:
    b64_data = f.read().strip()

# 构建 data URL
data_url = f'data:image/jpeg;base64,{b64_data}'

# 调用 mcporter
cmd = 'mcporter call image-recognition.recognize_image image_data="{}"'.format(data_url)
result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)
