"""SQLite 访问层。"""

import sqlite3
from pathlib import Path

import click
from flask import current_app, g


def get_db() -> sqlite3.Connection:
    """获取当前请求的数据库连接。"""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def connect(database: str) -> sqlite3.Connection:
    path = Path(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def close_db(_exception=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """建表并确保存在一个管理员账号。"""
    from datetime import datetime

    from .auth import hash_password

    db = get_db()
    schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    db.executescript(schema)

    username = current_app.config["ADMIN_USERNAME"]
    existing = db.execute("SELECT 1 FROM admins WHERE username = ?", (username,)).fetchone()
    if existing is None:
        db.execute(
            "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
            (
                username,
                hash_password(current_app.config["ADMIN_PASSWORD"]),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
    db.commit()


@click.command("init-db")
def init_db_command() -> None:
    """初始化数据库（flask init-db）。"""
    init_db()
    click.echo("数据库初始化完成。")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    # 启动时自动建表，避免部署时忘记执行 init-db。
    with app.app_context():
        init_db()
