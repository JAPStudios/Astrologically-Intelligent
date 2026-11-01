"""SQLite-backed conversations, durable memory, and agent work items."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, path: str = "astrologically_intelligent.sqlite3"):
        self.path = str(path)
        self._lock = threading.RLock()
        Path(self.path).parent.mkdir(parents=True, exist_ok=True) if self.path != ":memory:" else None
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("PRAGMA journal_mode=WAL")
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._db:
            self._db.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY, session_id TEXT NOT NULL, role TEXT NOT NULL,
                content TEXT NOT NULL, created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS messages_session_time ON messages(session_id, created_at);
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY, namespace TEXT NOT NULL, key TEXT NOT NULL,
                value TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL,
                UNIQUE(namespace, key)
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open', assignee TEXT, created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS tasks_status ON tasks(status, created_at);
            """)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?)",
                (uuid.uuid4().hex, session_id, role, content, time.time()),
            )

    def history(self, session_id: str, limit: int = 40) -> list[dict[str, str]]:
        limit = max(1, min(int(limit), 200))
        with self._lock:
            rows = self._db.execute(
                "SELECT role, content FROM messages WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def remember(self, namespace: str, key: str, value: Any) -> None:
        now = time.time()
        encoded = json.dumps(value, ensure_ascii=False)
        with self._lock, self._db:
            self._db.execute("""
                INSERT INTO memories(id, namespace, key, value, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(namespace, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """, (uuid.uuid4().hex, namespace, key, encoded, now, now))

    def recall(self, namespace: str, key: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            if key is None:
                rows = self._db.execute(
                    "SELECT key, value, updated_at FROM memories WHERE namespace=? ORDER BY updated_at DESC",
                    (namespace,),
                ).fetchall()
            else:
                rows = self._db.execute(
                    "SELECT key, value, updated_at FROM memories WHERE namespace=? AND key=?",
                    (namespace, key),
                ).fetchall()
        return [{"key": r["key"], "value": json.loads(r["value"]), "updated_at": r["updated_at"]} for r in rows]

    def create_task(self, title: str, description: str = "", assignee: str | None = None) -> dict[str, Any]:
        now, task_id = time.time(), uuid.uuid4().hex
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO tasks(id,title,description,status,assignee,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (task_id, title, description, "open", assignee, now, now),
            )
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(row) if row else None

    def list_tasks(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM tasks WHERE status=? ORDER BY created_at" if status else
                "SELECT * FROM tasks ORDER BY created_at",
                (status,) if status else (),
            ).fetchall()
        return [dict(r) for r in rows]

    def update_task(self, task_id: str, status: str, assignee: str | None = None) -> dict[str, Any] | None:
        if status not in {"open", "in_progress", "blocked", "done", "cancelled"}:
            raise ValueError("Unsupported task status")
        with self._lock, self._db:
            self._db.execute(
                "UPDATE tasks SET status=?, assignee=COALESCE(?, assignee), updated_at=? WHERE id=?",
                (status, assignee, time.time(), task_id),
            )
        return self.get_task(task_id)

    def close(self) -> None:
        with self._lock:
            self._db.close()
