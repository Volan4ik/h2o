import asyncio
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, CallbackQuery
from aiogram.filters import CommandStart, Command
from sqlmodel import select
from ..shared.config import settings
from ..shared.db import session
from ..shared.models import User, WaterLog
from datetime import datetime, timezone

router = Router()


def app_keyboard(user: User | None = None) -> InlineKeyboardMarkup:
    glass = user.default_glass_ml if user else 250
    return InlineKeyboardMarkup(inline_keyboard=[[ 
        [InlineKeyboardButton(text=f"+{glass} мл", callback_data=f"add:{glass}"),
         InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=settings.WEBAPP_URL))]
    ]])

@router.message(CommandStart())
async def start(msg):
    with session() as s:
        u = s.exec(select(User).where(User.tg_id == msg.from_user.id)).first()
        if not u:
            u = User(tg_id=msg.from_user.id)
            s.add(u); s.commit(); s.refresh(u)
    await msg.answer("Привет! Открой Mini App, чтобы вести воду без лишних сообщений.", reply_markup=app_keyboard(u))

@router.message(Command("app"))
async def app_link(msg):
    with session() as s:
        u = s.exec(select(User).where(User.tg_id == msg.from_user.id)).first()
    await msg.answer("Открываю:", reply_markup=app_keyboard(u))

@router.callback_query(F.data.startswith("add:"))
async def quick_add(call: CallbackQuery):
    amount = int(call.data.split(":")[1])
    with session() as s:
        u = s.exec(select(User).where(User.tg_id == call.from_user.id)).first() or User(tg_id=call.from_user.id)
        s.add(u); s.commit(); s.refresh(u)
        s.add(WaterLog(user_id=u.id, ts_utc=datetime.utcnow().replace(tzinfo=timezone.utc), amount_ml=amount, source="quick"))
        s.commit()
    await call.answer(f"+{amount} мл засчитано 💧")
    try:
        await call.message.edit_reply_markup(reply_markup=app_keyboard(u))
    except Exception:
        pass

async def main():
    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())