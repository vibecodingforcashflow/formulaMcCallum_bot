import html
import re

import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from mccallum_bot.formulas import LABEL_RU, MeasurementKey
from mccallum_bot.guide_content import GUIDE


def _line_with_bold(line: str) -> str:
    esc = html.escape(line)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc)


def _guide_html(text: str) -> str:
    parts: list[str] = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        lines = [_line_with_bold(L) for L in block.split("\n")]
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def guide_main_kb() -> InlineKeyboardMarkup:
    keys: list[MeasurementKey] = [
        "chest",
        "waist",
        "thigh",
        "neck",
        "biceps",
        "calf",
        "forearm",
    ]
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for i, k in enumerate(keys, start=1):
        row.append(
            InlineKeyboardButton(text=LABEL_RU[k], callback_data=f"guide:{k}")
        )
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def setup_guide_router() -> Router:
    router = Router(name="guide")

    @router.message(F.text == "Замеры")
    async def open_guide_menu(message: Message) -> None:
        await message.answer(
            "Выберите зону замера — пришлю **только текст** методики (без картинок).\n"
            "Нажмите кнопку с названием зоны:",
            reply_markup=guide_main_kb(),
            parse_mode=ParseMode.MARKDOWN,
        )

    @router.callback_query(F.data.startswith("guide:"))
    async def send_guide(cq: CallbackQuery) -> None:
        key = (cq.data or "").split(":", 1)[1] if cq.data else ""
        if key not in GUIDE:
            await cq.answer("Неизвестный раздел", show_alert=True)
            return
        body = _guide_html(GUIDE[key])
        try:
            if cq.message:
                if len(body) <= 4096:
                    await cq.message.answer(body, parse_mode=ParseMode.HTML)
                else:
                    await cq.message.answer(body[:4096], parse_mode=ParseMode.HTML)
                    await cq.message.answer(body[4096:], parse_mode=ParseMode.HTML)
            else:
                if len(body) <= 4096:
                    await cq.bot.send_message(
                        cq.from_user.id, body, parse_mode=ParseMode.HTML
                    )
                else:
                    await cq.bot.send_message(
                        cq.from_user.id, body[:4096], parse_mode=ParseMode.HTML
                    )
                    await cq.bot.send_message(
                        cq.from_user.id, body[4096:], parse_mode=ParseMode.HTML
                    )
        except Exception:
            logging.exception("guide: не удалось отправить текст зоны %s", key)
            await cq.answer("Не удалось отправить текст. Попробуйте ещё раз.", show_alert=True)
            return
        await cq.answer()

    return router
