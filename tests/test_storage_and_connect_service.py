from __future__ import annotations

import random
from datetime import date

from team_random_bot.connect_service import MessageContext, handle_stateful_message
from team_random_bot.storage import SQLiteStorage


def context(user_id: str = "u1", user_name: str = "Анна") -> MessageContext:
    return MessageContext(chat_id="chat-1", user_id=user_id, user_name=user_name, today=date(2026, 5, 31))


def test_connect_command_persists_daily_intent(tmp_path) -> None:
    storage = SQLiteStorage(tmp_path / "bot.sqlite3")

    response = handle_stateful_message("/connect после 15:00", storage=storage, context=context())
    today = handle_stateful_message("/today", storage=storage, context=context())

    assert "записал" in (response or "")
    assert "Анна — после 15:00" in (today or "")


def test_plus_shortcut_and_skip_update_today_list(tmp_path) -> None:
    storage = SQLiteStorage(tmp_path / "bot.sqlite3")

    handle_stateful_message("+", storage=storage, context=context())
    assert "Анна" in (handle_stateful_message("/today", storage=storage, context=context()) or "")

    handle_stateful_message("/skip", storage=storage, context=context())
    assert "никто" in (handle_stateful_message("/today", storage=storage, context=context()) or "")


def test_pairs_use_saved_daily_intents(tmp_path) -> None:
    storage = SQLiteStorage(tmp_path / "bot.sqlite3")
    handle_stateful_message("+", storage=storage, context=context("u1", "Анна"))
    handle_stateful_message("+", storage=storage, context=context("u2", "Борис"))

    response = handle_stateful_message(
        "/pairs",
        storage=storage,
        context=context("u3", "Вера"),
        rng=random.Random(1),
    )

    assert "Случайные команды" in (response or "")
    assert "Анна" in (response or "")
    assert "Борис" in (response or "")


def test_reactions_are_saved_for_today(tmp_path) -> None:
    storage = SQLiteStorage(tmp_path / "bot.sqlite3")

    response = handle_stateful_message("/react @boris 👍", storage=storage, context=context())
    reactions = handle_stateful_message("/reactions", storage=storage, context=context())

    assert "👍" in (response or "")
    assert "boris: 👍 от Анна" in (reactions or "")
