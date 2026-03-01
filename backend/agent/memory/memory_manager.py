import json
import os
import re
import sqlite3
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z0-9']+", text.lower())
    return [w for w in words if len(w) > 2]


class MemoryManager:
    """Local long-term memory for coaching sessions.

    Strategy:
    - Keep runtime conversation small and fast (in-memory short window)
    - Persist long-term context locally in SQLite
    - Retrieve only relevant memories on demand via tool calls
    """

    def __init__(self, db_path: str | None = None):
        base_dir = Path(__file__).resolve().parent.parent
        default_db = base_dir / "data" / "memory.db"
        self._db_path = str(db_path or default_db)
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    session_id TEXT,
                    role TEXT NOT NULL,
                    text TEXT NOT NULL,
                    tags TEXT,
                    metadata TEXT
                );

                CREATE TABLE IF NOT EXISTS profile_summary (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    updated_at REAL NOT NULL,
                    summary TEXT NOT NULL
                );
                """
            )

    def add_memory(
        self,
        text: str,
        role: str = "user",
        session_id: str | None = None,
        tags: List[str] | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        text = text.strip()
        if not text:
            return
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO memory_entries (created_at, session_id, role, text, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    session_id,
                    role,
                    text,
                    json.dumps(tags or []),
                    json.dumps(metadata or {}),
                ),
            )

    def save_session_summary(self, session_data: Dict[str, Any], session_id: str) -> None:
        for entry in session_data.get("transcript", []):
            if entry.get("speaker") not in {"user", "agent"}:
                continue
            self.add_memory(
                text=entry.get("text", ""),
                role=entry.get("speaker", "user"),
                session_id=session_id,
                tags=["transcript"],
            )

        strengths = session_data.get("strengths", [])
        improvements = session_data.get("improvements", [])
        if strengths or improvements:
            summary = {
                "strengths": strengths,
                "improvements": improvements,
                "last_score": session_data.get("overall_score", 0),
            }
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO memory_entries (created_at, session_id, role, text, tags, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        time.time(),
                        session_id,
                        "system",
                        "Session coaching summary",
                        json.dumps(["session_summary", "coach_feedback"]),
                        json.dumps(summary),
                    ),
                )

            profile_text = self._build_profile_summary(strengths, improvements)
            self._upsert_profile_summary(profile_text)

    def _build_profile_summary(self, strengths: List[str], improvements: List[str]) -> str:
        strengths_text = "; ".join(strengths[:3]) if strengths else "No stable strengths yet"
        improvements_text = "; ".join(improvements[:3]) if improvements else "No critical improvement areas yet"
        return (
            f"Communication profile: strengths={strengths_text}. "
            f"Focus areas={improvements_text}."
        )

    def _upsert_profile_summary(self, summary: str) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO profile_summary (id, updated_at, summary)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET updated_at=excluded.updated_at, summary=excluded.summary
                """,
                (time.time(), summary),
            )

    def get_profile_summary(self) -> str:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT summary FROM profile_summary WHERE id = 1"
            ).fetchone()
            return row[0] if row else "No profile summary yet."

    def search_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        query_tokens = Counter(_tokenize(query))
        if not query_tokens:
            return []

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, created_at, session_id, role, text, tags, metadata
                FROM memory_entries
                ORDER BY created_at DESC
                LIMIT 800
                """
            ).fetchall()

        scored: List[tuple[float, Dict[str, Any]]] = []
        for row in rows:
            text = row["text"] or ""
            doc_tokens = Counter(_tokenize(text))
            if not doc_tokens:
                continue

            overlap = sum(min(doc_tokens[t], query_tokens[t]) for t in query_tokens)
            if overlap <= 0:
                continue

            recency_bonus = min(0.5, max(0.0, (time.time() - row["created_at"]) / 86400.0))
            score = float(overlap) - recency_bonus

            scored.append(
                (
                    score,
                    {
                        "id": row["id"],
                        "created_at": row["created_at"],
                        "session_id": row["session_id"],
                        "role": row["role"],
                        "text": text,
                        "tags": json.loads(row["tags"] or "[]"),
                        "metadata": json.loads(row["metadata"] or "{}"),
                    },
                )
            )

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[: max(1, min(limit, 10))]]
