"""认证与身份工具。

- 普通用户：匿名，靠一个 HttpOnly Cookie 持有随机 token 标识身份；
- 管理员：用户名 + 口令（scrypt 哈希），登录后写入 Flask session。
"""

import secrets
from datetime import datetime
from functools import wraps

from flask import current_app, g, jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="scrypt")


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


# --------------------------------------------------------------------------- #
# 普通用户（匿名）
# --------------------------------------------------------------------------- #
def get_current_user(create: bool = False) -> dict | None:
    """按 Cookie 里的 token 找到用户；create=True 时不存在则自动创建。"""
    if "user" in g:
        return g.user

    db = get_db()
    token = request.cookies.get(current_app.config["USER_COOKIE_NAME"])
    user = None
    if token:
        user = db.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()

    if user is None and create:
        token = secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO users (token, created_at) VALUES (?, ?)",
            (token, datetime.now().isoformat(timespec="seconds")),
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
        g.new_user_token = token

    g.user = user
    return user


def ensure_user_cookie(response, user) -> None:
    """把新生成的用户 token 写回 Cookie。"""
    token = getattr(g, "new_user_token", None)
    if token:
        response.set_cookie(
            current_app.config["USER_COOKIE_NAME"],
            token,
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            samesite="Lax",
        )


def require_user(view):
    """视图装饰器：保证存在匿名用户，并把新 token 写入响应。"""

    @wraps(view)
    def wrapper(*args, **kwargs):
        get_current_user(create=True)
        result = view(*args, **kwargs)
        if isinstance(result, tuple):
            response = result[0]
            ensure_user_cookie(response, g.user)
            return result
        if hasattr(result, "set_cookie"):
            ensure_user_cookie(result, g.user)
        return result

    return wrapper


# --------------------------------------------------------------------------- #
# 管理员
# --------------------------------------------------------------------------- #
def is_admin() -> bool:
    return bool(session.get("admin_id"))


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not is_admin():
            if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapper
