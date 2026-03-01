---
name: image-recognition
description: Analyze and describe images using AI vision capabilities. Use when the user provides an image (URL, local file path, or data URI) and asks for description, analysis, OCR, or any visual understanding task. Handles automatic conversion of local file paths to accessible URLs before processing.
---

# Image Recognition

## Overview

This skill enables AI-powered image analysis including:
- General image description and scene understanding
- Text extraction (OCR)
- Object detection and identification
- Visual question answering about image content

## Input Handling Workflow

Images can be provided in three formats. Follow this decision tree:

```
Is the input a URL? (starts with http:// or https://)
├── YES → Use directly with read tool
│
└── NO → Is it a local file path?
    ├── YES → Use absolute path directly with read tool
    │   ⚠️ Note: Windows paths with Chinese characters may have encoding issues
    │       If encoding fails, copy file to workspace first
    │
    └── NO → Assume it's a data URI or base64
              → Use directly with read tool
```

### Critical Rules

1. **Local file paths**: The `read` tool accepts absolute paths directly. No conversion needed.

2. **Windows encoding issues**: If the path contains non-ASCII characters (e.g., Chinese), command-line tools may fail due to encoding. Workaround:
   ```python
   # Copy to workspace first, then read
   import shutil; shutil.copy2(r"D:\中文路径\image.jpg", "temp.jpg")
   # Then use read tool with "temp.jpg"
   ```

## Usage Examples

### Example 1: URL Input
```
User: "Describe this image: https://example.com/photo.jpg"
→ Directly use read tool with the URL
```

### Example 2: Local File Path (ASCII only)
```
User: "What's in this image? C:\\photos\\vacation.jpg"
→ Directly use read tool with the absolute path
```

### Example 2b: Local File Path (with Chinese characters)
```
User: "分析一下这张图：D:\\图片\\截图.jpg"
→ Encoding issues may occur, copy first:
  python -c "import shutil; shutil.copy2(r'D:\\图片\\截图.jpg', 'temp.jpg')"
→ Then use read tool with "temp.jpg"
```

### Example 3: Data URI
```
User: "[attached image as base64]"
→ Use directly with read tool
```

## Scripts

### path_to_url.py
Converts local file paths to file:// URLs that can be used with the read tool.

**Usage:**
```bash
python scripts/path_to_url.py "/path/to/image.jpg"
python scripts/path_to_url.py "C:\\Users\\name\\image.png"
```

**Output:** A file:// URL ready for use with read tool

**Behavior:**
- Validates that the file exists
- Handles both Unix (/path) and Windows (C:\path) paths
- Properly escapes special characters
- Returns error if file not found

## Analysis Guidelines

When analyzing images:

1. **Be specific** - Name objects, colors, quantities when relevant
2. **Describe context** - What's happening, where is it, what's the mood
3. **Note text** - Transcribe any visible text (signs, labels, screens)
4. **Answer questions** - If user asked something specific, address it directly
5. **Be honest** - If uncertain, say so rather than hallucinate details
