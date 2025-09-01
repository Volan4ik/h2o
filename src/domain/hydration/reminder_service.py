import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import select, func
from aiogram import Bot

from src.shared.config import settings
from src.shared.db import session
from src.shared.models import User, WaterLog

logger = logging.getLogger(__name__)


class HydrationReminderService:
    """
    Сервис умных напоминаний о питье воды.
    
    Логика уведомлений:
    - Максимум 3-4 уведомления в день
    - Окно тишины: 22:00 - 07:00
    - Утро (8-10): если выпито <200 мл
    - День (12-14): если выпито <40% дневной цели
    - Вечер (18-20): если выпито <70-80% дневной цели
    - Критическое отставание (21:00): если далеко до цели
    """
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.default_tz = pytz.timezone(settings.DEFAULT_TZ)
        
        # Настройка расписания проверок
        self.check_times = [
            (8, "morning"),   # Утро
            (10, "morning"),  # Утро (дублируем для покрытия окна)
            (12, "day"),      # День
            (14, "day"),      # День (дублируем)
            (18, "evening"),  # Вечер
            (20, "evening"),  # Вечер (дублируем)
            (21, "critical"), # Критическое отставание
        ]
        
        # Счетчик уведомлений для каждого пользователя
        self.daily_notifications = {}
        
    async def start(self):
        """Запускает планировщик напоминаний."""
        logger.info("Запуск сервиса напоминаний о питье воды")
        
        # Добавляем задачи для каждого времени проверки
        for hour, period in self.check_times:
            self.scheduler.add_job(
                self.check_and_notify,
                CronTrigger(hour=hour, minute=0, timezone=settings.DEFAULT_TZ),
                args=[hour, period],
                id=f"hydration_check_{hour}",
                replace_existing=True
            )
        
        # Задача для сброса счетчиков уведомлений в полночь
        self.scheduler.add_job(
            self._reset_daily_counters,
            CronTrigger(hour=0, minute=0, timezone=settings.DEFAULT_TZ),
            id="reset_daily_counters",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Планировщик напоминаний запущен")
    
    async def stop(self):
        """Останавливает планировщик."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Планировщик напоминаний остановлен")
    
    async def _reset_daily_counters(self):
        """Сбрасывает счетчики ежедневных уведомлений."""
        self.daily_notifications.clear()
        logger.info("Счетчики ежедневных уведомлений сброшены")
    
    async def check_and_notify(self, hour: int, period: str):
        """
        Проверяет всех пользователей и отправляет уведомления при необходимости.
        
        Args:
            hour: Час проверки
            period: Период дня (morning, day, evening, critical)
        """
        logger.info(f"Проверка напоминаний для часа {hour} ({period})")
        
        try:
            with session() as db:
                # Получаем всех пользователей
                users = db.exec(select(User)).all()
                
                for user in users:
                    try:
                        await self._check_user_hydration(db, user, hour, period)
                    except Exception as e:
                        logger.error(f"Ошибка при проверке пользователя {user.id}: {e}")
                        
        except Exception as e:
            logger.error(f"Ошибка при проверке напоминаний: {e}")
    
    async def _check_user_hydration(self, db, user: User, hour: int, period: str):
        """Проверяет гидратацию конкретного пользователя."""
        user_tz = self.default_tz  # Можно расширить для поддержки индивидуальных таймзон
        
        # Проверяем окно тишины (22:00 - 07:00)
        if self._is_quiet_hours(hour):
            return
        
        # Проверяем лимит уведомлений (максимум 4 в день)
        user_key = f"{user.id}_{datetime.now().date()}"
        if self.daily_notifications.get(user_key, 0) >= 4:
            return
        
        # Получаем статистику за сегодня
        today_stats = self._get_today_hydration_stats(db, user, user_tz)
        
        # Проверяем, нужно ли напоминание
        should_notify = self._should_send_reminder(user, today_stats, period)
        
        if should_notify:
            await self._send_reminder(user, today_stats, period)
            self.daily_notifications[user_key] = self.daily_notifications.get(user_key, 0) + 1
    
    def _is_quiet_hours(self, hour: int) -> bool:
        """Проверяет, находится ли час в окне тишины."""
        return hour >= 22 or hour < 7
    
    def _get_today_hydration_stats(self, db, user: User, user_tz) -> dict:
        """Получает статистику гидратации пользователя за сегодня."""
        now = datetime.now(user_tz)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Конвертируем в UTC для запроса к БД
        start_utc = start_of_day.astimezone(pytz.UTC)
        end_utc = end_of_day.astimezone(pytz.UTC)
        
        # Получаем общее количество выпитой воды за день
        result = db.exec(
            select(func.sum(WaterLog.amount_ml))
            .where(WaterLog.user_id == user.id)
            .where(WaterLog.ts_utc >= start_utc)
            .where(WaterLog.ts_utc <= end_utc)
        ).first()
        
        total_ml = result or 0
        progress_percent = (total_ml / user.goal_ml) * 100 if user.goal_ml > 0 else 0
        
        return {
            "total_ml": total_ml,
            "goal_ml": user.goal_ml,
            "progress_percent": progress_percent,
            "remaining_ml": max(0, user.goal_ml - total_ml),
            "current_hour": now.hour
        }
    
    def _should_send_reminder(self, user: User, stats: dict, period: str) -> bool:
        """Определяет, нужно ли отправить напоминание."""
        total_ml = stats["total_ml"]
        goal_ml = stats["goal_ml"]
        progress_percent = stats["progress_percent"]
        
        if period == "morning":
            # Утро: напомнить, если выпито <200 мл
            return total_ml < 200
            
        elif period == "day":
            # День: напомнить, если выпито <40% дневной цели
            return progress_percent < 40
            
        elif period == "evening":
            # Вечер: напомнить, если выпито <70% дневной цели
            return progress_percent < 70
            
        elif period == "critical":
            # Критическое отставание: если выпито <50% дневной цели
            return progress_percent < 50
            
        return False
    
    async def _send_reminder(self, user: User, stats: dict, period: str):
        """Отправляет напоминание пользователю."""
        message = self._generate_reminder_message(user, stats, period)
        
        try:
            await self.bot.send_message(
                chat_id=user.tg_id,
                text=message,
                parse_mode="HTML"
            )
            logger.info(f"Напоминание отправлено пользователю {user.id} ({period})")
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания пользователю {user.id}: {e}")
    
    def _generate_reminder_message(self, user: User, stats: dict, period: str) -> str:
        """Генерирует текст напоминания."""
        total_ml = stats["total_ml"]
        goal_ml = stats["goal_ml"]
        progress_percent = stats["progress_percent"]
        remaining_ml = stats["remaining_ml"]
        
        # Эмодзи в зависимости от периода
        emoji_map = {
            "morning": "🌅",
            "day": "☀️", 
            "evening": "🌆",
            "critical": "⚠️"
        }
        
        emoji = emoji_map.get(period, "💧")
        
        # Базовое сообщение
        if period == "morning":
            message = f"{emoji} <b>Доброе утро!</b>\n\n"
            message += f"Время начать день с воды! Выпейте стаканчик 💧\n\n"
            message += f"📊 За сегодня: {total_ml} мл из {goal_ml} мл"
            
        elif period == "day":
            message = f"{emoji} <b>Время для воды!</b>\n\n"
            message += f"Вы выпили {progress_percent:.0f}% от дневной цели.\n"
            message += f"Осталось {remaining_ml} мл до цели 🎯\n\n"
            message += f"💡 Рекомендуем выпить {user.default_glass_ml} мл прямо сейчас!"
            
        elif period == "evening":
            message = f"{emoji} <b>Не забывайте о воде!</b>\n\n"
            message += f"Прогресс: {progress_percent:.0f}% ({total_ml}/{goal_ml} мл)\n"
            message += f"Осталось {remaining_ml} мл до цели 🎯\n\n"
            message += f"💧 Выпейте {user.default_glass_ml} мл для поддержания гидратации"
            
        elif period == "critical":
            message = f"{emoji} <b>Последний шанс!</b>\n\n"
            message += f"День подходит к концу, а вы выпили только {progress_percent:.0f}% от цели.\n"
            message += f"Осталось {remaining_ml} мл до {goal_ml} мл 🎯\n\n"
            message += f"⏰ Пора наверстать упущенное! Выпейте {user.default_glass_ml} мл"
        
        # Добавляем мотивационные фразы
        motivational_phrases = [
            "Вы справитесь! 💪",
            "Каждая капля на счету! 💧",
            "Ваше здоровье важнее всего! ❤️",
            "Продолжайте в том же духе! 🌟"
        ]
        
        import random
        message += f"\n\n{random.choice(motivational_phrases)}"
        
        return message
    
    async def get_user_stats(self, user_id: int) -> Optional[dict]:
        """Получает статистику пользователя за сегодня (для отладки)."""
        try:
            with session() as db:
                user = db.get(User, user_id)
                if not user:
                    return None
                
                stats = self._get_today_hydration_stats(db, user, self.default_tz)
                return {
                    "user_id": user_id,
                    "goal_ml": user.goal_ml,
                    "default_glass_ml": user.default_glass_ml,
                    **stats
                }
        except Exception as e:
            logger.error(f"Ошибка получения статистики пользователя {user_id}: {e}")
            return None
