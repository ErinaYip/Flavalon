"""面向普通用户的 JSON API。"""

from flask import Blueprint, jsonify, request

from .. import store
from ..auth import get_current_user, require_user

bp = Blueprint("api", __name__, url_prefix="/api")


def _user_id() -> int:
    return get_current_user()["id"]


@bp.get("/me")
@require_user
def me():
    return jsonify({"ok": True})


# --------------------------------------------------------------------------- #
# 待办
# --------------------------------------------------------------------------- #
@bp.get("/todos")
@require_user
def get_todos():
    return jsonify(store.list_todos(_user_id()))


@bp.post("/todos")
@require_user
def add_todo():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    if len(text) > 500:
        return jsonify({"error": "text too long"}), 400
    return jsonify(store.create_todo(_user_id(), text)), 201


@bp.post("/todos/<int:todo_id>/toggle")
@require_user
def toggle_todo(todo_id: int):
    todo = store.toggle_todo(_user_id(), todo_id)
    if todo is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(todo)


@bp.delete("/todos/<int:todo_id>")
@require_user
def delete_todo(todo_id: int):
    if not store.delete_todo(_user_id(), todo_id):
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


# --------------------------------------------------------------------------- #
# 小记
# --------------------------------------------------------------------------- #
@bp.get("/notes/<day>")
@require_user
def get_note(day: str):
    return jsonify({"date": day, "content": store.get_note(_user_id(), day)})


@bp.put("/notes/<day>")
@require_user
def put_note(day: str):
    data = request.get_json(silent=True) or {}
    content = str(data.get("content", ""))
    if len(content) > 20000:
        return jsonify({"error": "content too long"}), 400
    store.save_note(_user_id(), day, content)
    return jsonify({"ok": True})


@bp.get("/notes")
@require_user
def note_dates():
    return jsonify(store.list_note_dates(_user_id()))


# --------------------------------------------------------------------------- #
# 导出 / 导入
# --------------------------------------------------------------------------- #
@bp.get("/export")
@require_user
def export_data():
    return jsonify(store.export_user_data(_user_id()))


@bp.post("/import")
@require_user
def import_data():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "invalid payload"}), 400
    store.import_user_data(_user_id(), data)
    return jsonify({"ok": True})
