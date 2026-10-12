"""Flavalon —— a place for peace.

一个自托管的日程 / 待办 / 日记应用。
"""

from flask import Flask

from . import db
from .config import Config


def create_app(config_object=Config) -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_object)

    db.init_app(app)

    from . import bot
    from .routes import admin, api, pages

    app.register_blueprint(pages.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(admin.bp)

    # 后台审核机器人：轮询 pending 日程并代为复核发布。
    bot.init_app(app)

    return app
