"""管理员后台：登录、审核队列、查看系统密钥。"""

from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .. import store
from ..auth import is_admin, require_admin, verify_password
from ..db import get_db

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/login")
def login_page():
    if is_admin():
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/login.html", error=None)


@bp.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    row = get_db().execute(
        "SELECT * FROM admins WHERE username = ?", (username,)
    ).fetchone()
    if row is None or not verify_password(row["password_hash"], password):
        return render_template("admin/login.html", error="用户名或密码错误"), 401

    session.clear()
    session["admin_id"] = row["id"]
    session["admin_username"] = row["username"]

    next_url = request.args.get("next") or request.form.get("next")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect(url_for("admin.dashboard"))


@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login_page"))


@bp.get("/")
@require_admin
def dashboard():
    return render_template(
        "admin/dashboard.html",
        pending=store.list_agenda_pending(),
        username=session.get("admin_username"),
    )


@bp.get("/queue/<int:agenda_id>")
@require_admin
def queue_detail(agenda_id: int):
    item = store.get_agenda(agenda_id)
    if item is None:
        return render_template("admin/not_found.html"), 404
    return render_template("admin/review.html", item=item)


@bp.post("/queue/<int:agenda_id>/review")
@require_admin
def review(agenda_id: int):
    item = store.get_agenda(agenda_id)
    if item is None:
        return jsonify({"error": "not found"}), 404

    action = request.form.get("action", "")
    approved = action == "approve"
    store.review_agenda(agenda_id, approved, note=request.form.get("note", ""))
    return redirect(url_for("admin.dashboard"))


@bp.get("/flag")
@require_admin
def site_key():
    """系统密钥（动态 flag），仅供管理员查看。"""
    flag_path = Path(current_app.config["FLAG_PATH"])
    try:
        value = flag_path.read_text(encoding="utf-8").strip()
    except OSError:
        value = "flag{missing_flag_file}"
    return jsonify({"key": value})
