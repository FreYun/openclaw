from paddleocr import PaddleOCR
import os
import warnings
warnings.filterwarnings('ignore')

# 切换到工作区
os.chdir(r'D:\.openclaw\.openclaw\workspace')

# 初始化 OCR
ocr = PaddleOCR(lang='ch')

# 识别图片
img_path = 'test_image.jpg'
result = ocr.predict(img_path)

print("=== OCR RESULT ===")
if result and 'rec_texts' in result:
    texts = result['rec_texts']
    for text in texts:
        print(text)
else:
    print('No text detected')
