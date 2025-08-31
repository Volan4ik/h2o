import asyncio
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlmodel import select
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from ..shared.config import settings
from ..shared.db import jobstore_url, session, init_db
from ..shared.models import User
from ..domain.hydration.service import HydrationService as HS

scheduler = AsyncIOScheduler(jobstores={"default": SQLAlchemyJobStore(url=jobstore_url)})

async def send_nudge(bot: Bot, user: User, dose: int):
    kb = InlineKeyboardMarkup(inline_keyboard=[[ 
        [InlineKeyboardButton(text=f"+{user.default_glass_ml} мл", callback_data=f"add:{user.default_glass_ml}"),
         InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=settings.WEBAPP_URL))]
    ]])
    try:
        await bot.send_message(user.tg_id, f"Пора глоток ~{dose} мл? 💧", reply_markup=kb)
    except Exception:
        pass

async def plan_next(bot: Bot, user: User):
    when_local, dose = HS.compute_next_nudge(user)
    if when_local is None:
        try:
            scheduler.remove_job(f"nudge:{user.id}")
        except Exception:
            pass
        return
    run_dt = when_local.astimezone(timezone.utc)
    scheduler.add_job(lambda: asyncio.create_task(send_nudge(bot, user, dose)), "date", id=f"nudge:{user.id}", replace_existing=True, run_date=run_dt)

async def refresh_all(bot: Bot):
    with session() as s:
        users = s.exec(select(User).where(User.smart_on == True)).all()
        for u in users:
            await plan_next(bot, u)

async def main():
    init_db()
    bot = Bot(settings.BOT_TOKEN)
    scheduler.start()
    await refresh_all(bot)
    while True:
        await refresh_all(bot)
        await asyncio.sleep(900)

if __name__ == "__main__":
    asyncio.run(main())