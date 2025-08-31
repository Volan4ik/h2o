from __future__ import annotations
from datetime import datetime, timedelta, time as dtime
import pytz
from typing import Optional
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from sqlmodel import select
from .config import settings
from .db import engine, get_session
from .models import User, WaterLog
from .keyboards import kb_today

scheduler = AsyncIOScheduler(jobstores={"default": SQLAlchemyJobStore(url=settings.JOBSTORE_URL)})
_bot: Optional[Bot] = None

def set_bot(bot: Bot):
    global _bot
    _bot = bot

def user_now(user: User) -> datetime:
    tz = pytz.timezone(user.tz or settings.DEFAULT_TZ)
    return datetime.now(tz)

def local_day_bounds(user: User):
    now = user_now(user)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end

def to_utc(dt_local: datetime) -> datetime:
    return dt_local.astimezone(pytz.UTC)

def from_utc(dt_utc: datetime, user: User) -> datetime:
    return dt_utc.astimezone(pytz.timezone(user.tz or settings.DEFAULT_TZ))

def consumed_today_ml(user: User) -> int:
    start_local, end_local = local_day_bounds(user)
    with get_session() as s:
        q = select(WaterLog).where(
            (WaterLog.user_id == user.id) &
            (WaterLog.ts >= to_utc(start_local)) &
            (WaterLog.ts < to_utc(end_local))
        )
        rows = s.exec(q).all()
        return sum(r.amount_ml for r in rows)

def last_intake_dt(user: User) -> Optional[datetime]:
    with get_session() as s:
        q = (select(WaterLog)
             .where(WaterLog.user_id == user.id)
             .order_by(WaterLog.ts.desc())
             .limit(1))
        row = s.exec(q).first()
        return row.ts if row else None

def within_quiet_hours(user: User, when_local: Optional[datetime] = None) -> bool:
    now_local = when_local or user_now(user)
    w = dtime(hour=user.wake_at.hour, minute=user.wake_at.minute)
    sl = dtime(hour=user.sleep_at.hour, minute=user.sleep_at.minute)
    return not (w <= now_local.time() <= sl)

def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))

def compute_next_nudge(user: User):
    now_local = user_now(user)
    if within_quiet_hours(user, now_local):
        # Начнём в момент пробуждения
        start_today = now_local.replace(hour=user.wake_at.hour, minute=user.wake_at.minute, second=0, microsecond=0)
        if now_local.time() < dtime(user.wake_at.hour, user.wake_at.minute):
            return start_today, None
        # Уже после сна — до завтра
        return None, None

    consumed = consumed_today_ml(user)
    remaining = user.goal_ml - consumed
    if remaining <= 0:
        return None, None

    # Доза: 10–15% от дневной цели, зажать 150..350 мл
    dose = clamp(int(0.12 * user.goal_ml), 150, 350)

    # Временной шаг по умолчанию 90 мин
    when = now_local + timedelta(minutes=90)

    # Если сильно отстаём, подвинем раньше (например, 45 мин)
    end_today = now_local.replace(hour=user.sleep_at.hour, minute=user.sleep_at.minute, second=0, microsecond=0)
    time_left = max(1, int((end_today - now_local).total_seconds() // 60))
    ideal_rate = user.goal_ml / max(1, int(((end_today - now_local.replace(hour=user.wake_at.hour, minute=user.wake_at.minute)).total_seconds() // 60)))
    current_rate = remaining / time_left
    if current_rate > 1.25 * ideal_rate:
        when = now_local + timedelta(minutes=45)

    # Троттлинг: если последний приём < 40 мин назад — передвинем
    last = last_intake_dt(user)
    if last:
        last_local = from_utc(last, user)
        if (now_local - last_local) < timedelta(minutes=40):
            when = max(when, last_local + timedelta(minutes=40))

    return when, dose

async def send_nudge(user_id: int):
    if _bot is None:
        return
    with get_session() as s:
        user = s.exec(select(User).where(User.id == user_id)).first()
        if not user or not user.smart_on:
            return
        # Уважить mute
        if user.mute_until and user.mute_until > datetime.utcnow().replace(tzinfo=pytz.UTC):
            return
        if within_quiet_hours(user):
            return
        when, dose = compute_next_nudge(user)
        if dose is None:
            return
        await _bot.send_message(user.tg_id, f"Пора глоток ~{dose} мл? 💧", reply_markup=kb_today(dose))
        schedule_next(user)  # Переназначить следующее

def schedule_next(user: User):
    when_local, dose = compute_next_nudge(user)
    if when_local is None:
        # Не планируем (цель достигнута или после сна)
        try:
            scheduler.remove_job(f"nudge:{user.id}")
        except Exception:
            pass
        return
    run_date = when_local.astimezone(pytz.UTC)
    scheduler.add_job(send_nudge, "date", id=f"nudge:{user.id}", replace_existing=True, run_date=run_date, args=[user.id])