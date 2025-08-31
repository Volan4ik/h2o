from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str = "sqlite:///./water.db"
    JOBSTORE_URL: str = "sqlite:///./jobs.sqlite"
    DEFAULT_TZ: str = "UTC"

settings = Settings()