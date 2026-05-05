from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from mccallum_bot.config import Settings
from mccallum_bot.db import (
    clear_next_reminder,
    get_user_prefs,
    schedule_next_reminder,
    set_reminder_enabled,
    set_reminder_interval,
)


def reminder_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="7 дней", callback_data="rem:7"),
                InlineKeyboardButton(text="14 дней", callback_data="rem:14"),
            ],
            [
                InlineKeyboardButton(text="30 дней", callback_data="rem:30"),
                InlineKeyboardButton(text="90 дней", callback_data="rem:90"),
            ],
            [InlineKeyboardButton(text="Выключить напоминания", callback_data="rem:off")],
        ]
    )


async def send_reminder_panel(message: Message, settings: Settings) -> None:
    prefs = await get_user_prefs(settings.db_path, message.from_user.id)
    status = "включены" if prefs["reminder_enabled"] else "выключены"
    days = prefs["reminder_interval_days"]
    await message.answer(
        f"Напоминания сейчас: <b>{status}</b>. Интервал: <b>{days}</b> дн.\n"
        "Выберите новый интервал или выключите:",
        reply_markup=reminder_kb(),
        parse_mode=ParseMode.HTML,
    )


def setup_reminders_router(settings: Settings) -> Router:
    router = Router(name="reminders")

    @router.message(F.text == "Напоминания")
    async def on_reminder_button(message: Message) -> None:
        await send_reminder_panel(message, settings)

    @router.message(Command("reminder"))
    async def cmd_reminder(message: Message) -> None:
        await send_reminder_panel(message, settings)

    @router.callback_query(F.data.startswith("rem:"))
    async def set_reminder(cq: CallbackQuery) -> None:
        uid = cq.from_user.id
        tag = cq.data.split(":", 1)[1]
        if tag == "off":
            await set_reminder_enabled(settings.db_path, uid, False)
            await clear_next_reminder(settings.db_path, uid)
            await cq.message.answer("Напоминания выключены.")
            await cq.answer()
            return
        try:
            days = int(tag)
        except ValueError:
            await cq.answer("Ошибка", show_alert=True)
            return
        await set_reminder_interval(settings.db_path, uid, days)
        await schedule_next_reminder(settings.db_path, uid, days)
        await cq.message.answer(
            f"Интервал напоминаний: <b>{days}</b> дн. Следующее уведомление запланировано.",
            parse_mode=ParseMode.HTML,
        )
        await cq.answer()

    return router
