from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    BOT_USERNAME: str | None = None

    DATABASE_URL: str = "sqlite:////data/water.db"
    JOBSTORE_URL: str = "sqlite:////data/jobs.sqlite"


    WEBAPP_URL: str = "https://h2o-back-tutas9.amvera.io/"
    API_BASE: str = "https://h2o-back-tutas9.amvera.io/api"
    ALLOWED_ORIGINS: str | None = None

    INITDATA_TTL: int = 3600
    DEFAULT_TZ: str = "UTC"

    # Dev options
    DEV_ALLOW_NO_INITDATA: bool = True
    DEV_USER_ID: int = 1

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
