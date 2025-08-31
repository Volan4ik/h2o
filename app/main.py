import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from .config import settings
from .db import init_db
from .handlers import router
from .reminders import scheduler, set_bot


def _ensure_sqlite_dirs():
    """Создаёт каталоги для SQLite-файлов из DATABASE_URL и JOBSTORE_URL."""
    urls = [settings.DATABASE_URL, settings.JOBSTORE_URL]
    for url in urls:
        if url.startswith("sqlite:///"):
            # относительный путь, например sqlite:///./data/water.db
            path = url.removeprefix("sqlite:///")
        elif url.startswith("sqlite:////"):
            # абсолютный путь, например sqlite:////Data/water.db
            path = url.removeprefix("sqlite:////")
            if os.name == "nt":
                path = path.lstrip("/")
        else:
            continue
        dirpath = os.path.dirname(path) or "."
        os.makedirs(dirpath, exist_ok=True)


async def main():
    _ensure_sqlite_dirs()
    init_db()
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    set_bot(bot)
    dp = Dispatcher()
    dp.include_router(router)

    # Старт планировщика
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())