from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import date

from team_random_bot.core import safe_handle_message, split_into_teams
from team_random_bot.storage import SQLiteStorage

CONNECT_SHORTCUTS = {"+", "++", "хочу", "иду", "я", "я хочу"}
CANCEL_COMMANDS = {"/skip", "/cancel", "/no", "-"}
TODAY_COMMANDS = {"/today", "/connects", "/list"}
CONNECT_COMMANDS = {"/connect", "/join", "/want"}
REACTION_COMMANDS = {"/react", "/reaction"}
PAIR_COMMANDS = {"/pairs", "/match"}


@dataclass(frozen=True)
class MessageContext:
    chat_id: str
    user_id: str
    user_name: str
    today: date


def _first_token(text: str) -> str:
    return text.strip().split(maxsplit=1)[0].lower() if text.strip() else ""


def _tail(text: str) -> str:
    parts = text.strip().split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def _render_people(people: list[str]) -> str:
    return "\n".join(f"{index}. {name}" for index, name in enumerate(people, start=1))


def mark_connection(storage: SQLiteStorage, context: MessageContext, comment: str = "") -> str:
    storage.save_intent(
        chat_id=context.chat_id,
        user_id=context.user_id,
        user_name=context.user_name,
        intent_date=context.today,
        comment=comment,
    )
    suffix = f" Комментарий: {comment}" if comment else ""
    return f"✅ {context.user_name}, записал(а) тебя на коннект сегодня.{suffix}"


def cancel_connection(storage: SQLiteStorage, context: MessageContext) -> str:
    storage.cancel_intent(chat_id=context.chat_id, user_id=context.user_id, intent_date=context.today)
    return f"Ок, {context.user_name}, убрал(а) тебя из списка на сегодня."


def render_today(storage: SQLiteStorage, context: MessageContext) -> str:
    intents = storage.list_active_intents(chat_id=context.chat_id, intent_date=context.today)
    if not intents:
        return "Сегодня пока никто не записался на коннект. Напишите `/connect` или `+`."

    lines = [f"🤝 Сегодня хотят законнектиться ({len(intents)}):"]
    for index, intent in enumerate(intents, start=1):
        comment = f" — {intent.comment}" if intent.comment else ""
        lines.append(f"{index}. {intent.user_name}{comment}")
    return "\n".join(lines)


def create_pairs(storage: SQLiteStorage, context: MessageContext, *, rng: random.Random | None = None) -> str:
    intents = storage.list_active_intents(chat_id=context.chat_id, intent_date=context.today)
    people = [intent.user_name for intent in intents]
    if len(people) < 2:
        return "Нужно минимум два человека в сегодняшнем списке. Напишите `/connect` или `+`."
    return split_into_teams(people, 2, rng=rng).render()


def save_reaction(storage: SQLiteStorage, context: MessageContext, raw: str) -> str:
    match = re.match(r"(?P<target>\S+)\s+(?P<reaction>\S+)", raw.strip())
    if not match:
        return "Формат: `/react @user 👍`"

    target = match.group("target").lstrip("@")
    reaction = match.group("reaction")
    storage.save_reaction(
        chat_id=context.chat_id,
        actor_user_id=context.user_id,
        actor_name=context.user_name,
        target_user_id=target,
        reaction=reaction,
        reaction_date=context.today,
    )
    return f"{reaction} сохранил(а) реакцию от {context.user_name} для {target}."


def render_reactions(storage: SQLiteStorage, context: MessageContext) -> str:
    reactions = storage.list_reactions(chat_id=context.chat_id, reaction_date=context.today)
    if not reactions:
        return "Сегодня реакций на коннекты пока нет."

    lines = ["📌 Реакции сегодня:"]
    for reaction in reactions:
        lines.append(f"• {reaction.target_user_id}: {reaction.reaction} от {reaction.actor_name}")
    return "\n".join(lines)


def handle_stateful_message(
    text: str,
    *,
    storage: SQLiteStorage,
    context: MessageContext,
    rng: random.Random | None = None,
) -> str | None:
    stripped = text.strip()
    lowered = stripped.lower()
    command = _first_token(stripped)

    if lowered in CONNECT_SHORTCUTS or command in CONNECT_COMMANDS:
        return mark_connection(storage, context, _tail(stripped) if command in CONNECT_COMMANDS else "")
    if command in CANCEL_COMMANDS:
        return cancel_connection(storage, context)
    if command in TODAY_COMMANDS:
        return render_today(storage, context)
    if command in PAIR_COMMANDS:
        return create_pairs(storage, context, rng=rng)
    if command in REACTION_COMMANDS:
        return save_reaction(storage, context, _tail(stripped))
    if command == "/reactions":
        return render_reactions(storage, context)

    return safe_handle_message(text, rng=rng)
