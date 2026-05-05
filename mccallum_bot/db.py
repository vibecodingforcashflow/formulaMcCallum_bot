import json
import time
from pathlib import Path
from typing import Any

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY,
  reminder_interval_days INTEGER NOT NULL DEFAULT 30,
  reminder_enabled INTEGER NOT NULL DEFAULT 1,
  next_reminder_at REAL
);

CREATE TABLE IF NOT EXISTS measurements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  created_at REAL NOT NULL,
  wrist REAL NOT NULL,
  ideal_json TEXT NOT NULL,
  actual_json TEXT NOT NULL,
  landing_token TEXT NOT NULL UNIQUE,
  landing_url TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_measurements_user ON measurements(user_id);
"""


async def migrate_measurements_columns(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute("PRAGMA table_info(measurements)")
        rows = await cur.fetchall()
        cols = {row[1] for row in rows}
        if "working_weights" not in cols:
            await db.execute(
                "ALTER TABLE measurements ADD COLUMN working_weights TEXT"
            )
            await db.commit()


async def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA)
        await db.commit()
    await migrate_measurements_columns(db_path)


async def ensure_user(db_path: str, user_id: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
        )
        await db.commit()


async def get_user_prefs(db_path: str, user_id: int) -> dict[str, Any]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT reminder_interval_days, reminder_enabled, next_reminder_at FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cur.fetchone()
        if not row:
            return {
                "reminder_interval_days": 30,
                "reminder_enabled": True,
                "next_reminder_at": None,
            }
        return {
            "reminder_interval_days": int(row["reminder_interval_days"]),
            "reminder_enabled": bool(row["reminder_enabled"]),
            "next_reminder_at": row["next_reminder_at"],
        }


async def set_reminder_interval(db_path: str, user_id: int, days: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, reminder_interval_days, reminder_enabled)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
              reminder_interval_days = excluded.reminder_interval_days,
              reminder_enabled = 1
            """,
            (user_id, days),
        )
        await db.commit()


async def set_reminder_enabled(db_path: str, user_id: int, enabled: bool) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, reminder_enabled)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET reminder_enabled = excluded.reminder_enabled
            """,
            (user_id, 1 if enabled else 0),
        )
        await db.commit()


async def schedule_next_reminder(db_path: str, user_id: int, interval_days: int) -> None:
    nxt = time.time() + interval_days * 86400.0
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, next_reminder_at, reminder_interval_days, reminder_enabled)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
              next_reminder_at = excluded.next_reminder_at,
              reminder_interval_days = excluded.reminder_interval_days,
              reminder_enabled = 1
            """,
            (user_id, nxt, interval_days),
        )
        await db.commit()


async def clear_next_reminder(db_path: str, user_id: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE users SET next_reminder_at = NULL WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def fetch_due_reminders(db_path: str, now: float) -> list[int]:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            SELECT user_id FROM users
            WHERE reminder_enabled = 1
              AND next_reminder_at IS NOT NULL
              AND next_reminder_at <= ?
            """,
            (now,),
        )
        rows = await cur.fetchall()
        return [int(r[0]) for r in rows]


async def save_measurement(
    db_path: str,
    *,
    user_id: int,
    wrist: float,
    ideal: dict[str, float],
    actual: dict[str, float],
    landing_token: str,
    landing_url: str,
    working_weights: str | None = None,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO measurements (
              user_id, created_at, wrist, ideal_json, actual_json,
              landing_token, landing_url, working_weights
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                time.time(),
                wrist,
                json.dumps(ideal, ensure_ascii=False),
                json.dumps(actual, ensure_ascii=False),
                landing_token,
                landing_url,
                working_weights,
            ),
        )
        await db.commit()


async def get_landing_payload(db_path: str, token: str) -> dict[str, Any] | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT ideal_json, actual_json, working_weights
            FROM measurements WHERE landing_token = ?
            """,
            (token,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        out: dict[str, Any] = {
            "ideal": json.loads(row["ideal_json"]),
            "actual": json.loads(row["actual_json"]),
        }
        ww = row["working_weights"]
        if ww:
            out["working_weights"] = str(ww)
        else:
            out["working_weights"] = None
        return out
