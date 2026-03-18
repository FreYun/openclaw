"""
permissions.py — 基于 bot_id 的权限控制

skill 部门通过 permissions.yaml 管理各 bot 的工具访问权限。
"""

import logging
import os

import yaml

logger = logging.getLogger("research-gateway")

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "permissions.yaml")
_config: dict | None = None


def _load_config() -> dict:
    global _config
    if _config is None:
        with open(_CONFIG_PATH, "r") as f:
            _config = yaml.safe_load(f)
    return _config


def reload_config():
    """重载权限配置（skill 部门修改 yaml 后调用）"""
    global _config
    _config = None
    _load_config()
    logger.info("Permissions config reloaded")


def get_allowed_tools(bot_id: str) -> list[str]:
    """返回某个 bot 可以使用的工具列表"""
    config = _load_config()
    bots = config.get("bots", {})
    role = bots.get(bot_id, bots.get("default", "content_creator"))
    roles = config.get("roles", {})
    return roles.get(role, [])


def is_allowed(bot_id: str, tool_name: str) -> bool:
    return tool_name in get_allowed_tools(bot_id)
