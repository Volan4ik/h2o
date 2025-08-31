from __future__ import annotations
from datetime import datetime, timedelta, time as dtime, timezone
import pytz
from sqlmodel import select
from ...shared.db import session
from ...shared.models import User, WaterLog

OZ_TO_ML = 29.5735

class HydrationService:
    @staticmethod
    def user_now(user: User) -> datetime:
        return datetime.now(pytz.timezone(user.tz))

    @staticmethod
    def local_bounds(user: User):
        now = HydrationService.user_now(user)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return start, end

    @staticmethod
    def to_utc(dt_local: datetime) -> datetime:
        return dt_local.astimezone(timezone.utc)

    @staticmethod
    def from_utc(dt_utc: datetime, user: User) -> datetime:
        return dt_utc.astimezone(pytz.timezone(user.tz))

    @staticmethod
    def consumed_today_ml(user: User) -> int:
        start, end = HydrationService.local_bounds(user)
        with session() as s:
            rows = s.exec(select(WaterLog).where(
                (WaterLog.user_id == user.id) &
                (WaterLog.ts_utc >= HydrationService.to_utc(start)) &
                (WaterLog.ts_utc < HydrationService.to_utc(end))
            )).all()
            return sum(r.amount_ml for r in rows)

    @staticmethod
    def last_intake_local(user: User) -> datetime | None:
        with session() as s:
            row = s.exec(select(WaterLog).where(WaterLog.user_id == user.id).order_by(WaterLog.ts_utc.desc()).limit(1)).first()
            return HydrationService.from_utc(row.ts_utc, user) if row else None

    @staticmethod
    def within_quiet_hours(user: User, when_local: datetime | None = None) -> bool:
        now = when_local or HydrationService.user_now(user)
        w = dtime(user.wake_at.hour, user.wake_at.minute)
        sl = dtime(user.sleep_at.hour, user.sleep_at.minute)
        return not (w <= now.time() <= sl)

    @staticmethod
    def compute_next_nudge(user: User):
        now = HydrationService.user_now(user)
        if HydrationService.within_quiet_hours(user, now):
            # планировать на момент пробуждения
            start_today = now.replace(hour=user.wake_at.hour, minute=user.wake_at.minute, second=0, microsecond=0)
            if now.time() < dtime(user.wake_at.hour, user.wake_at.minute):
                return start_today, None
            return None, None
        consumed = HydrationService.consumed_today_ml(user)
        remaining = user.goal_ml - consumed
        if remaining <= 0:
            return None, None
        # dose: 10–15% цели, clamp 150..350 мл
        dose = max(150, min(350, int(0.12 * user.goal_ml)))
        when = now + timedelta(minutes=90)
        # ускориться при отставании
        end_today = now.replace(hour=user.sleep_at.hour, minute=user.sleep_at.minute, second=0, microsecond=0)
        time_left = max(1, int((end_today - now).total_seconds() // 60))
        ideal_rate = user.goal_ml / max(1, int((end_today - now.replace(hour=user.wake_at.hour, minute=user.wake_at.minute)).total_seconds() // 60))
        current_rate = remaining / time_left
        if current_rate > 1.25 * ideal_rate:
            when = now + timedelta(minutes=45)
        # троттлинг по последнему приёму
        last = HydrationService.last_intake_local(user)
        if last and (now - last) < timedelta(minutes=40):
            when = max(when, last + timedelta(minutes=40))
        return when, dose