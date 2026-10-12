"""数据访问层：待办、小记、日程。"""

from datetime import date, datetime

from .db import get_db


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# 待办
# --------------------------------------------------------------------------- #
def list_todos(user_id: int) -> list[dict]:
    rows = get_db().execute(
        "SELECT id, text, completed, created_at, completed_at "
        "FROM todos WHERE user_id = ? ORDER BY completed ASC, id DESC",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def create_todo(user_id: int, text: str) -> dict:
    db = get_db()
    cur = db.execute(
        "INSERT INTO todos (user_id, text, completed, created_at) VALUES (?, ?, 0, ?)",
        (user_id, text, _now()),
    )
    db.commit()
    row = db.execute("SELECT * FROM todos WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def toggle_todo(user_id: int, todo_id: int) -> dict | None:
    db = get_db()
    row = db.execute(
        "SELECT * FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id)
    ).fetchone()
    if row is None:
        return None
    completed = 0 if row["completed"] else 1
    completed_at = _now() if completed else None
    db.execute(
        "UPDATE todos SET completed = ?, completed_at = ? WHERE id = ?",
        (completed, completed_at, todo_id),
    )
    db.commit()
    return dict(db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone())


def delete_todo(user_id: int, todo_id: int) -> bool:
    db = get_db()
    cur = db.execute("DELETE FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id))
    db.commit()
    return cur.rowcount > 0


# --------------------------------------------------------------------------- #
# 小记
# --------------------------------------------------------------------------- #
def get_note(user_id: int, day: str) -> str:
    row = get_db().execute(
        "SELECT content FROM notes WHERE user_id = ? AND date = ?", (user_id, day)
    ).fetchone()
    return row["content"] if row else ""


def list_note_dates(user_id: int) -> list[str]:
    rows = get_db().execute(
        "SELECT date FROM notes WHERE user_id = ? AND content != ''", (user_id,)
    ).fetchall()
    return [r["date"] for r in rows]


def save_note(user_id: int, day: str, content: str) -> None:
    db = get_db()
    if content.strip() == "":
        db.execute("DELETE FROM notes WHERE user_id = ? AND date = ?", (user_id, day))
    else:
        db.execute(
            "INSERT INTO notes (user_id, date, content, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, date) DO UPDATE SET content = excluded.content, "
            "updated_at = excluded.updated_at",
            (user_id, day, content, _now()),
        )
    db.commit()


# --------------------------------------------------------------------------- #
# 导出 / 导入
# --------------------------------------------------------------------------- #
def export_user_data(user_id: int) -> dict:
    db = get_db()
    todos = [
        dict(r)
        for r in db.execute(
            "SELECT text, completed, created_at, completed_at FROM todos "
            "WHERE user_id = ? ORDER BY id",
            (user_id,),
        ).fetchall()
    ]
    notes = {
        r["date"]: r["content"]
        for r in db.execute(
            "SELECT date, content FROM notes WHERE user_id = ?", (user_id,)
        ).fetchall()
    }
    return {
        "version": 1,
        "exported_at": _now(),
        "todos": todos,
        "notes": notes,
    }


def import_user_data(user_id: int, data: dict) -> None:
    db = get_db()
    db.execute("DELETE FROM todos WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM notes WHERE user_id = ?", (user_id,))

    for todo in data.get("todos", []):
        db.execute(
            "INSERT INTO todos (user_id, text, completed, created_at, completed_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                str(todo.get("text", "")),
                1 if todo.get("completed") else 0,
                str(todo.get("createdAt") or todo.get("created_at") or _now()),
                todo.get("completedAt") or todo.get("completed_at"),
            ),
        )

    for day, content in (data.get("notes") or {}).items():
        if content:
            db.execute(
                "INSERT INTO notes (user_id, date, content, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, str(day), str(content), _now()),
            )

    db.commit()
