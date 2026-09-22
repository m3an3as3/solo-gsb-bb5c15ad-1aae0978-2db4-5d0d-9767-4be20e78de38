"""SQLite 持久化：审查记录与例外包。"""

import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.environ.get("DB_PATH") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "review.db"
)


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at   TEXT NOT NULL,
                policy       TEXT NOT NULL,
                project_name TEXT NOT NULL,
                manifest     TEXT NOT NULL,
                result       TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS exceptions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id  INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
                package    TEXT NOT NULL,
                note       TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE (review_id, package)
            );
            """
        )


def _now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def create_review(policy, project_name, manifest, result):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO reviews (created_at, policy, project_name, manifest, result)"
            " VALUES (?, ?, ?, ?, ?)",
            (_now(), policy, project_name, json.dumps(manifest, ensure_ascii=False),
             json.dumps(result, ensure_ascii=False)),
        )
        return cur.lastrowid


def _row_to_review(row, exceptions):
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "policy": row["policy"],
        "project_name": row["project_name"],
        "manifest": json.loads(row["manifest"]),
        "result": json.loads(row["result"]),
        "exceptions": exceptions,
    }


def get_review(review_id):
    with _conn() as c:
        row = c.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        if row is None:
            return None
        exceptions = [
            {"package": r["package"], "note": r["note"], "created_at": r["created_at"]}
            for r in c.execute(
                "SELECT * FROM exceptions WHERE review_id = ? ORDER BY package", (review_id,)
            )
        ]
    return _row_to_review(row, exceptions)


def list_reviews(limit=20):
    with _conn() as c:
        rows = c.execute(
            "SELECT id, created_at, policy, project_name, result"
            " FROM reviews ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    items = []
    for r in rows:
        result = json.loads(r["result"])
        items.append({
            "id": r["id"],
            "created_at": r["created_at"],
            "policy": r["policy"],
            "policy_label": result.get("policy_label", r["policy"]),
            "project_name": r["project_name"],
            "summary": result.get("summary", {}),
        })
    return items


def update_result(review_id, result):
    with _conn() as c:
        c.execute(
            "UPDATE reviews SET result = ? WHERE id = ?",
            (json.dumps(result, ensure_ascii=False), review_id),
        )


def add_exception(review_id, package, note):
    with _conn() as c:
        c.execute(
            "INSERT INTO exceptions (review_id, package, note, created_at) VALUES (?, ?, ?, ?)"
            " ON CONFLICT (review_id, package) DO UPDATE SET note = excluded.note",
            (review_id, package, note, _now()),
        )


def remove_exception(review_id, package):
    with _conn() as c:
        c.execute(
            "DELETE FROM exceptions WHERE review_id = ? AND package = ?",
            (review_id, package),
        )
