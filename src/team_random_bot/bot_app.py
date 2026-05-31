from __future__ import annotations

import logging
import os

from bot.bot import Bot

from team_random_bot.core import HELP_TEXT, safe_handle_message

LOGGER = logging.getLogger(__name__)
DEFAULT_API_URL = "https://api.icq.net/bot/v1"


def _api_url_from_env() -> str:
    return (
        os.environ.get("BOT_API_URL")
        or os.environ.get("VKTEAMS_BOT_API_URL")
        or DEFAULT_API_URL
    )


def build_bot(token: str, api_url_base: str | None = None) -> Bot:
    bot = Bot(
        token=token,
        name=os.environ.get("BOT_NAME", "team-random-bot"),
        version=os.environ.get("BOT_VERSION", "0.1.0"),
        api_url_base=api_url_base or _api_url_from_env(),
        is_myteam=True,
    )

    @bot.message_handler()
    def on_message(bot: Bot, event) -> None:  # type: ignore[no-untyped-def]
        text = event.data.get("text", "")
        answer = safe_handle_message(text)
        if answer is None:
            return

        chat_id = event.data.get("chat", {}).get("chatId")
        if not chat_id:
            LOGGER.warning("Cannot answer event without chatId: %s", event.data)
            return
        bot.send_text(chat_id=chat_id, text=answer)

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
    LOGGER.info("VK Teams bot started with mailru-im-bot")
    if os.environ.get("LOG_HELP_ON_START", "0") == "1":
        LOGGER.info("Available commands:\n%s", HELP_TEXT)

    bot.start_polling()
    bot.idle()


def run() -> None:
    main()


if __name__ == "__main__":
    run()
