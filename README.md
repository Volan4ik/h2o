## Запуск

1. Создайте файлы `.env.api` и `.env.bot` в корне (рядом с docker-compose.yml):

```
# .env.api
BOT_TOKEN=000000:xxxx
BOT_USERNAME=your_bot
DATABASE_URL=sqlite:///./data/water.db
WEBAPP_URL=https://your-domain.example
API_BASE=https://your-domain.example
ALLOWED_ORIGINS=*
INITDATA_TTL=3600
DEV_ALLOW_NO_INITDATA=true
```

```
# .env.bot
BOT_TOKEN=000000:xxxx
BOT_USERNAME=your_bot
```

2. Запустите:

```
docker-compose up --build
```

API доступно на http://localhost:8000, фронт отдаётся со статики контейнера API.

База данных создаётся автоматически в volume `./data`.

## Интеграция с Telegram WebApp

Через BotFather:

- `/setmenubutton` → Web App → укажите URL фронта (домен API)
- `/setdomain` → укажите домен, на котором доступен ваш WebApp

В проде включите проверку `initData` (установите `DEV_ALLOW_NO_INITDATA=false`).

