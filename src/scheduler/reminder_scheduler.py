"""
Модуль для запуска сервиса напоминаний о питье воды.
Может использоваться как отдельный сервис или интегрироваться с ботом.
"""

import asyncio
import logging
from aiogram import Bot
from src.shared.config import settings
from src.domain.hydration.reminder_service import HydrationReminderService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция для запуска сервиса напоминаний."""
    logger.info("Запуск сервиса напоминаний о питье воды")
    
    # Создаем бота для отправки уведомлений
    bot = Bot(token=settings.BOT_TOKEN)
    
    # Инициализируем сервис напоминаний
    reminder_service = HydrationReminderService(bot)
    
    try:
        # Запускаем сервис
        await reminder_service.start()
        logger.info("Сервис напоминаний успешно запущен")
        
        # Держим сервис запущенным
        while True:
            await asyncio.sleep(60)  # Проверяем каждую минуту
            
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Ошибка в сервисе напоминаний: {e}")
    finally:
        # Останавливаем сервис
        await reminder_service.stop()
        await bot.session.close()
        logger.info("Сервис напоминаний остановлен")


if __name__ == "__main__":
    asyncio.run(main())
