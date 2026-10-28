"""基于 SQLite 的持久化会话 Memory。"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Literal, TypedDict


class MemoryMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class ConversationSummary(TypedDict):
    conversation_id: str
    title: str
    message_count: int
    updated_at: str


class MemoryStore:
    """每次操作使用独立连接，适合 FastAPI 的并发请求。"""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id)
                        REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
                    ON messages(conversation_id, id);
                """
            )

    def get_recent_messages(
        self, conversation_id: str, limit: int
    ) -> list[MemoryMessage]:
        if limit == 0:
            return []

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, limit),
            ).fetchall()

        return [
            MemoryMessage(role=row["role"], content=row["content"])
            for row in reversed(rows)
        ]

    def get_all_messages(self, conversation_id: str) -> list[MemoryMessage]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,),
            ).fetchall()

        return [
            MemoryMessage(role=row["role"], content=row["content"])
            for row in rows
        ]

    def append_exchange(
        self, conversation_id: str, user_message: str, assistant_message: str
    ) -> None:
        """在一个事务中保存完整的一问一答。"""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (id)
                VALUES (?)
                ON CONFLICT(id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
                """,
                (conversation_id,),
            )
            connection.executemany(
                """
                INSERT INTO messages (conversation_id, role, content)
                VALUES (?, ?, ?)
                """,
                (
                    (conversation_id, "user", user_message),
                    (conversation_id, "assistant", assistant_message),
                ),
            )
            connection.execute(
                """
                UPDATE conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (conversation_id,),
            )

    def list_conversations(self, limit: int = 50) -> list[ConversationSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    c.id AS conversation_id,
                    COALESCE(
                        (SELECT content FROM messages
                         WHERE conversation_id = c.id AND role = 'user'
                         ORDER BY id ASC LIMIT 1),
                        '新会话'
                    ) AS title,
                    COUNT(m.id) AS message_count,
                    c.updated_at
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            ConversationSummary(
                conversation_id=row["conversation_id"],
                title=row["title"][:60],
                message_count=row["message_count"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE id = ?", (conversation_id,)
            )
        return cursor.rowcount > 0
