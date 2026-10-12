"""应用配置。

全部配置项都可以通过环境变量覆盖，默认值面向本地开发。
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "flavalon-dev-secret-change-me")
    JSON_AS_ASCII = False

    # SQLite 数据库文件位置
    DATABASE = os.environ.get("DATABASE_PATH", str(BASE_DIR / "data" / "flavalon.db"))

    # 初始管理员账号，仅在数据库还没有管理员时用于初始化
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    # 动态 flag（审核机器人持有），容器内通常位于 web 根之外
    FLAG_PATH = os.environ.get("FLAG_PATH", "/flag")

    # 审核机器人
    BOT_ENABLED = _env_bool("BOT_ENABLED", True)
    # 机器人访问站点使用的地址；留空时按 127.0.0.1:PORT 推导
    SELF_BASE_URL = os.environ.get("SELF_BASE_URL", "")
    # 机器人每次审核的等待时间（毫秒），给页面脚本留出执行时间
    BOT_REVIEW_DELAY_MS = int(os.environ.get("BOT_REVIEW_DELAY_MS", "1500"))
    # 浏览器可执行文件路径；留空则用 Playwright 自带的 Chromium
    BROWSER_PATH = os.environ.get("BROWSER_PATH", "")

    # 匿名身份 Cookie
    USER_COOKIE_NAME = "flavalon_uid"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
