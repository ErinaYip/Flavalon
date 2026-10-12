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
# 日程（每日事项投稿）
# --------------------------------------------------------------------------- #
def create_agenda(user_id: int, title: str, content: str) -> dict:
    db = get_db()
    cur = db.execute(
        "INSERT INTO agenda (user_id, title, content, status, created_at) "
        "VALUES (?, ?, ?, 'pending', ?)",
        (user_id, title, content, _now()),
    )
    db.commit()
    return dict(db.execute("SELECT * FROM agenda WHERE id = ?", (cur.lastrowid,)).fetchone())


def list_agenda_mine(user_id: int) -> list[dict]:
    rows = get_db().execute(
        "SELECT id, title, content, status, created_at, reviewed_at, review_note "
        "FROM agenda WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_agenda_published() -> list[dict]:
    rows = get_db().execute(
        "SELECT id, title, content, reviewed_at FROM agenda "
        "WHERE status = 'approved' ORDER BY id DESC",
    ).fetchall()
    return [dict(r) for r in rows]


def list_agenda_pending() -> list[dict]:
    rows = get_db().execute(
        "SELECT a.id, a.title, a.content, a.created_at, u.token AS user_token "
        "FROM agenda a JOIN users u ON u.id = a.user_id "
        "WHERE a.status = 'pending' ORDER BY a.id ASC",
    ).fetchall()
    return [dict(r) for r in rows]


def get_agenda(agenda_id: int) -> dict | None:
    row = get_db().execute("SELECT * FROM agenda WHERE id = ?", (agenda_id,)).fetchone()
    return dict(row) if row else None


def review_agenda(agenda_id: int, approved: bool, note: str = "") -> None:
    db = get_db()
    db.execute(
        "UPDATE agenda SET status = ?, reviewed_at = ?, review_note = ? WHERE id = ?",
        ("approved" if approved else "rejected", _now(), note, agenda_id),
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
    agenda = [
        dict(r)
        for r in db.execute(
            "SELECT title, content, status, created_at FROM agenda WHERE user_id = ? ORDER BY id",
            (user_id,),
        ).fetchall()
    ]
    return {
        "version": 2,
        "exported_at": _now(),
        "todos": todos,
        "notes": notes,
        "agenda": agenda,
    }


def import_user_data(user_id: int, data: dict) -> None:
    db = get_db()
    db.execute("DELETE FROM todos WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM notes WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM agenda WHERE user_id = ?", (user_id,))

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

    for item in data.get("agenda", []):
        db.execute(
            "INSERT INTO agenda (user_id, title, content, status, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                str(item.get("title", "")),
                str(item.get("content", "")),
                "pending",
                str(item.get("createdAt") or item.get("created_at") or _now()),
            ),
        )
    db.commit()


# --------------------------------------------------------------------------- #
# 回连收集
# --------------------------------------------------------------------------- #
def record_webhook(token: str, payload: str) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO webhook_hits (token, payload, created_at) VALUES (?, ?, ?)",
        (token, payload, _now()),
    )
    db.commit()


def list_webhook_hits(token: str) -> list[dict]:
    rows = get_db().execute(
        "SELECT id, payload, created_at FROM webhook_hits WHERE token = ? ORDER BY id DESC",
        (token,),
    ).fetchall()
    return [dict(r) for r in rows]
