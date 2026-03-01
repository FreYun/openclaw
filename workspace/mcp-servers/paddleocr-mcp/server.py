#!/usr/bin/env python3
"""
PaddleOCR MCP Server - 本地 OCR 图片识别
"""

import sys
import base64
from io import BytesIO
from PIL import Image
from paddleocr import PaddleOCR

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("PaddleOCR")

# 初始化 PaddleOCR（中文 + 英文）
import os
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
ocr = PaddleOCR(lang='ch')


@mcp.tool()
def ocr_image(image_url: str = None, image_path: str = None, image_base64: str = None):
    """
    使用 PaddleOCR 识别图片中的文字
    
    Args:
        image_url: 图片 URL 地址
        image_path: 本地图片路径
        image_base64: 图片 base64 数据（可带 data:image/xxx;base64, 前缀）
    
    Returns:
        识别结果：包含文字内容和置信度
    """
    try:
        img = None
        
        # 加载图片
        if image_url:
            import requests
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
        elif image_path:
            img = Image.open(image_path)
        elif image_base64:
            # 移除 data:image/xxx;base64, 前缀
            if ',' in image_base64:
                image_base64 = image_base64.split(',', 1)[1]
            img_data = base64.b64decode(image_base64)
            img = Image.open(BytesIO(img_data))
        else:
            return {"error": "请提供 image_url、image_path 或 image_base64 之一"}
        
        # 转换为 numpy 数组（PaddleOCR 需要 BGR 格式）
        import numpy as np
        img_array = np.array(img)
        if len(img_array.shape) == 2:
            img_array = np.stack([img_array] * 3, axis=-1)
        if img_array.shape[-1] == 4:  # RGBA -> RGB
            img_array = img_array[:, :, :3]
        img_array = img_array[:, :, ::-1]  # RGB -> BGR
        
        # 执行 OCR（PaddleOCR 3.4+ API）
        result = ocr.ocr(img_array)
        
        # 解析结果
        texts = []
        if result and result[0]:
            for line in result[0]:
                bbox, (text, confidence) = line
                texts.append({
                    "text": text,
                    "confidence": round(confidence, 4),
                    "bbox": bbox
                })
        
        return {
            "success": True,
            "text_count": len(texts),
            "full_text": "\n".join([t["text"] for t in texts]),
            "details": texts
        }
        
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
