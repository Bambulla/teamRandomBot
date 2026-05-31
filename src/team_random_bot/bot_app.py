from __future__ import annotations

import asyncio
import logging
import os

from vk_teams_async_bot import Bot, Dispatcher, NewMessageEvent

from team_random_bot.core import HELP_TEXT, safe_handle_message

LOGGER = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    @dp.message()
    async def on_message(event: NewMessageEvent, bot: Bot) -> None:
        text = event.text or ""
        answer = safe_handle_message(text)
        if answer is None:
            return
        await bot.send_text(chat_id=event.chat.chat_id, text=answer)

    return dp


async def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    token = os.environ.get("BOT_TOKEN") or os.environ.get("VKTEAMS_BOT_TOKEN")
    if not token:
        raise RuntimeError("Set BOT_TOKEN or VKTEAMS_BOT_TOKEN before starting the bot.")

    bot = Bot(
        bot_token=token,
        url=os.environ.get("BOT_API_URL") or os.environ.get("VKTEAMS_BOT_API_URL"),
    )
    dispatcher = build_dispatcher()

    @bot.on_startup
    async def on_startup(bot: Bot) -> None:
        LOGGER.info("VK Teams bot started")
        if os.environ.get("LOG_HELP_ON_START", "0") == "1":
            LOGGER.info("Available commands:\n%s", HELP_TEXT)

    @bot.on_shutdown
    async def on_shutdown(bot: Bot) -> None:
        LOGGER.info("VK Teams bot stopped")

    async with bot:
        await bot.start_polling(dispatcher)


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
