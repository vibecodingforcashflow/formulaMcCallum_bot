import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_path: str
    timezone: str


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Установите BOT_TOKEN в .env")

    db_path = os.getenv("DB_PATH", "data/mccallum.sqlite3").strip()
    tz = os.getenv("TZ", "Europe/Moscow").strip()

    return Settings(
        bot_token=token,
        db_path=db_path,
        timezone=tz,
    )
