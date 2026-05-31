from __future__ import annotations

import random

import pytest

from team_random_bot.core import (
    CommandError,
    assign_roles,
    handle_message,
    normalize_participants,
    parse_team_command,
    split_into_teams,
)


def test_normalize_participants_deduplicates_and_supports_commas() -> None:
    assert normalize_participants(" Анна, Борис; анна\nВера ") == ["Анна", "Борис", "Вера"]


def test_split_into_teams_is_deterministic_with_seed() -> None:
    split = split_into_teams(["Анна", "Борис", "Вера", "Глеб"], 2, rng=random.Random(7))

    assert split.teams == (("Глеб", "Борис"), ("Анна", "Вера"))
    assert "🎲 Случайные команды" in split.render()


def test_parse_team_command_accepts_vk_teams_command_text() -> None:
    result = parse_team_command("/teams 2 Анна, Борис, Вера", rng=random.Random(1))

    assert "1." in result
    assert "2." in result


def test_parse_team_command_returns_readable_errors() -> None:
    with pytest.raises(CommandError, match="размер команды числом"):
        parse_team_command("/team два Анна Борис")


def test_assign_roles_mentions_every_participant() -> None:
    result = assign_roles("Анна, Борис", rng=random.Random(2))

    assert "Анна" in result
    assert "Борис" in result
    assert "🎭" in result


def test_handle_message_ignores_regular_chat_messages() -> None:
    assert handle_message("давайте обсудим") is None


def test_handle_message_serves_help_and_ping() -> None:
    assert "Команды" in (handle_message("/help") or "")
    assert handle_message("/ping") == "pong"
