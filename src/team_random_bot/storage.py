from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Participant:
    chat_id: str
    user_id: str
    user_name: str
    position: str = ""
    department: str = ""
    active: bool = True


@dataclass(frozen=True)
class WeeklyPairing:
    chat_id: str
    week_key: str
    first_user_id: str
    first_user_name: str
    second_user_id: str | None = None
    second_user_name: str | None = None


@dataclass(frozen=True)
class Reaction:
    chat_id: str
    actor_user_id: str
    actor_name: str
    target_user_id: str
    reaction: str
    reaction_date: date


class SQLiteStorage:
    """SQLite repository for random-coffee participants, pairings and reactions."""

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
                CREATE TABLE IF NOT EXISTS participants (
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    position TEXT NOT NULL DEFAULT '',
                    department TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (chat_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS weekly_pairings (
                    chat_id TEXT NOT NULL,
                    week_key TEXT NOT NULL,
                    pair_index INTEGER NOT NULL,
                    first_user_id TEXT NOT NULL,
                    second_user_id TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (chat_id, week_key, pair_index)
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

    def upsert_participant(
        self,
        *,
        chat_id: str,
        user_id: str,
        user_name: str,
        position: str = "",
        department: str = "",
        active: bool = True,
    ) -> None:
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO participants (
                    chat_id, user_id, user_name, position, department, active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    user_name = excluded.user_name,
                    position = CASE WHEN excluded.position != '' THEN excluded.position ELSE participants.position END,
                    department = CASE WHEN excluded.department != '' THEN excluded.department ELSE participants.department END,
                    active = excluded.active,
                    updated_at = excluded.updated_at
                """,
                (chat_id, user_id, user_name, position, department, int(active), now, now),
            )

    def set_participation(self, *, chat_id: str, user_id: str, active: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE participants
                SET active = ?, updated_at = ?
                WHERE chat_id = ? AND user_id = ?
                """,
                (int(active), self._now(), chat_id, user_id),
            )

    def list_active_participants(self, *, chat_id: str) -> list[Participant]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT chat_id, user_id, user_name, position, department, active
                FROM participants
                WHERE chat_id = ? AND active = 1
                ORDER BY user_name
                """,
                (chat_id,),
            ).fetchall()
        return [self._participant_from_row(row) for row in rows]

    def get_participant(self, *, chat_id: str, user_id: str) -> Participant | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT chat_id, user_id, user_name, position, department, active
                FROM participants
                WHERE chat_id = ? AND user_id = ?
                """,
                (chat_id, user_id),
            ).fetchone()
        return self._participant_from_row(row) if row else None

    @staticmethod
    def _participant_from_row(row: sqlite3.Row) -> Participant:
        return Participant(
            chat_id=row["chat_id"],
            user_id=row["user_id"],
            user_name=row["user_name"],
            position=row["position"],
            department=row["department"],
            active=bool(row["active"]),
        )

    def replace_weekly_pairings(
        self,
        *,
        chat_id: str,
        week_key: str,
        pairs: list[tuple[str, str]],
        bench_user_id: str | None = None,
    ) -> None:
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM weekly_pairings WHERE chat_id = ? AND week_key = ?",
                (chat_id, week_key),
            )
            for index, (first_user_id, second_user_id) in enumerate(pairs, start=1):
                connection.execute(
                    """
                    INSERT INTO weekly_pairings (
                        chat_id, week_key, pair_index, first_user_id, second_user_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (chat_id, week_key, index, first_user_id, second_user_id, now),
                )
            if bench_user_id:
                connection.execute(
                    """
                    INSERT INTO weekly_pairings (
                        chat_id, week_key, pair_index, first_user_id, second_user_id, created_at
                    ) VALUES (?, ?, ?, ?, NULL, ?)
                    """,
                    (chat_id, week_key, len(pairs) + 1, bench_user_id, now),
                )

    def list_weekly_pairings(self, *, chat_id: str, week_key: str) -> list[WeeklyPairing]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    wp.chat_id,
                    wp.week_key,
                    wp.first_user_id,
                    first_participant.user_name AS first_user_name,
                    wp.second_user_id,
                    second_participant.user_name AS second_user_name
                FROM weekly_pairings wp
                JOIN participants first_participant
                    ON first_participant.chat_id = wp.chat_id
                    AND first_participant.user_id = wp.first_user_id
                LEFT JOIN participants second_participant
                    ON second_participant.chat_id = wp.chat_id
                    AND second_participant.user_id = wp.second_user_id
                WHERE wp.chat_id = ? AND wp.week_key = ?
                ORDER BY wp.pair_index
                """,
                (chat_id, week_key),
            ).fetchall()
        return [
            WeeklyPairing(
                chat_id=row["chat_id"],
                week_key=row["week_key"],
                first_user_id=row["first_user_id"],
                first_user_name=row["first_user_name"],
                second_user_id=row["second_user_id"],
                second_user_name=row["second_user_name"],
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
