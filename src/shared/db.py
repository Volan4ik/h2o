import os
from sqlmodel import SQLModel, create_engine, Session
from .config import settings

_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args)

# APScheduler jobstore URL берём из env напрямую
jobstore_url = settings.JOBSTORE_URL


def ensure_sqlite_dirs():
    for url in (settings.DATABASE_URL, settings.JOBSTORE_URL):
        if url.startswith("sqlite:///"):
            path = url.removeprefix("sqlite:///")
        elif url.startswith("sqlite:////"):
            path = url.removeprefix("sqlite:////")
        else:
            continue
        d = os.path.dirname(path) or "."
        os.makedirs(d, exist_ok=True)


def init_db():
    ensure_sqlite_dirs()
    SQLModel.metadata.create_all(engine)


def session() -> Session:
    return Session(engine)