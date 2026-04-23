#!/usr/bin/env python3
"""搞钱小财迷封面渲染器 — bot 调用入口

用法：
  # 封面（剧照+文字卡片）
  python3 render.py cover --tpl 05-阳光 --title "月薪8千的上海女生 💰<br>3年存下20万" --subtitle "✨ 不是省出来的，是分出来的" --body "正文内容" -o /tmp/cover.png

  # 内页（米色背景+编号小节）
  python3 render.py inner --page-title "⚠️ Token注意事项 💸" --sections '[{"title":"警惕隐藏消耗 🧐","body":"说明文字"},{"title":"优化技巧 📋","body":"说明文字"}]' --tip "💡 最后提醒：搞钱要稳" -o /tmp/inner.png
"""

import argparse, json, os, sys, tempfile

WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TPL_DIR = os.path.join(WORKSPACE, "茱莉亚图包", "templates")

# ─── HTML Templates ───

COVER_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1024px;height:1536px;overflow:hidden;font-family:"PingFang SC","Noto Sans SC","Noto Color Emoji","Microsoft YaHei",sans-serif}}
.cover{{width:1024px;height:1536px;position:relative;background:url('{bg}') center/cover no-repeat}}
.text-area{{position:absolute;top:570px;left:56px;right:56px}}
.title{{font-size:72px;font-weight:900;line-height:1.3;color:#1A1A1A;letter-spacing:-1px}}
.subtitle{{font-size:32px;color:#B08D57;margin-top:48px;line-height:1.5}}
.body-text{{font-size:30px;color:#333;margin-top:36px;line-height:1.75}}
</style></head><body>
<div class="cover"><div class="text-area">
<div class="title">{title}</div>
<div class="subtitle">{subtitle}</div>
<div class="body-text">{body}</div>
</div></div></body></html>"""

INNER_HTML_HEAD = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1024px;height:1536px;overflow:hidden;font-family:"PingFang SC","Noto Sans SC","Noto Color Emoji","Microsoft YaHei",sans-serif}}
.page{{width:1024px;height:1536px;position:relative;background:url('{bg}') center/cover no-repeat;padding:72px 64px}}
.page-title{{font-size:64px;font-weight:900;line-height:1.3;color:#8B6914;margin-bottom:48px}}
.section{{margin-bottom:40px}}
.section-head{{font-size:40px;font-weight:800;color:#5C3D1A;margin-bottom:16px;display:flex;align-items:center;gap:12px}}
.badge{{display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;background:#B08D57;color:#fff;border-radius:10px;font-size:26px;font-weight:700;flex-shrink:0}}
.section-body{{font-size:30px;color:#4A3A2A;line-height:1.7;margin-left:56px}}
.tip-box{{margin-top:48px;background:rgba(176,141,87,.08);border-radius:16px;padding:32px 36px}}
.tip-label{{font-size:28px;color:#B08D57;margin-bottom:12px}}
.tip-text{{font-size:28px;color:#5C3D1A;line-height:1.7}}
</style></head><body><div class="page">
<div class="page-title">{page_title}</div>"""

SECTION_HTML = """<div class="section">
<div class="section-head"><span class="badge">{idx}</span> {title}</div>
<div class="section-body">{body}</div></div>"""

TIP_HTML = """<div class="tip-box">
<div class="tip-label">{label}</div>
<div class="tip-text">{text}</div></div>"""

INNER_HTML_TAIL = "</div></body></html>"


def find_tpl(name):
    """Match template by short name, e.g. '05-阳光' or '05'."""
    for f in os.listdir(TPL_DIR):
        if name in f and f.endswith(".png"):
            return os.path.join(TPL_DIR, f)
    raise FileNotFoundError(f"找不到底板: {name}，可用: {os.listdir(TPL_DIR)}")


def render_html(html, output):
    """Write HTML to temp file, screenshot with Playwright."""
    from playwright.sync_api import sync_playwright

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, dir="/tmp") as f:
        f.write(html)
        html_path = f.name

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1024, "height": 1536})
        page.goto(f"file://{html_path}", wait_until="load")
        page.wait_for_timeout(600)
        page.screenshot(path=output)
        browser.close()

    os.unlink(html_path)
    print(output)


def cmd_cover(args):
    bg = find_tpl(args.tpl)
    html = COVER_HTML.format(
        bg=bg, title=args.title,
        subtitle=args.subtitle or "",
        body=args.body or "",
    )
    render_html(html, args.output)


def cmd_inner(args):
    bg = os.path.join(TPL_DIR, "tpl-inner.png")
    parts = [INNER_HTML_HEAD.format(bg=bg, page_title=args.page_title)]

    sections = json.loads(args.sections) if args.sections else []
    for i, sec in enumerate(sections, 1):
        parts.append(SECTION_HTML.format(idx=i, title=sec["title"], body=sec["body"]))

    if args.tip:
        # tip format: "💡 label：text" or just text
        if "：" in args.tip:
            label, text = args.tip.split("：", 1)
            parts.append(TIP_HTML.format(label=label.strip(), text=text.strip()))
        else:
            parts.append(TIP_HTML.format(label="💡 提醒", text=args.tip))

    parts.append(INNER_HTML_TAIL)
    render_html("".join(parts), args.output)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="搞钱小财迷封面渲染器")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # cover
    p1 = sub.add_parser("cover", help="封面（剧照+文字卡片）")
    p1.add_argument("--tpl", required=True, help="底板短名，如 05-阳光、01-沉静")
    p1.add_argument("--title", required=True, help="大标题，用 <br> 换行")
    p1.add_argument("--subtitle", default="", help="副标题")
    p1.add_argument("--body", default="", help="正文，用 <br> 换行")
    p1.add_argument("-o", "--output", default="/tmp/caimi-cover.png", help="输出路径")

    # inner
    p2 = sub.add_parser("inner", help="内页（米色+编号小节）")
    p2.add_argument("--page-title", required=True, help="页标题")
    p2.add_argument("--sections", default="[]", help='JSON数组: [{"title":"...", "body":"..."}]')
    p2.add_argument("--tip", default="", help="底部提醒，格式: 💡 label：text")
    p2.add_argument("-o", "--output", default="/tmp/caimi-inner.png", help="输出路径")

    args = ap.parse_args()
    {"cover": cmd_cover, "inner": cmd_inner}[args.cmd](args)
