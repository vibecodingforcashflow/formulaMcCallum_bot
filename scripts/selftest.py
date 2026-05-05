#!/usr/bin/env python3
"""Локальная проверка формул, БД и генерации PDF без Telegram."""

import asyncio
import os
import tempfile
from pathlib import Path

os.environ.setdefault("BOT_TOKEN", "123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")

from mccallum_bot.config import load_settings
from mccallum_bot.db import get_landing_payload, init_db, save_measurement
from mccallum_bot.formulas import ORDER, color_class, ideals_from_wrist, pct_of_ideal
from mccallum_bot.pdf_report import build_measurement_rows, render_mccallum_report_png


def test_formulas() -> None:
    i = ideals_from_wrist(17.0)
    assert abs(i.chest - 110.5) < 0.02
    raw_c = 6.5 * 17.0
    assert abs(i.waist - round(raw_c * 0.70 + 1e-9, 1)) < 0.02
    assert abs(i.thigh - round(raw_c * 0.53 + 1e-9, 1)) < 0.02
    assert color_class("waist", i.waist, i.waist) == "good"
    assert color_class("waist", i.waist + 1, i.waist) == "bad"
    assert color_class("biceps", i.biceps - 1, i.biceps) == "bad"
    assert pct_of_ideal(35.0, 40.0) == 87.5
    print("formulas OK")


async def test_db_and_pdf() -> None:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "t.sqlite3"
        os.environ["DB_PATH"] = str(db)
        await init_db(str(db))

        settings = load_settings()
        ideal = ideals_from_wrist(17.0)
        ideal_map = {
            "chest": ideal.chest,
            "waist": ideal.waist,
            "thigh": ideal.thigh,
            "neck": ideal.neck,
            "biceps": ideal.biceps,
            "calf": ideal.calf,
            "forearm": ideal.forearm,
        }
        actual = {k: ideal_map[k] * 0.95 for k in ORDER}
        token = "x" * 64
        await save_measurement(
            settings.db_path,
            user_id=1,
            wrist=17.0,
            ideal=ideal_map,
            actual=actual,
            landing_token=token,
            landing_url="",
        )
        row = await get_landing_payload(settings.db_path, token)
        assert row is not None
        assert row.get("working_weights") is None

        png = render_mccallum_report_png(ideal=ideal_map, actual=actual)
        assert png.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(png) > 50_000
        rows = build_measurement_rows(ideal_map, actual)
        assert rows[0]["name"] == "Грудь"
        print("db + PNG OK")


def main() -> None:
    test_formulas()
    asyncio.run(test_db_and_pdf())
    print("All selftests passed.")


if __name__ == "__main__":
    main()
