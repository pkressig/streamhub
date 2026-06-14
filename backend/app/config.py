from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://pascalhub:pascalhub@postgres:5432/pascalhub"
    REDIS_URL: str = "redis://redis:6379/0"
    SECRET_KEY: str = "changeme-in-production"

    class Config:
        env_file = ".env"

settings = Settings()
