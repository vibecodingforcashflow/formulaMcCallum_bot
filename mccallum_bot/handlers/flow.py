import logging
import secrets
from typing import Any

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from mccallum_bot.config import Settings
from mccallum_bot.db import (
    ensure_user,
    get_user_prefs,
    save_measurement,
    schedule_next_reminder,
)
from mccallum_bot.formulas import LABEL_RU, ORDER, IdealSet, ideals_from_wrist
from mccallum_bot.parsing import parse_cm, parse_wrist
from mccallum_bot.pdf_report import render_mccallum_report_png
from mccallum_bot.states import McCallumFlow

START_BUTTON_TEXT = "Всё дело в запястье"

ASK_PROMPTS: dict[str, str] = {
    "chest": "Введите **обхват груди** в сантиметрах (например, `102` или `102,5`):",
    "waist": "Введите **обхват талии** в сантиметрах:",
    "thigh": "Введите **обхват бедра** в сантиметрах:",
    "neck": "Введите **обхват шеи** в сантиметрах:",
    "biceps": "Введите **обхват бицепса** в сантиметрах:",
    "calf": "Введите **обхват голени** в сантиметрах:",
    "forearm": "Введите **обхват предплечья** в сантиметрах:",
}


def main_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=START_BUTTON_TEXT)],
            [
                KeyboardButton(text="Замеры"),
                KeyboardButton(text="Напоминания"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Введите число в см…",
    )


def ideals_to_dict(i: IdealSet) -> dict[str, float]:
    return {
        "chest": i.chest,
        "waist": i.waist,
        "thigh": i.thigh,
        "neck": i.neck,
        "biceps": i.biceps,
        "calf": i.calf,
        "forearm": i.forearm,
    }


def fix_kb(show: bool) -> InlineKeyboardMarkup | None:
    if not show:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Исправить предыдущий замер",
                    callback_data="flow:fix",
                )
            ]
        ]
    )


