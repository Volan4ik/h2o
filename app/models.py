from __future__ import annotations
from datetime import datetime, time
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tg_id: int = Field(index=True, unique=True)
    tz: str = "UTC"
    units: str = "ml" # ml|oz
    goal_ml: int = 2000
    wake_at: time = time(8, 0)
    sleep_at: time = time(23, 0)
    default_glass_ml: int = 250
    mute_until: Optional[datetime] = None
    smart_on: bool = True

class WaterLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    ts: datetime
    amount_ml: int
    source: str = "manual" # manual|quick|nudge