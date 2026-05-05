from __future__ import annotations

import asyncio
import logging
import time

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from mccallum_bot.config import load_settings
from mccallum_bot.db import (
    clear_next_reminder,
    fetch_due_reminders,
    get_user_prefs,
    init_db,
    schedule_next_reminder,
)
from mccallum_bot.handlers.flow import setup_flow_router
from mccallum_bot.handlers.guide import setup_guide_router
from mccallum_bot.handlers.reminders_ui import setup_reminders_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


async def reminder_tick(bot: Bot, settings) -> None:
    now = time.time()
    due = await fetch_due_reminders(settings.db_path, now)
    for uid in due:
        prefs = await get_user_prefs(settings.db_path, uid)
        if not prefs["reminder_enabled"]:
            await clear_next_reminder(settings.db_path, uid)
            continue
        text = (
            "Пора снова снять замеры и обновить карту пропорций. "
            "Нажми /start в этом чате."
        )
        try:
            await bot.send_message(uid, text)
        except Exception as exc:
            logging.warning("Не удалось отправить напоминание %s: %s", uid, exc)
        await schedule_next_reminder(
            settings.db_path, uid, int(prefs["reminder_interval_days"])
        )


async def main() -> None:
    settings = load_settings()
    await init_db(settings.db_path)

    bot = Bot(
        settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(setup_guide_router())
    dp.include_router(setup_reminders_router(settings))
    dp.include_router(setup_flow_router(settings))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        reminder_tick,
        "interval",
        seconds=60,
        args=[bot, settings],
        id="mccallum_reminders",
        replace_existing=True,
    )
    scheduler.start()

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
