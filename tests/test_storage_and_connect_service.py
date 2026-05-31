from __future__ import annotations

import random
from datetime import date

from team_random_bot.connect_service import MessageContext, handle_stateful_message
from team_random_bot.storage import SQLiteStorage


def context(user_id: str = "u1", user_name: str = "Анна") -> MessageContext:
    return MessageContext(chat_id="chat-1", user_id=user_id, user_name=user_name, today=date(2026, 5, 31))


def test_join_command_persists_random_coffee_participant(tmp_path) -> None:
    storage = SQLiteStorage(tmp_path / "bot.sqlite3")

    response = handle_stateful_message("/join дизайнер, маркетинг", storage=storage, context=context())
    participants = handle_stateful_message("/participants", storage=storage, context=context())

    assert "ра [бот] аем" in (response or "")
    assert "Анна (дизайнер, маркетинг)" in (participants or "")


def test_plus_shortcut_and_leave_update_participants(tmp_path) -> None:
    storage = SQLiteStorage(tmp_path / "bot.sqlite3")

    handle_stateful_message("+", storage=storage, context=context())
    assert "Анна" in (handle_stateful_message("/participants", storage=storage, context=context()) or "")

    handle_stateful_message("/leave", storage=storage, context=context())
    assert "Пока никто" in (handle_stateful_message("/participants", storage=storage, context=context()) or "")


def test_pairs_use_saved_active_participants_and_week_message(tmp_path) -> None:
    storage = SQLiteStorage(tmp_path / "bot.sqlite3")
    handle_stateful_message("/join дизайнер, маркетинг", storage=storage, context=context("u1", "Анна"))
    handle_stateful_message("/join разработчик, продукт", storage=storage, context=context("u2", "Борис"))

    response = handle_stateful_message(
        "/pairs",
        storage=storage,
        context=context("u3", "Вера"),
        rng=random.Random(1),
    )
    week = handle_stateful_message("/week", storage=storage, context=context("u3", "Вера"))

    assert "Пары для чата составлены" in (response or "")
    assert "Анна" in (response or "")
    assert "Борис" in (response or "")
    assert "Пары этой недели" in (week or "")


def test_reactions_are_saved_for_today(tmp_path) -> None:
    storage = SQLiteStorage(tmp_path / "bot.sqlite3")

    response = handle_stateful_message("/react @boris классно пообщались", storage=storage, context=context())
    reactions = handle_stateful_message("/reactions", storage=storage, context=context())

    assert "Спасибо" in (response or "")
    assert "boris: классно пообщались — Анна" in (reactions or "")


def test_intro_and_poll_match_spec_copy(tmp_path) -> None:
    storage = SQLiteStorage(tmp_path / "bot.sqlite3")

    intro = handle_stateful_message("/start", storage=storage, context=context())
    poll = handle_stateful_message("/poll", storage=storage, context=context())

    assert "прив, это бот для коллег: ра [бот] аем" in (intro or "")
    assert "Хочешь участвовать" in (poll or "")
