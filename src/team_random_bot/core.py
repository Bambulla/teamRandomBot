from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Sequence


class CommandError(ValueError):
    """Raised when a chat command cannot be parsed into a bot action."""


@dataclass(frozen=True)
class TeamSplit:
    """Result of splitting participants into random teams."""

    teams: tuple[tuple[str, ...], ...]
    bench: tuple[str, ...] = ()

    def render(self) -> str:
        lines = ["🎲 Случайные команды:"]
        for index, team in enumerate(self.teams, start=1):
            members = ", ".join(team) if team else "—"
            lines.append(f"{index}. {members}")
        if self.bench:
            lines.append("\nОстались без команды: " + ", ".join(self.bench))
        return "\n".join(lines)


CREATIVE_PROMPTS: tuple[str, ...] = (
    "Придумайте 10 самых плохих решений задачи, а затем переверните 2 из них в полезные идеи.",
    "Сформулируйте идею как афишу: заголовок, обещание, эмоция, доказательство.",
    "Опишите решение глазами трёх людей: новичка, скептика и фаната продукта.",
    "Уберите из идеи главный ресурс: время, бюджет или разработку. Что останется?",
    "Сделайте идею в 10 раз проще: какая версия запускается уже сегодня?",
    "Соберите мини-кампанию из трёх касаний: первое знакомство, вовлечение, финальный призыв.",
    "Придумайте метафору для проекта и проверьте, какие решения она подсказывает.",
    "Сделайте идею полезной для команды, клиента и руководителя одновременно.",
)

BRIEF_TEMPLATE = """🧩 Быстрый креативный бриф
1. Задача: что должно измениться?
2. Аудитория: для кого делаем?
3. Инсайт: какая боль или желание важны?
4. Ограничения: сроки, каналы, тон, нельзя.
5. Критерий успеха: как поймём, что сработало?
6. Первый шаг: что проверяем за 24 часа?"""

HELP_TEXT = """Привет! Я бот для VK Teams: делю участников на случайные команды и помогаю с креативом.

Команды:
/connect или + — записаться в список тех, кто сегодня хочет законнектиться
/today — показать сегодняшний список
/pairs — случайно разбить сегодняшний список на пары
/react @user 👍 — сохранить реакцию на участника
/reactions — показать реакции за сегодня
/skip — убрать себя из сегодняшнего списка
/team 2 Анна, Борис, Вера, Глеб — разбить список на команды по 2 человека
/teams 3 Анна Борис Вера Глеб Дима — то же самое, можно без запятых
/roles Анна, Борис, Вера — раздать фасилитационные роли
/idea — случайный креативный приём
/brief — шаблон короткого брифа
/ping — проверить, что бот жив
/help — показать помощь"""

ROLES: tuple[str, ...] = (
    "фасилитатор",
    "таймкипер",
    "адвокат пользователя",
    "скептик",
    "презентатор",
    "фиксатор решений",
    "генератор альтернатив",
    "проверяющий реалистичность",
)

_SPLIT_PATTERN = re.compile(r"[,;\n]+")
_SPACE_PATTERN = re.compile(r"\s+")


def normalize_participants(raw: str) -> list[str]:
    """Parse comma/newline separated names, falling back to whitespace tokens."""
    raw = raw.strip()
    if not raw:
        return []

    if _SPLIT_PATTERN.search(raw):
        chunks = _SPLIT_PATTERN.split(raw)
    else:
        chunks = _SPACE_PATTERN.split(raw)

    participants = []
    seen = set()
    for chunk in chunks:
        name = " ".join(chunk.strip().split())
        if not name:
            continue
        dedupe_key = name.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        participants.append(name)
    return participants


def split_into_teams(
    participants: Sequence[str],
    team_size: int,
    *,
    rng: random.Random | None = None,
) -> TeamSplit:
    if team_size < 1:
        raise CommandError("Размер команды должен быть больше 0.")
    if len(participants) < 2:
        raise CommandError("Нужно минимум два участника.")

    shuffled = list(participants)
    (rng or random).shuffle(shuffled)
    teams = tuple(tuple(shuffled[i : i + team_size]) for i in range(0, len(shuffled), team_size))
    return TeamSplit(teams=teams)


def parse_team_command(text: str, *, rng: random.Random | None = None) -> str:
    parts = text.strip().split(maxsplit=2)
    if len(parts) < 3:
        raise CommandError("Формат: /team 2 Анна, Борис, Вера, Глеб")

    try:
        team_size = int(parts[1])
    except ValueError as exc:
        raise CommandError("После команды укажите размер команды числом: /team 2 ...") from exc

    participants = normalize_participants(parts[2])
    split = split_into_teams(participants, team_size, rng=rng)
    return split.render()


def assign_roles(raw_participants: str, *, rng: random.Random | None = None) -> str:
    participants = normalize_participants(raw_participants)
    if not participants:
        raise CommandError("Формат: /roles Анна, Борис, Вера")

    randomizer = rng or random
    shuffled_roles = list(ROLES)
    randomizer.shuffle(shuffled_roles)

    lines = ["🎭 Роли на сессию:"]
    for index, participant in enumerate(participants):
        role = shuffled_roles[index % len(shuffled_roles)]
        lines.append(f"• {participant}: {role}")
    return "\n".join(lines)


def random_idea(*, rng: random.Random | None = None) -> str:
    randomizer = rng or random
    return "💡 Креативный приём:\n" + randomizer.choice(CREATIVE_PROMPTS)


def handle_message(text: str, *, rng: random.Random | None = None) -> str | None:
    stripped = text.strip()
    command = stripped.split(maxsplit=1)[0].lower() if stripped else ""

    if command in {"/start", "/help"}:
        return HELP_TEXT
    if command in {"/team", "/teams", "/shuffle"}:
        return parse_team_command(stripped, rng=rng)
    if command == "/roles":
        raw = stripped.split(maxsplit=1)[1] if len(stripped.split(maxsplit=1)) > 1 else ""
        return assign_roles(raw, rng=rng)
    if command == "/idea":
        return random_idea(rng=rng)
    if command == "/brief":
        return BRIEF_TEMPLATE
    if command == "/ping":
        return "pong"
    return None


def safe_handle_message(text: str, *, rng: random.Random | None = None) -> str | None:
    try:
        return handle_message(text, rng=rng)
    except CommandError as exc:
        return f"⚠️ {exc}"
