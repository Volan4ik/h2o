import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.filters import CommandStart
from src.shared.config import settings
from src.domain.hydration.reminder_service import HydrationReminderService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
router = Router()

# Инициализация сервиса напоминаний
reminder_service = HydrationReminderService(bot)

@router.message(CommandStart())
async def start_cmd(msg: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=settings.WEBAPP_URL))]],
        resize_keyboard=True
    )
    await msg.answer(
        "👋 Привет! Я помогу тебе пить воду 💧\nНажми, чтобы открыть мини‑приложение:",
        reply_markup=kb,
    )

dp.include_router(router)

async def main():
    try:
        # Запускаем сервис напоминаний
        await reminder_service.start()
        logger.info("Сервис напоминаний запущен")
        
        # Запускаем бота
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")
    finally:
        # Останавливаем сервис напоминаний при завершении
        await reminder_service.stop()

if __name__ == "__main__":
    asyncio.run(main())
