# Gemini Image Generation

## Config

| Key | Value |
|-----|-------|
| **Base URL** | `https://dd-ai-api.eastmoney.com/v1` |
| **API Key** | `AQ.Ab8RN6JQNCE2rHq04-EprnfJ7TWEiSkh2rddL_aN1wrI9btf3A` |
| **Model** | `gemini-3-pro-image-preview` |

## Sizes

| Use Case | Size |
|----------|------|
| XHS vertical (default) | 1024x1536 |
| Square | 1024x1024 |
| Landscape | 1536x1024 |

## Generate Image

```bash
curl -s -X POST "https://dd-ai-api.eastmoney.com/v1/images/generations" \
  -H "Authorization: Bearer AQ.Ab8RN6JQNCE2rHq04-EprnfJ7TWEiSkh2rddL_aN1wrI9btf3A" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-pro-image-preview",
    "prompt": "YOUR_ENGLISH_PROMPT",
    "n": 1,
    "size": "1024x1536"
  }' | python3 -c "
import json, sys, base64, os
r = json.load(sys.stdin)
folder = sys.argv[1]
os.makedirs(folder, exist_ok=True)
for i, img in enumerate(r.get('data', [])):
    if img.get('b64_json'):
        path = f'{folder}/{i+1:03d}.png'
        with open(path, 'wb') as f:
            f.write(base64.b64decode(img['b64_json']))
        print(f'Saved: {path}')
    elif img.get('url'):
        print(f'URL: {img[\"url\"]}')
    else:
        print(f'Unknown format: {list(img.keys())}')
" "$OUTPUT_DIR"
```

## Prompt Optimization

Write prompts in English. Include:
1. **Subject** — what to draw
2. **Style** — photorealistic / illustration / watercolor / 3D render / etc.
3. **Composition** — close-up / wide angle / centered / etc.
4. **Lighting** — soft natural / golden hour / studio / etc.
5. **Quality** — high quality, detailed, 4k

## Output

Save to `/tmp/image-generator/{YYYY-MM-DD}_{HHmmss}_{desc}/`:
- `001.png` — generated image
- `prompt.txt` — final English prompt
- `metadata.json` — task metadata
