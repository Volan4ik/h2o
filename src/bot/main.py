import asyncio
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from src.shared.config import settings

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
router = Router()

@router.message(CommandStart())
async def start_cmd(msg: Message):
    await msg.answer("👋 Привет! Я помогу тебе пить воду 💧")

dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
