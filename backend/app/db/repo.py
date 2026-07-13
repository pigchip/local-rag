"""CRUD helpers for sessions, messages, and KB descriptions."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from app.db.database import get_conn, write_lock


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


# --- Sessions ---------------------------------------------------------------

def create_session(
    title: str = "New chat",
    kb_name: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> dict:
    sid = _new_id()
    now = _now()
    with write_lock():
        conn = get_conn()
        conn.execute(
            "INSERT INTO sessions (id, title, kb_name, provider, model, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sid, title, kb_name, provider, model, now, now),
        )
        conn.commit()
    return get_session(sid)


def list_sessions() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT s.*, (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) AS message_count"
        " FROM sessions s ORDER BY s.updated_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def get_session(session_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        return None
    session = dict(row)
    session["messages"] = list_messages(session_id)
    return session


def update_session(session_id: str, **fields) -> dict | None:
    allowed = {"title", "kb_name", "provider", "model"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if updates:
        updates["updated_at"] = _now()
        cols = ", ".join(f"{k} = ?" for k in updates)
        with write_lock():
            conn = get_conn()
            conn.execute(
                f"UPDATE sessions SET {cols} WHERE id = ?",
                (*updates.values(), session_id),
            )
            conn.commit()
    return get_session(session_id)


def touch_session(session_id: str) -> None:
    with write_lock():
        conn = get_conn()
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?", (_now(), session_id)
        )
        conn.commit()


def delete_session(session_id: str) -> bool:
    with write_lock():
        conn = get_conn()
        cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        return cur.rowcount > 0


# --- Messages ---------------------------------------------------------------

def add_message(
    session_id: str,
    role: str,
    content: str,
    sources: list | None = None,
) -> dict:
    mid = _new_id()
    now = _now()
    sources_json = json.dumps(sources) if sources else None
    with write_lock():
        conn = get_conn()
        conn.execute(
            "INSERT INTO messages (id, session_id, role, content, sources_json, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (mid, session_id, role, content, sources_json, now),
        )
        conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        conn.commit()
    return {
        "id": mid,
        "session_id": session_id,
        "role": role,
        "content": content,
        "sources": sources or [],
        "created_at": now,
    }


def list_messages(session_id: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,)
    ).fetchall()
    out = []
    for r in rows:
        msg = dict(r)
        raw = msg.pop("sources_json", None)
        msg["sources"] = json.loads(raw) if raw else []
        out.append(msg)
    return out


# --- KB descriptions --------------------------------------------------------

def set_kb_description(kb_name: str, description: str, examples: list[str] | None = None) -> None:
    now = _now()
    examples_json = json.dumps(examples if examples is not None else [])
    with write_lock():
        conn = get_conn()
        if examples is None:
            conn.execute(
                "INSERT INTO kb_meta (kb_name, description, created_at, updated_at)"
                " VALUES (?, ?, ?, ?)"
                " ON CONFLICT(kb_name) DO UPDATE SET description = excluded.description,"
                " updated_at = excluded.updated_at",
                (kb_name, description, now, now),
            )
        else:
            conn.execute(
                "INSERT INTO kb_meta (kb_name, description, examples_json, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(kb_name) DO UPDATE SET description = excluded.description,"
                " examples_json = excluded.examples_json, updated_at = excluded.updated_at",
                (kb_name, description, examples_json, now, now),
            )
        conn.commit()


def get_kb_description(kb_name: str) -> str:
    conn = get_conn()
    row = conn.execute(
        "SELECT description FROM kb_meta WHERE kb_name = ?", (kb_name,)
    ).fetchone()
    return row["description"] if row else ""


def get_kb_examples(kb_name: str) -> list[str]:
    conn = get_conn()
    row = conn.execute(
        "SELECT examples_json FROM kb_meta WHERE kb_name = ?", (kb_name,)
    ).fetchone()
    if not row or not row["examples_json"]:
        return []
    try:
        return json.loads(row["examples_json"])
    except (ValueError, TypeError):
        return []


def all_kb_meta() -> dict[str, dict]:
    conn = get_conn()
    rows = conn.execute("SELECT kb_name, description, examples_json FROM kb_meta").fetchall()
    out: dict[str, dict] = {}
    for r in rows:
        try:
            examples = json.loads(r["examples_json"]) if r["examples_json"] else []
        except (ValueError, TypeError):
            examples = []
        out[r["kb_name"]] = {"description": r["description"], "examples": examples}
    return out


def all_kb_descriptions() -> dict[str, str]:
    conn = get_conn()
    rows = conn.execute("SELECT kb_name, description FROM kb_meta").fetchall()
    return {r["kb_name"]: r["description"] for r in rows}


def delete_kb_description(kb_name: str) -> None:
    with write_lock():
        conn = get_conn()
        conn.execute("DELETE FROM kb_meta WHERE kb_name = ?", (kb_name,))
        conn.commit()
