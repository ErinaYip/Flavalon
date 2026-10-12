"""日程审核机器人。

所有投稿的每日日程都会先进入 pending 队列，由这个后台机器人代为「打开后台审核页
复核」后再发布。机器人在真实的浏览器上下文里操作，因此它可以执行页面脚本、
并访问管理员才能看到的内容。

安全说明：本模块只负责「驱动浏览器」，对投稿内容的转义/渲染由模板决定。
在安全版本中，审核页以纯文本展示投稿，机器人不会执行任何投稿者提供的脚本。
"""

import logging
import threading
import time
from datetime import datetime

import requests

log = logging.getLogger("flavalon.bot")


class ReviewBot:
    """轮询 pending 日程并逐个审核。"""

    def __init__(self, app):
        self.app = app
        self._stop = threading.Event()
        self._thread = None
        self._http = requests.Session()

    # -- 生命周期 ---------------------------------------------------------- #
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="review-bot", daemon=True)
        self._thread.start()
        log.info("审核机器人已启动")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    # -- 主循环 ------------------------------------------------------------ #
    def _run(self):
        # 等 Flask 真正开始监听
        time.sleep(2)
        while not self._stop.is_set():
            try:
                self._review_pending()
            except Exception:  # pragma: no cover - 后台线程不应因单次错误退出
                log.exception("审核循环出现异常")
            self._stop.wait(3)

    def _review_pending(self):
        from . import store

        with self.app.app_context():
            pending = store.list_agenda_pending()

        for item in pending:
            if self._stop.is_set():
                return
            self._review_one(item)

    # -- 单条审核 ---------------------------------------------------------- #
    def _base_url(self) -> str:
        cfg = self.app.config
        if cfg.get("SELF_BASE_URL"):
            return cfg["SELF_BASE_URL"].rstrip("/")
        return "http://127.0.0.1:5000"

    def _admin_login(self) -> bool:
        cfg = self.app.config
        try:
            resp = self._http.post(
                f"{self._base_url()}/admin/login",
                data={
                    "username": cfg["ADMIN_USERNAME"],
                    "password": cfg["ADMIN_PASSWORD"],
                },
                allow_redirects=False,
                timeout=5,
            )
            return resp.status_code in (301, 302, 303, 200)
        except requests.RequestException:
            log.warning("机器人登录管理员失败，稍后重试")
            return False

    def _review_one(self, item: dict):
        from . import store

        cfg = self.app.config
        review_url = f"{self._base_url()}/admin/queue/{item['id']}"

        if not self._admin_login():
            return

        if cfg.get("BOT_ENABLED", True):
            visited = self._visit_in_browser(review_url)
            if not visited:
                # 没有可用的浏览器时，退化为纯 HTTP 访问，保证审核流程不阻塞。
                self._http.get(review_url, timeout=5)

        # 机器人看过之后即视为审核通过（这是本题设定的自动发布流程）。
        with self.app.app_context():
            store.review_agenda(item["id"], approved=True, note="reviewed by bot")
        log.info("日程 #%s 已审核通过", item["id"])

    def _visit_in_browser(self, url: str) -> bool:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            log.warning("未安装 playwright，使用纯 HTTP 审核")
            return False

        cfg = self.app.config
        try:
            with sync_playwright() as p:
                launch_kwargs = {
                    "headless": True,
                    "args": ["--no-sandbox", "--disable-dev-shm-usage"],
                }
                browser_path = cfg.get("BROWSER_PATH")
                if browser_path:
                    launch_kwargs["executable_path"] = browser_path
                browser = p.chromium.launch(**launch_kwargs)
                context = browser.new_context()
                # 把机器人（管理员）的会话 Cookie 注入浏览器
                for cookie in self._http.cookies:
                    context.add_cookies(
                        [
                            {
                                "name": cookie.name,
                                "value": cookie.value,
                                "domain": "127.0.0.1",
                                "path": "/",
                            }
                        ]
                    )
                page = context.new_page()
                page.goto(url, wait_until="networkidle", timeout=15000)
                page.wait_for_timeout(int(cfg.get("BOT_REVIEW_DELAY_MS", 1500)))
                browser.close()
            return True
        except Exception:
            log.exception("浏览器审核失败")
            return False


_bot: ReviewBot | None = None


def init_app(app):
    """在应用启动时拉起审核机器人（可在配置中关闭）。"""
    global _bot
    if not app.config.get("BOT_ENABLED", True):
        return
    # 避免 Flask debug 重载器启动两个机器人
    import os

    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    _bot = ReviewBot(app)
    _bot.start()
