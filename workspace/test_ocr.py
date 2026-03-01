#!/usr/bin/env python3
import base64
import requests

# 读取图片转 base64
with open(r"D:\虚拟人\人设集合\大厂搬砖工\电网+CPO+有色_1_大厂搬砖工_来自小红书网页版.jpg", "rb") as f:
    img_data = base64.b64encode(f.read()).decode()

# 调用阿里云百炼 OCR API
api_key = "sk-8937a309c5f04f909aabd1ad255b3654"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# 使用 qwen-vl-max 进行图片识别
payload = {
    "model": "qwen-vl-max-latest",
    "input": {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"image": f"data:image/jpeg;base64,{img_data}"},
                    {"text": "请识别这张图片中的所有文字内容"}
                ]
            }
        ]
    }
}

# 使用正确的 dashscope API 端点
response = requests.post(
    "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
    headers=headers,
    json=payload,
    timeout=30
)

import json
result = response.json()
with open("ocr_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("结果已保存到 ocr_result.json")
# 打印文本内容
if "output" in result and "choices" in result["output"]:
    content = result["output"]["choices"][0]["message"]["content"]
    print("\n识别结果:")
    print(content)
