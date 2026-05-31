from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class ConnectionIntent:
    chat_id: str
    user_id: str
    user_name: str
    intent_date: date
    status: str
    comment: str = ""


@dataclass(frozen=True)
class Reaction:
    chat_id: str
    actor_user_id: str
    actor_name: str
    target_user_id: str
    reaction: str
    reaction_date: date


class SQLiteStorage:
    """SQLite repository for daily connection intents and reactions."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS connection_intents (
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    intent_date TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('active', 'cancelled')),
                    comment TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (chat_id, user_id, intent_date)
                );

                CREATE TABLE IF NOT EXISTS connection_reactions (
                    chat_id TEXT NOT NULL,
                    actor_user_id TEXT NOT NULL,
                    actor_name TEXT NOT NULL,
                    target_user_id TEXT NOT NULL,
                    reaction TEXT NOT NULL,
                    reaction_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (chat_id, actor_user_id, target_user_id, reaction_date)
                );
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def save_intent(
        self,
        *,
        chat_id: str,
        user_id: str,
        user_name: str,
        intent_date: date,
        comment: str = "",
        status: str = "active",
    ) -> None:
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO connection_intents (
                    chat_id, user_id, user_name, intent_date, status, comment, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, user_id, intent_date) DO UPDATE SET
                    user_name = excluded.user_name,
                    status = excluded.status,
                    comment = excluded.comment,
                    updated_at = excluded.updated_at
                """,
                (chat_id, user_id, user_name, intent_date.isoformat(), status, comment, now, now),
            )

    def cancel_intent(self, *, chat_id: str, user_id: str, intent_date: date) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE connection_intents
                SET status = 'cancelled', updated_at = ?
                WHERE chat_id = ? AND user_id = ? AND intent_date = ?
                """,
                (self._now(), chat_id, user_id, intent_date.isoformat()),
            )

    def list_active_intents(self, *, chat_id: str, intent_date: date) -> list[ConnectionIntent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT chat_id, user_id, user_name, intent_date, status, comment
                FROM connection_intents
                WHERE chat_id = ? AND intent_date = ? AND status = 'active'
                ORDER BY updated_at, user_name
                """,
                (chat_id, intent_date.isoformat()),
            ).fetchall()
        return [
            ConnectionIntent(
                chat_id=row["chat_id"],
                user_id=row["user_id"],
                user_name=row["user_name"],
                intent_date=date.fromisoformat(row["intent_date"]),
                status=row["status"],
                comment=row["comment"],
            )
            for row in rows
        ]

    def save_reaction(
        self,
        *,
        chat_id: str,
        actor_user_id: str,
        actor_name: str,
        target_user_id: str,
        reaction: str,
        reaction_date: date,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO connection_reactions (
                    chat_id, actor_user_id, actor_name, target_user_id, reaction, reaction_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, actor_user_id, target_user_id, reaction_date) DO UPDATE SET
                    actor_name = excluded.actor_name,
                    reaction = excluded.reaction,
                    created_at = excluded.created_at
                """,
                (
                    chat_id,
                    actor_user_id,
                    actor_name,
                    target_user_id,
                    reaction,
                    reaction_date.isoformat(),
                    self._now(),
                ),
            )

    def list_reactions(self, *, chat_id: str, reaction_date: date) -> list[Reaction]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT chat_id, actor_user_id, actor_name, target_user_id, reaction, reaction_date
                FROM connection_reactions
                WHERE chat_id = ? AND reaction_date = ?
                ORDER BY target_user_id, actor_name
                """,
                (chat_id, reaction_date.isoformat()),
            ).fetchall()
        return [
            Reaction(
                chat_id=row["chat_id"],
                actor_user_id=row["actor_user_id"],
                actor_name=row["actor_name"],
                target_user_id=row["target_user_id"],
                reaction=row["reaction"],
                reaction_date=date.fromisoformat(row["reaction_date"]),
            )
            for row in rows
        ]
