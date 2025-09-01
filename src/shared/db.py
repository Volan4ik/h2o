from sqlmodel import SQLModel, create_engine, Session
from src.shared.config import settings
import os

# Ensure SQLite directory exists when using file-based sqlite path
if settings.DATABASE_URL.startswith("sqlite"):
    # Extract path part after sqlite:/// or sqlite:////
    db_path = settings.DATABASE_URL.split("sqlite:///")[-1]
    dir_path = os.path.dirname(db_path) or "."
    os.makedirs(dir_path, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

def session():
    return Session(engine)