from __future__ import annotations

import re
import sqlite3
from pathlib import Path


class History:
    """Em memória por padrão; SQLite apenas quando --session é solicitado."""

    def __init__(self, path: Path | None = None, session: str = "temporary"):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", session):
            raise ValueError("Sessão: use 1 a 64 letras, números, _ ou -.")
        if path:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(str(path) if path else ":memory:")
        if path:
            path.chmod(0o600)
        self.session = session
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, "
            "session TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL)"
        )
        self.db.execute("CREATE INDEX IF NOT EXISTS ix_session ON messages(session,id)")
        self.db.commit()

    def load(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT role,content FROM (SELECT id,role,content FROM messages "
            "WHERE session=? ORDER BY id DESC LIMIT 40) ORDER BY id",
            (self.session,),
        ).fetchall()
        return [{"role": role, "content": content} for role, content in rows]

    def save_turn(self, user: str, assistant: str) -> None:
        with self.db:
            self.db.executemany(
                "INSERT INTO messages(session,role,content) VALUES (?,?,?)",
                [(self.session, "user", user), (self.session, "assistant", assistant)],
            )
            self.db.execute(
                "DELETE FROM messages WHERE session=? AND id NOT IN "
                "(SELECT id FROM messages WHERE session=? ORDER BY id DESC LIMIT 40)",
                (self.session, self.session),
            )

    def clear(self) -> None:
        with self.db:
            self.db.execute("DELETE FROM messages WHERE session=?", (self.session,))

    def close(self) -> None:
        self.db.close()
