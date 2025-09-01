from datetime import datetime, timedelta, timezone
from src.shared.models import User

class HydrationService:
    @staticmethod
    def user_now(user: User) -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def to_utc(dt: datetime) -> datetime:
        return dt.astimezone(timezone.utc)

    @staticmethod
    def from_utc(dt: datetime, user: User) -> datetime:
        return dt.astimezone(timezone.utc)

    @staticmethod
    def local_bounds(user: User):
        now = HydrationService.user_now(user)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end