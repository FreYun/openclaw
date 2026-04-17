#!/usr/bin/env python3
"""
轻量文章抓取器 — 替代 browser_snapshot 读新闻，节省 90%+ 上下文。

用法：
    python fetch_article.py <url>
    python fetch_article.py <url1> <url2> <url3>

返回：每条 URL 的标题 + 正文纯文本，用分隔线隔开。

支持站点：
    - finance.eastmoney.com（东方财富）
    - mp.weixin.qq.com（微信公众号，不保证 100% 成功）
    - www.cls.cn（财联社）
    - www.stcn.com / stcn.com（证券时报/券商中国）
    - news.cctv.com��央视新闻）
    - www.news.cn / xinhuanet.com（新华社）
    - 其他站点：通用提取（<article> / <p> 标签）
"""

import sys
import re
import urllib.request
import urllib.error
from html.parser import HTMLParser

DESKTOP_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)
TIMEOUT = 15


def fetch_html(url: str, ua: str = DESKTOP_UA, referer: str = "") -> str:
    """Fetch HTML with appropriate headers."""
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def strip_tags(html_text: str) -> str:
    """Remove HTML tags, decode entities, clean whitespace."""
    text = re.sub(r"<br\s*/?>", "\n", html_text)
    text = re.sub(r"</?(p|div|section|h[1-6]|blockquote|ul|ol|li|tr)[^>]*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#39;", "'", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Site-specific extractors ��─────────────────────────────────────


def extract_eastmoney(html: str) -> dict:
    """东方财富 finance.eastmoney.com"""
    title_m = re.search(r"<title>(.*?)</title>", html, re.S)
    title = strip_tags(title_m.group(1)).split("_")[0].strip() if title_m else ""

    # Source & time from meta
    source_m = re.search(r'<span[^>]*>来源：(.*?)</span>', html, re.S)
    source = strip_tags(source_m.group(1)) if source_m else ""

    time_m = re.search(
        r"<span[^>]*>\d{4}年\d{2}月\d{2}日\s*\d{2}:\d{2}</span>", html
    )
    pub_time = strip_tags(time_m.group(0)) if time_m else ""

    # Body: try multiple selectors
    body = ""
    for pattern in [
        r'<div[^>]*class="txtinfos"[^>]*>(.*?)</div>',
        r'<div[^>]*id="ContentBody"[^>]*>(.*?)</div>',
        r'<div[^>]*class="Body"[^>]*>(.*?)</div>\s*<div',
    ]:
        m = re.search(pattern, html, re.S)
        if m:
            body = strip_tags(m.group(1))
            break

    # Remove trailing boilerplate
    for marker in ["（文章来源：", "（来源：", "东财图解", "关注同花顺"]:
        idx = body.find(marker)
        if idx > 0:
            body = body[:idx].strip()

    return {"title": title, "source": source, "time": pub_time, "body": body}


def extract_weixin(html: str) -> dict:
    """��信公众号 mp.weixin.qq.com"""
    # Check anti-scraping
    if "环境异常" in html and "js_content" not in html:
        return {"title": "", "body": "", "error": "微信返回验证页面，curl 被拦截"}

    title_m = re.search(r'var msg_title\s*=\s*["\'](.+?)["\']', html)
    if not title_m:
        title_m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    title = strip_tags(title_m.group(1)) if title_m else ""

    acct_m = re.search(r'var nickname\s*=\s*["\'](.+?)["\']', html)
    source = acct_m.group(1) if acct_m else ""

    time_m = re.search(r'var ct\s*=\s*"(\d+)"', html)
    pub_time = ""
    if time_m:
        import datetime
        pub_time = datetime.datetime.fromtimestamp(int(time_m.group(1))).strftime(
            "%Y-%m-%d %H:%M"
        )

    body_m = re.search(
        r'<div[^>]*id="js_content"[^>]*>(.*?)(?:</div>\s*<script|<div[^>]*class="ct_mpda_wrp)',
        html,
        re.S,
    )
    body = strip_tags(body_m.group(1)) if body_m else ""

    return {"title": title, "source": source, "time": pub_time, "body": body}


def extract_generic(html: str) -> dict:
    """通用提取：title + 最大的 <article> 或正文 <p> 集合"""
    title_m = re.search(r"<title>(.*?)</title>", html, re.S)
    title = strip_tags(title_m.group(1)).strip() if title_m else ""

    # Try <article>
    article_m = re.search(r"<article[^>]*>(.*?)</article>", html, re.S)
    if article_m:
        body = strip_tags(article_m.group(1))
    else:
        # Collect all <p> tags
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, re.S)
        body = "\n\n".join(strip_tags(p) for p in paragraphs if len(strip_tags(p)) > 20)

    return {"title": title, "body": body}


# ── Router ────────────────────────────────────────────────────────


def fetch_article(url: str) -> dict:
    """Fetch and extract article content from URL."""
    domain = re.search(r"https?://([^/]+)", url)
    if not domain:
        return {"error": f"无效 URL: {url}"}
    host = domain.group(1).lower()

    try:
        if "mp.weixin.qq.com" in host:
            html = fetch_html(url, ua=MOBILE_UA, referer="https://mp.weixin.qq.com/")
            result = extract_weixin(html)
        elif "eastmoney.com" in host:
            html = fetch_html(url)
            result = extract_eastmoney(html)
        else:
            html = fetch_html(url)
            result = extract_generic(html)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {url}"}
    except Exception as e:
        return {"error": f"请求失败: {e}"}

    result["url"] = url
    if not result.get("body") and not result.get("error"):
        result["error"] = "未提取到正文，可能需要浏览器访问"
    return result


# ── Main ──────────────────────────────────────────────────────────


def main():
    if len(sys.argv) < 2:
        print("用法: python fetch_article.py <url> [url2] [url3] ...")
        sys.exit(1)

    urls = sys.argv[1:]
    for i, url in enumerate(urls):
        if i > 0:
            print("\n" + "=" * 60 + "\n")

        result = fetch_article(url)

        if result.get("error"):
            print(f"[错��] {result['error']}")
            print(f"URL: {url}")
            print("→ 请改用浏览器访问此链接")
            continue

        if result.get("title"):
            print(f"标题：{result['title']}")
        if result.get("source"):
            print(f"来源：{result['source']}")
        if result.get("time"):
            print(f"时间：{result['time']}")
        print()
        print(result.get("body", ""))


if __name__ == "__main__":
    main()
