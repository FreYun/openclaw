#!/usr/bin/env python3
"""inspect_cookies.py — 检查小红书 Chrome profile 中的 cookie 状态。

用法:
    python inspect_cookies.py <account_id>
    python inspect_cookies.py bot7
    python inspect_cookies.py bot10 --all   # 显示所有 cookie，不仅 xiaohongshu
"""

import sqlite3
import sys
import os
import shutil
import tempfile
import datetime

PROFILES_ROOT = os.environ.get("XHS_PROFILES_DIR", "/home/rooot/.xhs-profiles")

# 登录关键 cookie
LOGIN_COOKIES = {
    "web_session": "主站登录 session",
    "galaxy_creator_session_id": "创作者平台 session",
    "customer-sso-sid": "SSO session",
    "access-token-creator.xiaohongshu.com": "创作者平台 access token",
    "galaxy.creator.beaker.session.id": "创作者 beaker session",
    "x-user-id-creator.xiaohongshu.com": "创作者平台 user ID",
    "id_token": "身份令牌",
}


def chrome_time_to_datetime(chrome_time):
    """Chrome cookie 时间戳转 datetime (微秒, epoch = 1601-01-01)。"""
    if chrome_time == 0:
        return None
    epoch = datetime.datetime(1601, 1, 1)
    try:
        return epoch + datetime.timedelta(microseconds=chrome_time)
    except (OverflowError, OSError):
        return None


def inspect(account_id, show_all=False):
    profile_dir = os.path.join(PROFILES_ROOT, account_id)
    cookie_db = os.path.join(profile_dir, "Default", "Cookies")

    if not os.path.exists(profile_dir):
        print(f"[ERROR] Profile 目录不存在: {profile_dir}")
        sys.exit(1)
    if not os.path.exists(cookie_db):
        print(f"[ERROR] Cookie 数据库不存在: {cookie_db}")
        print(f"  Profile 目录存在，但 Default/Cookies 文件缺失。")
        print(f"  可能该 profile 从未启动过 Chrome。")
        sys.exit(1)

    # 复制 DB 以避免锁冲突（Chrome 可能正在使用）
    tmp = tempfile.mktemp(suffix=".db")
    shutil.copy2(cookie_db, tmp)

    try:
        conn = sqlite3.connect(tmp)
        conn.row_factory = sqlite3.Row

        if show_all:
            query = "SELECT name, host_key, path, expires_utc, is_httponly, is_secure, samesite FROM cookies ORDER BY host_key, name"
        else:
            query = "SELECT name, host_key, path, expires_utc, is_httponly, is_secure, samesite FROM cookies WHERE host_key LIKE '%xiaohongshu%' ORDER BY name"

        rows = conn.execute(query).fetchall()
        conn.close()
    finally:
        os.unlink(tmp)

    if not rows:
        print(f"[{account_id}] 没有找到小红书相关的 cookie")
        print(f"  状态: 未登录（无 cookie）")
        return

    # 登录状态判断
    cookie_names = {r["name"] for r in rows}
    has_main = "web_session" in cookie_names
    has_creator = "galaxy_creator_session_id" in cookie_names

    print(f"=== {account_id} Cookie 检查报告 ===")
    print(f"Profile: {profile_dir}")
    print(f"Cookie DB: {cookie_db}")
    print()

    # 登录状态
    print("--- 登录状态 ---")
    print(f"  主站:       {'✅ 已登录 (web_session 存在)' if has_main else '❌ 未登录'}")
    print(f"  创作者平台: {'✅ 已登录 (galaxy_creator_session_id 存在)' if has_creator else '❌ 未登录'}")
    print()

    # 关键 cookie 详情
    print("--- 关键 Cookie ---")
    for key, desc in LOGIN_COOKIES.items():
        found = [r for r in rows if r["name"] == key]
        if found:
            r = found[0]
            exp = chrome_time_to_datetime(r["expires_utc"])
            exp_str = exp.strftime("%Y-%m-%d %H:%M") if exp else "Session"
            expired = ""
            if exp and exp < datetime.datetime.now():
                expired = " [已过期!]"
            print(f"  ✅ {key}")
            print(f"     {desc} | 过期: {exp_str}{expired} | HttpOnly: {bool(r['is_httponly'])}")
        else:
            print(f"  ❌ {key}")
            print(f"     {desc} | 未找到")
    print()

    # 所有 cookie 列表
    print(f"--- 全部 Cookie ({len(rows)} 条) ---")
    print(f"{'Name':45s}  {'Domain':30s}  {'Expires':20s}  {'Flags'}")
    print("-" * 120)
    for r in rows:
        exp = chrome_time_to_datetime(r["expires_utc"])
        exp_str = exp.strftime("%Y-%m-%d %H:%M") if exp else "Session"
        flags = []
        if r["is_httponly"]:
            flags.append("HttpOnly")
        if r["is_secure"]:
            flags.append("Secure")
        samesite_map = {0: "", 1: "Lax", 2: "Strict", -1: "None"}
        ss = samesite_map.get(r["samesite"], "")
        if ss:
            flags.append(f"SameSite={ss}")
        print(f"{r['name']:45s}  {r['host_key']:30s}  {exp_str:20s}  {', '.join(flags)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python inspect_cookies.py <account_id> [--all]")
        print("  account_id: bot1, bot7, bot10 等")
        print("  --all: 显示所有 cookie，不仅 xiaohongshu 相关")
        sys.exit(1)

    account = sys.argv[1]
    show_all = "--all" in sys.argv
    inspect(account, show_all)
