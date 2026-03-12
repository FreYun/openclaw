#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
import os

# 创建输出目录
os.makedirs('/home/rooot/.openclaw/workspace-bot5/images', exist_ok=True)

# 图片规格：竖版 3:4
WIDTH, HEIGHT = 1080, 1440

# 卡片内容（月度复盘拆分）
cards = [
    ("2 月黄金复盘\n\n避险失效了？\n别慌", "#2C3E50"),
    ("黄金避的不是炮火\n\n黄金避的是货币", "#34495E"),
    ("油价涨 → 通胀预期升温\n\n降息预期后移 → 黄金承压", "#5D6D7E"),
    ("涨太多了\n\n从避险资产变成了\n风险资产", "#7F8C8D"),
    ("长期逻辑变了吗？\n\n没有！", "#27AE60"),
    ("央行还在买\n\n美债问题没解决", "#2ECC71"),
    ("风浪越大\n\n鱼越贵", "#E67E22"),
    ("我的策略很简单\n\n拿着不动，慢慢变富🪙", "#8E44AD"),
]

# 尝试加载中文字体
font_paths = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "C:\\Windows\\Fonts\\simhei.ttf",
]

font = None
for fp in font_paths:
    try:
        font = ImageFont.truetype(fp, 60)
        print(f"Using font: {fp}")
        break
    except:
        continue

if not font:
    font = ImageFont.load_default()
    print("Using default font")

title_font = ImageFont.truetype(font.path, 80) if hasattr(font, 'path') else font

for i, (text, color) in enumerate(cards):
    # 创建图片
    img = Image.new('RGB', (WIDTH, HEIGHT), color=color)
    draw = ImageDraw.Draw(img)
    
    # 计算文字位置（居中）
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (WIDTH - text_width) // 2
    y = (HEIGHT - text_height) // 2
    
    # 绘制文字（白色）
    draw.text((x, y), text, fill='white', font=font)
    
    # 保存
    filepath = f'/home/rooot/.openclaw/workspace-bot5/images/card_{i+1}.png'
    img.save(filepath)
    print(f"Created: {filepath}")

print("\nAll cards generated!")
