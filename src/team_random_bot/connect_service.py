from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import date

from team_random_bot.core import safe_handle_message
from team_random_bot.storage import Participant, SQLiteStorage

START_COMMANDS = {"/start", "/help"}
JOIN_COMMANDS = {"/join", "/yes", "/participate", "+"}
LEAVE_COMMANDS = {"/leave", "/no", "/pause", "-"}
PARTICIPANTS_COMMANDS = {"/participants", "/list", "/status"}
PAIR_COMMANDS = {"/pairs", "/match"}
REACTION_COMMANDS = {"/react", "/reaction"}
REACTIONS_COMMANDS = {"/reactions", "/feedback"}
POLL_COMMANDS = {"/poll", "/question"}

INTRO_MESSAGE = """прив, это бот для коллег: ра [бот] аем.

я нужен, чтобы навести мосты между коллегами внутри Рокета, чтобы каждый был в контексте происходящего в других командах.
раз в неделю рандомным образом я буду формировать пары, с которыми вы найдёте общий свободный слот на 30 минут и встретитесь — обсудите что нового у каждого в отделе, можете поштормить над задачами друг друга или просто поболтать.

когда будете писать друг другу — укажите вашу должность и отдел.

Команды:
/join должность, отдел — участвовать в еженедельном рандом-кофе
/leave — не участвовать в ближайших парах
/participants — показать участников
/pairs — составить пары на эту неделю
/react @user текст — оставить реакцию после встречи
/reactions — показать реакции"""

POLL_MESSAGE = """Хочешь участвовать в ра [бот] аем?

Если да — напиши `/join должность, отдел` или просто `+`.
Если хочешь пропустить неделю — напиши `/leave` или `-`."""

PAIRS_HEADER = """Пары для чата составлены!
Смотри, с кем встречаешься на этой неделе:

Напишите друг другу в личку, чтобы договориться на свободный слот на 30 минут, чтобы почирикать о рабочем и всяком."""


@dataclass(frozen=True)
class MessageContext:
    chat_id: str
    user_id: str
    user_name: str
    today: date


def week_key(day: date) -> str:
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _first_token(text: str) -> str:
    return text.strip().split(maxsplit=1)[0].lower() if text.strip() else ""


def _tail(text: str) -> str:
    parts = text.strip().split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def _split_profile(raw: str) -> tuple[str, str]:
    if not raw:
        return "", ""
    parts = [part.strip() for part in re.split(r"[,;|]", raw, maxsplit=1)]
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def _participant_label(participant: Participant) -> str:
    details = ", ".join(part for part in (participant.position, participant.department) if part)
    return f"{participant.user_name} ({details})" if details else participant.user_name


def render_intro() -> str:
    return INTRO_MESSAGE


def render_poll() -> str:
    return POLL_MESSAGE


def join_random_coffee(storage: SQLiteStorage, context: MessageContext, raw_profile: str = "") -> str:
    position, department = _split_profile(raw_profile)
    storage.upsert_participant(
        chat_id=context.chat_id,
        user_id=context.user_id,
        user_name=context.user_name,
        position=position,
        department=department,
        active=True,
    )
    profile_hint = ""
    if not position and not department:
        profile_hint = " Потом можно обновить профиль командой `/join должность, отдел`."
    return f"✅ {context.user_name}, записал(а) тебя в ра [бот] аем.{profile_hint}"


def leave_random_coffee(storage: SQLiteStorage, context: MessageContext) -> str:
    storage.set_participation(chat_id=context.chat_id, user_id=context.user_id, active=False)
    return f"Ок, {context.user_name}, на ближайшие пары тебя не добавляю. Вернуться можно через `/join`."


def render_participants(storage: SQLiteStorage, context: MessageContext) -> str:
    participants = storage.list_active_participants(chat_id=context.chat_id)
    if not participants:
        return "Пока никто не участвует. Напишите `/join должность, отдел` или `+`."

    lines = [f"Участники ра [бот] аем ({len(participants)}):"]
    lines.extend(f"{index}. {_participant_label(participant)}" for index, participant in enumerate(participants, start=1))
    return "\n".join(lines)