def setup_flow_router(settings: Settings) -> Router:
    router = Router(name="flow")

    async def finalize_session(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        ideals: dict[str, float] = dict(data.get("ideals") or {})
        actual_raw: dict[str, Any] = dict(data.get("actual") or {})
        wrist = float(data["wrist"])
        token = secrets.token_urlsafe(48)
        actual_f = {k: float(actual_raw[k]) for k in ORDER}
        await save_measurement(
            settings.db_path,
            user_id=message.from_user.id,
            wrist=wrist,
            ideal=ideals,
            actual=actual_f,
            landing_token=token,
            landing_url="",
            working_weights=None,
        )
        prefs = await get_user_prefs(settings.db_path, message.from_user.id)
        if prefs["reminder_enabled"]:
            await schedule_next_reminder(
                settings.db_path,
                message.from_user.id,
                int(prefs["reminder_interval_days"]),
            )
        await state.clear()
        try:
            png_bytes = render_mccallum_report_png(ideal=ideals, actual=actual_f)
        except Exception:
            logging.exception("Не удалось сформировать изображение отчёта")
            await message.answer(
                "Замеры сохранены, но не получилось сформировать картинку отчёта. "
                "Проверьте WeasyPrint, PyMuPDF и системные зависимости (см. README). "
                "Напишите /start для нового цикла.",
                reply_markup=main_reply_kb(),
            )
            return
        photo = BufferedInputFile(png_bytes, filename="mccallum_proportions.png")
        await message.answer_photo(
            photo=photo,
            caption=(
                "Готово! Карта пропорций: формулы, схема и таблица «Ваши замеры». "
                "Напоминание о следующем замере придёт согласно настройкам."
            ),
            reply_markup=main_reply_kb(),
        )

    async def run_start(message: Message, state: FSMContext) -> None:
        await ensure_user(settings.db_path, message.from_user.id)
        await state.set_state(McCallumFlow.waiting_wrist)
        await state.set_data({"actual": {}, "step": 0})
        await message.answer(
            "Привет, культурист!\n\n"
            "Формула МакКаллума даёт нам представление об идеальных гармоничных пропорциях тела культуриста. "
            "Параметры, полученные по этой формуле, вполне реально достигнуть натурально и при данных пропорциях твоё тело будет выглядеть крепким и атлетичным. "
            "Многие из вас обязательно смогут превысить эти показатели, но прежде чем думать о большем, нужно, по крайней мере, приблизиться к ним. "
            "А дальше вы уже сами будете знать, что делать и на что ориентироваться.\n\n"
            "Не забывай, что процент жира должен быть 10% чтобы был виден пресс, была хорошая сепарация мышц, "
            "талия визуально узкая, грудь и плечи доминировали.\n\n"
            "Чтобы посчитать твои обхваты по формуле Маккаллума, напиши обхват запястья в сантиметрах (например: 17 или 17,5).\n\n"
            "Меряют запястье горизонтально в самом узком месте над косточкой.",
            reply_markup=main_reply_kb(),
            parse_mode=ParseMode.MARKDOWN,
        )

    @router.message(Command("start"))
    async def cmd_start(message: Message, state: FSMContext) -> None:
        await run_start(message, state)

    # Сразу после /start: тот же сценарий из любого состояния (до обработчиков с StateFilter).
    @router.message(F.text == START_BUTTON_TEXT)
    async def cmd_start_button(message: Message, state: FSMContext) -> None:
        await run_start(message, state)

    @router.message(StateFilter(McCallumFlow.waiting_wrist), F.text)
    async def on_wrist(message: Message, state: FSMContext) -> None:
        if message.text in {"Замеры", "Напоминания"}:
            return
        w = parse_wrist(message.text or "")
        if w is None:
            await message.answer(
                "Не получилось распознать число. Обхват запястья обычно **12–28 см**. "
                "Попробуй ещё раз, например: `17` или `17,5`.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        ideals = ideals_from_wrist(w)
        ideal_map = ideals_to_dict(ideals)
        lines = "\n".join(f"• **{LABEL_RU[k]}**: `{ideal_map[k]}` см" for k in ORDER)
        await message.answer(
            f"Запястье: `{w}` см.\n\n"
            f"Твои расчётные идеальные обхваты:\n{lines}\n\n"
            "Дальше по очереди введи **фактические** замеры — по одному сообщению.",
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.update_data(
            wrist=w,
            ideals=ideal_map,
            actual={},
            step=0,
        )
        await state.set_state(McCallumFlow.collecting)
        await message.answer(
            ASK_PROMPTS["chest"],
            reply_markup=fix_kb(False),
            parse_mode=ParseMode.MARKDOWN,
        )

    @router.callback_query(StateFilter(McCallumFlow.collecting), F.data == "flow:fix")
    async def fix_last(cq: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        step = int(data.get("step", 0))
        actual: dict[str, float] = dict(data.get("actual") or {})
        if step <= 0:
            await cq.answer("Пока нечего исправлять.", show_alert=True)
            return
        prev_key = ORDER[step - 1]
        actual.pop(prev_key, None)
        await state.update_data(actual=actual, step=step - 1)
        key = ORDER[step - 1]
        await cq.message.answer(
            ASK_PROMPTS[key],
            reply_markup=fix_kb(step - 1 > 0),
            parse_mode=ParseMode.MARKDOWN,
        )
        await cq.answer()

    @router.message(StateFilter(McCallumFlow.collecting), F.text)
    async def on_measurement(message: Message, state: FSMContext) -> None:
        if message.text in {"Замеры", "Напоминания"}:
            return
        data = await state.get_data()
        step = int(data.get("step", 0))
        actual: dict[str, Any] = dict(data.get("actual") or {})
        ideals: dict[str, float] = dict(data.get("ideals") or {})

        if step >= len(ORDER):
            await message.answer("Цикл уже завершён. Нажми /start чтобы заново.")
            return

        key = ORDER[step]
        val = parse_cm(message.text or "")
        if val is None:
            await message.answer(
                "Нужно число в сантиметрах, например `95` или `95,5`. Попробуй ещё раз.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        actual[key] = val
        next_step = step + 1
        await state.update_data(actual=actual, step=next_step)

        if next_step >= len(ORDER):
            await finalize_session(message, state)
            return

        next_key = ORDER[next_step]
        await message.answer(
            ASK_PROMPTS[next_key],
            reply_markup=fix_kb(True),
            parse_mode=ParseMode.MARKDOWN,
        )

    return router
