from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path
from typing import Any

from bot.bot import Bot

from team_random_bot.connect_service import MessageContext, handle_stateful_message
from team_random_bot.core import HELP_TEXT
from team_random_bot.storage import SQLiteStorage

LOGGER = logging.getLogger(__name__)
DEFAULT_API_URL = "https://api.icq.net/bot/v1"
DEFAULT_DATABASE_PATH = Path("data/team_random_bot.sqlite3")


def _api_url_from_env() -> str:
    return (
        os.environ.get("BOT_API_URL")
        or os.environ.get("VKTEAMS_BOT_API_URL")
        or DEFAULT_API_URL
    )


def _database_path_from_env() -> Path:
    return Path(os.environ.get("DATABASE_PATH") or os.environ.get("BOT_DATABASE_PATH") or DEFAULT_DATABASE_PATH)


def _nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _user_name(data: dict[str, Any]) -> str:
    first_name = _nested(data, "from", "firstName") or _nested(data, "from", "first_name")
    last_name = _nested(data, "from", "lastName") or _nested(data, "from", "last_name")
    full_name = " ".join(part for part in (first_name, last_name) if part).strip()
    return (
        full_name
        or _nested(data, "from", "nick")
        or _nested(data, "from", "userId")
        or _nested(data, "from", "user_id")
        or "unknown"
    )


def _message_context(data: dict[str, Any]) -> MessageContext | None:
    chat_id = _nested(data, "chat", "chatId") or _nested(data, "chat", "chat_id")
    user_id = _nested(data, "from", "userId") or _nested(data, "from", "user_id")
    if not chat_id or not user_id:
        return None
    return MessageContext(
        chat_id=str(chat_id),
        user_id=str(user_id),
        user_name=str(_user_name(data)),
        today=date.today(),
    )


def build_bot(
    token: str,
    api_url_base: str | None = None,
    storage: SQLiteStorage | None = None,
) -> Bot:
    bot = Bot(
        token=token,
        name=os.environ.get("BOT_NAME", "team-random-bot"),
        version=os.environ.get("BOT_VERSION", "0.1.0"),
        api_url_base=api_url_base or _api_url_from_env(),
        is_myteam=True,
    )
    repository = storage or SQLiteStorage(_database_path_from_env())

    @bot.message_handler()
    def on_message(bot: Bot, event) -> None:  # type: ignore[no-untyped-def]
        data = event.data
        text = data.get("text", "")
        context = _message_context(data)
        if context is None:
            LOGGER.warning("Cannot process event without chatId/userId: %s", data)
            return

        answer = handle_stateful_message(text, storage=repository, context=context)
        if answer is None:
            return

        bot.send_text(chat_id=context.chat_id, text=answer)

    return bot


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    token = os.environ.get("BOT_TOKEN") or os.environ.get("VKTEAMS_BOT_TOKEN")
    if not token:
        raise RuntimeError("Set BOT_TOKEN or VKTEAMS_BOT_TOKEN before starting the bot.")

    bot = build_bot(token=token)
    LOGGER.info("VK Teams bot started with mailru-im-bot and SQLite storage")
    if os.environ.get("LOG_HELP_ON_START", "0") == "1":
        LOGGER.info("Available commands:\n%s", HELP_TEXT)

    bot.start_polling()
    bot.idle()


def run() -> None:
    main()


if __name__ == "__main__":
    run()
