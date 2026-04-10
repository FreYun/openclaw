#!/usr/bin/env python3
"""
腾讯文档基金池自动下载脚本

用法:
  # 下载当月基金池（自动检测登录状态，需要时发二维码到飞书）
  python3 download_fund_pools.py --bot bot9

  # 手动触发登录
  python3 download_fund_pools.py --bot bot9 --login

  # 下载指定月份
  python3 download_fund_pools.py --bot bot9 --month 202605

  # 有头模式调试
  python3 download_fund_pools.py --bot bot9 --headed

--bot 参数必须指定，脚本会自动从该 bot 的 sessions.json 读取飞书账号和目标用户。
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── 配置 ──────────────────────────────────────────────
SHARE_URL = "https://docs.qq.com/s/KEims9pfBxkMG6-ujR4wYq"
FOLDER_NAME = "天天基金研究部-基金池汇总"
PROFILE_DIR = os.path.expanduser("~/.tencent-docs-profile")
OPENCLAW_DIR = "/home/rooot/.openclaw"
TARGET_FILES = ["权益基金池", "指数基金池"]
QR_SCREENSHOT_PATH = "/tmp/tencent-docs-qrcode.png"

# 运行时由 --bot 参数填充
FEISHU_BOT = None
FEISHU_TARGET = None
SKILL_DIR = None


def get_current_month():
    return datetime.now().strftime("%Y%m")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def resolve_bot(bot_id):
    """从 bot 的 sessions.json 读取飞书账号和目标用户，设置全局变量。"""
    global FEISHU_BOT, FEISHU_TARGET, SKILL_DIR

    FEISHU_BOT = bot_id
    # skill 目录：通过 symlink 解析到实际 workspace 下的路径
    skill_link = Path(OPENCLAW_DIR) / f"workspace-{bot_id}" / "skills" / "daily-market-recap"
    SKILL_DIR = str(skill_link.resolve()) if skill_link.exists() else str(skill_link)

    # 从 sessions.json 找飞书直聊 target
    sessions_file = Path(OPENCLAW_DIR) / "agents" / bot_id / "sessions" / "sessions.json"
    if sessions_file.exists():
        try:
            sessions = json.loads(sessions_file.read_text())
            for sid, sess in sessions.items():
                if "feishu" in sid and "direct" in sid:
                    dc = sess.get("deliveryContext", {})
                    target = dc.get("to", "")
                    if target:
                        FEISHU_TARGET = target.replace("user:", "")
                        log(f"飞书配置: bot={bot_id}, target={FEISHU_TARGET}")
                        return
        except Exception as e:
            log(f"读取 sessions.json 失败: {e}")

    log(f"警告: 未找到 {bot_id} 的飞书直聊配置，二维码将无法发送")


def send_feishu(message, media=None):
    """通过 openclaw CLI 发送飞书消息。"""
    if not FEISHU_BOT or not FEISHU_TARGET:
        log(f"飞书未配置，跳过发送: {message}")
        return
    cmd = [
        "openclaw", "message", "send",
        "--channel", "feishu",
        "--account", FEISHU_BOT,
        "--target", FEISHU_TARGET,
        "-m", message,
    ]
    if media:
        cmd += ["--media", media]
    try:
        subprocess.run(cmd, capture_output=True, timeout=30)
    except Exception as e:
        log(f"飞书发送失败: {e}")


# ── 登录模式 ──────────────────────────────────────────
def do_login(headless=True):
    """
    打开腾讯文档登录页，截取二维码通过飞书发送。
    headless=True 时无需显示器，二维码通过飞书接收。
    """
    os.makedirs(PROFILE_DIR, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=headless,
            accept_downloads=True,
            locale="zh-CN",
            viewport={"width": 800, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # 打开登录页
        page.goto("https://docs.qq.com/desktop/?nlc=1", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # 勾选隐私协议
        try:
            checkbox = page.get_by_role("checkbox", name="我已阅读并接受腾讯文档的")
            if checkbox.is_visible(timeout=3000) and not checkbox.is_checked():
                checkbox.click()
                time.sleep(1)
        except PWTimeout:
            pass

        # 等待二维码加载
        time.sleep(3)
        page.evaluate("window.scrollTo(0, 0)")

        # 截图并通过飞书发送
        page.screenshot(path=QR_SCREENSHOT_PATH, full_page=False)
        log("二维码已截图，通过飞书发送...")
        send_feishu("腾讯文档登录二维码，请用微信扫码", QR_SCREENSHOT_PATH)
        log("已发送到飞书，请尽快扫码（60秒内有效）")

        # 轮询等待登录成功（最多 90 秒）
        logged_in = False
        for i in range(30):
            time.sleep(3)
            # 检查是否已跳转到桌面（登录成功标志）
            if "desktop" in page.url and "nlc" not in page.url:
                logged_in = True
                break
            # 检查是否出现用户头像
            avatar = page.locator('img[alt="头像"], img.avatar')
            if avatar.count() > 0:
                logged_in = True
                break
            # 二维码可能过期，30秒后刷新一次
            if i == 10:
                log("二维码可能已过期，刷新中...")
                page.reload(wait_until="domcontentloaded")
                time.sleep(3)
                try:
                    checkbox = page.get_by_role("checkbox", name="我已阅读并接受腾讯文档的")
                    if checkbox.is_visible(timeout=2000) and not checkbox.is_checked():
                        checkbox.click()
                except PWTimeout:
                    pass
                time.sleep(3)
                page.evaluate("window.scrollTo(0, 0)")
                page.screenshot(path=QR_SCREENSHOT_PATH, full_page=False)
                send_feishu("二维码已刷新，请重新扫码", QR_SCREENSHOT_PATH)

        if logged_in:
            log("登录成功！")
            send_feishu("腾讯文档登录成功")
        else:
            log("登录超时，请重试")
            send_feishu("腾讯文档登录超时，请重新运行 --login")

        ctx.close()
        return logged_in


# ── 导出单个在线表格 ──────────────────────────────────
def export_sheet(sheet_page, file_label):
    """
    在已打开的腾讯文档在线表格页导出 xlsx。
    流程：点击 titlebar file 图标 → 点击"下载"菜单项。
    返回 Download 对象或 None。
    """
    sheet_page.wait_for_load_state("domcontentloaded", timeout=30000)
    time.sleep(5)

    try:
        # 点击 titlebar 的 file 图标（打开文件菜单）
        file_btn = sheet_page.get_by_label("file")
        if not file_btn.is_visible(timeout=5000):
            log(f"  找不到 file 菜单按钮")
            return None

        file_btn.click()
        time.sleep(1)

        # 在弹出的菜单中点击"下载"
        download_item = sheet_page.get_by_text("下载", exact=True).first
        if not download_item.is_visible(timeout=3000):
            log(f"  菜单中找不到'下载'选项")
            return None

        with sheet_page.expect_download(timeout=60000) as dl_info:
            download_item.click()

        return dl_info.value

    except PWTimeout:
        log(f"  导出超时")
        return None
    except Exception as e:
        log(f"  导出异常: {e}")
        return None


# ── 主流程 ────────────────────────────────────────────
def download_fund_pools(month=None, headless=True):
    month = month or get_current_month()
    os.makedirs(PROFILE_DIR, exist_ok=True)

    log(f"目标月份: {month}, 目标文件: {TARGET_FILES}")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=headless,
            accept_downloads=True,
            locale="zh-CN",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # 1. 打开分享页面
        log("打开分享页面 ...")
        page.goto(SHARE_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # 检查登录状态
        login_btn = page.locator('button:has-text("立即登录")')
        if login_btn.is_visible(timeout=3000):
            log("未登录 — 自动触发登录流程...")
            ctx.close()
            if not do_login(headless=headless):
                return False
            # 重新打开
            ctx = p.chromium.launch_persistent_context(
                PROFILE_DIR,
                headless=headless,
                accept_downloads=True,
                locale="zh-CN",
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(SHARE_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

        # 2. 点击进入文件夹
        log("进入文件夹 ...")
        # 点击 grid 中的文件夹链接（最后一个匹配，避免点到标题区）
        folder_links = page.locator(f"span:has-text('{FOLDER_NAME}')").all()
        if folder_links:
            folder_links[-1].click()
        time.sleep(5)

        # 等待文件列表出现（用第一个目标文件名判断）
        first_target = f"{month}-{TARGET_FILES[0]}"
        page.locator(f"text={first_target}").first.wait_for(state="visible", timeout=15000)

        downloaded = []

        for target in TARGET_FILES:
            file_label = f"{month}-{target}"
            log(f"处理: {file_label}")

            link = page.locator(f"text={file_label}").first
            try:
                link.wait_for(state="visible", timeout=5000)
            except PWTimeout:
                log(f"  未找到 {file_label}，跳过")
                continue

            # 点击打开（新标签页）
            with ctx.expect_page(timeout=15000) as new_page_info:
                link.click()
            sheet_page = new_page_info.value

            download = export_sheet(sheet_page, file_label)

            if download:
                dest = os.path.join(SKILL_DIR, f"{file_label}.xlsx")
                download.save_as(dest)
                downloaded.append(dest)
                log(f"  已保存: {dest}")
            else:
                log(f"  下载失败")

            sheet_page.close()

        ctx.close()

        # 3. 清理旧月份文件
        if downloaded:
            pattern = re.compile(r"^(\d{6})-(权益基金池|指数基金池)\.xlsx$")
            for f in os.listdir(SKILL_DIR):
                m = pattern.match(f)
                if m and m.group(1) != month:
                    old = os.path.join(SKILL_DIR, f)
                    os.remove(old)
                    log(f"  已删除旧文件: {f}")

        log(f"完成: {len(downloaded)}/{len(TARGET_FILES)} 个文件已下载")

        if downloaded:
            send_feishu(f"基金池更新完成: {', '.join(os.path.basename(d) for d in downloaded)}")

        return len(downloaded) == len(TARGET_FILES)


# ── CLI ───────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="腾讯文档基金池自动下载")
    parser.add_argument("--bot", type=str, required=True, help="Bot ID（如 bot9），用于确定飞书通知对象和 skill 目录")
    parser.add_argument("--login", action="store_true", help="登录（二维码通过飞书发送）")
    parser.add_argument("--month", type=str, help="指定月份 YYYYMM，默认当月")
    parser.add_argument("--headed", action="store_true", help="有头模式（调试用）")
    args = parser.parse_args()

    resolve_bot(args.bot)

    if args.login:
        ok = do_login(headless=not args.headed)
        sys.exit(0 if ok else 1)
    else:
        ok = download_fund_pools(
            month=args.month,
            headless=not args.headed,
        )
        sys.exit(0 if ok else 1)
