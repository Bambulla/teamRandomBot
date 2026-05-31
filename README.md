# teamRandomBot

Бот для VK Teams, который помогает быстро собрать случайные команды и провести короткую креативную сессию прямо в чате.

## Возможности

- `/team 2 Анна, Борис, Вера, Глеб` — случайно делит участников на команды указанного размера.
- `/teams 3 Анна Борис Вера Глеб Дима` — альтернативная команда для разбивки, работает и без запятых.
- `/roles Анна, Борис, Вера` — раздаёт роли для фасилитации: таймкипер, скептик, презентатор и другие.
- `/idea` — предлагает случайный креативный приём.
- `/brief` — присылает шаблон короткого креативного брифа.
- `/help` — показывает подсказку по командам.

## Подготовка бота в VK Teams

Проект использует официальный Python SDK `mailru-im-bot`.

1. Создайте бота через `@Metabot` в VK Teams и получите токен.
2. Узнайте URL Bot API вашего контура. По умолчанию SDK использует `https://api.icq.net/bot/v1`; для VK Teams/Myteam-контура укажите адрес вашей инсталляции, например `https://myteam.mail.ru/bot/v1`.
3. Скопируйте `.env.example` в `.env` или экспортируйте переменные окружения вручную.

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
export BOT_TOKEN="ваш_токен"
export BOT_API_URL="https://myteam.mail.ru/bot/v1"
team-random-bot
```

Также можно запускать модуль напрямую:

```bash
python -m team_random_bot.bot_app
```

## Разработка

```bash
pip install -e '.[dev]'
pytest
```

Основная логика команд находится в `src/team_random_bot/core.py`, а адаптер VK Teams на `mailru-im-bot` — в `src/team_random_bot/bot_app.py`.
