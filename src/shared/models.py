from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tg_id: int = Field(index=True, unique=True)
    goal_ml: int = Field(default=2000)
    default_glass_ml: int = Field(default=250)

    logs: list["WaterLog"] = Relationship(back_populates="user")

class WaterLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    ts_utc: datetime
    amount_ml: int
    source: str

    user: Optional[User] = Relationship(back_populates="logs")