def _make_pairs(
    participants: list[Participant],
    *,
    rng: random.Random | None = None,
) -> tuple[list[tuple[Participant, Participant]], Participant | None]:
    shuffled = list(participants)
    (rng or random).shuffle(shuffled)
    bench = shuffled.pop() if len(shuffled) % 2 else None
    pairs = [(shuffled[index], shuffled[index + 1]) for index in range(0, len(shuffled), 2)]
    return pairs, bench


def create_weekly_pairs(
    storage: SQLiteStorage,
    context: MessageContext,
    *,
    rng: random.Random | None = None,
) -> str:
    participants = storage.list_active_participants(chat_id=context.chat_id)
    if len(participants) < 2:
        return "Нужно минимум два участника. Пусть коллеги напишут `/join должность, отдел` или `+`."

    pairs, bench = _make_pairs(participants, rng=rng)
    current_week = week_key(context.today)
    storage.replace_weekly_pairings(
        chat_id=context.chat_id,
        week_key=current_week,
        pairs=[(first.user_id, second.user_id) for first, second in pairs],
        bench_user_id=bench.user_id if bench else None,
    )

    lines = [PAIRS_HEADER, ""]
    for index, (first, second) in enumerate(pairs, start=1):
        lines.append(f"{index}. {_participant_label(first)} ↔ {_participant_label(second)}")
    if bench:
        lines.append(f"\nБез пары на этой неделе: {_participant_label(bench)} — добавим в следующий раунд.")
    return "\n".join(lines)


def render_weekly_pairs(storage: SQLiteStorage, context: MessageContext) -> str:
    pairings = storage.list_weekly_pairings(chat_id=context.chat_id, week_key=week_key(context.today))
    if not pairings:
        return "На эту неделю пары ещё не составлены. Запустите `/pairs`."

    lines = ["Пары этой недели:"]
    for index, pairing in enumerate(pairings, start=1):
        if pairing.second_user_name:
            lines.append(f"{index}. {pairing.first_user_name} ↔ {pairing.second_user_name}")
        else:
            lines.append(f"{index}. {pairing.first_user_name} — без пары")
    return "\n".join(lines)


def save_reaction(storage: SQLiteStorage, context: MessageContext, raw: str) -> str:
    match = re.match(r"(?P<target>\S+)\s+(?P<reaction>.+)", raw.strip())
    if not match:
        return "Формат: `/react @user классно пообщались`"

    target = match.group("target").lstrip("@")
    reaction = match.group("reaction").strip()
    storage.save_reaction(
        chat_id=context.chat_id,
        actor_user_id=context.user_id,
        actor_name=context.user_name,
        target_user_id=target,
        reaction=reaction,
        reaction_date=context.today,
    )
    return f"Спасибо! Сохранил(а) реакцию от {context.user_name} для {target}."


def render_reactions(storage: SQLiteStorage, context: MessageContext) -> str:
    reactions = storage.list_reactions(chat_id=context.chat_id, reaction_date=context.today)
    if not reactions:
        return "Сегодня реакций после встреч пока нет."

    lines = ["Реакции сегодня:"]
    for reaction in reactions:
        lines.append(f"• {reaction.target_user_id}: {reaction.reaction} — {reaction.actor_name}")
    return "\n".join(lines)


def handle_stateful_message(
    text: str,
    *,
    storage: SQLiteStorage,
    context: MessageContext,
    rng: random.Random | None = None,
) -> str | None:
    stripped = text.strip()
    command = _first_token(stripped)

    if command in START_COMMANDS:
        return render_intro()
    if command in POLL_COMMANDS:
        return render_poll()
    if command in JOIN_COMMANDS:
        return join_random_coffee(storage, context, _tail(stripped) if command != "+" else "")
    if command in LEAVE_COMMANDS:
        return leave_random_coffee(storage, context)
    if command in PARTICIPANTS_COMMANDS:
        return render_participants(storage, context)
    if command in PAIR_COMMANDS:
        return create_weekly_pairs(storage, context, rng=rng)
    if command == "/week":
        return render_weekly_pairs(storage, context)
    if command in REACTION_COMMANDS:
        return save_reaction(storage, context, _tail(stripped))
    if command in REACTIONS_COMMANDS:
        return render_reactions(storage, context)

    return safe_handle_message(text, rng=rng)
