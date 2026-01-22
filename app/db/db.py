from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import os

import aiosqlite


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(slots=True)
class Database:
    path: str

    def __post_init__(self) -> None:
        # Normalize database path so it works in Windows and Docker, independent of CWD.
        normalized = os.path.expandvars(self.path)
        posix_hint = normalized.replace("\\", "/")
        raw_path = Path(normalized)
        if os.name == "nt" and posix_hint.startswith("/app/"):
            self.path = str(PROJECT_ROOT / "data" / "bot.db")
        elif raw_path.is_absolute():
            self.path = str(raw_path.expanduser())
        else:
            self.path = str((PROJECT_ROOT / raw_path).expanduser())

    @staticmethod
    def _configure_connection(conn: aiosqlite.Connection) -> None:
        # Ensure Row access by column name.
        conn.row_factory = aiosqlite.Row

    def connect(self) -> aiosqlite.Connection:
        # Create the parent directory so SQLite can create the file.
        db_path = Path(self.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return aiosqlite.connect(db_path)

    async def init(self, enable_automation: bool) -> None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT,
                    first_seen_at TEXT,
                    last_seen_at TEXT,
                    is_subscribed INTEGER DEFAULT 1,
                    is_blocked INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS discount_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    created_at TEXT,
                    status TEXT,
                    comment TEXT
                );
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    created_at TEXT,
                    audience TEXT,
                    text TEXT,
                    sent_count INTEGER,
                    failed_count INTEGER
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE TABLE IF NOT EXISTS user_flows (
                    user_id INTEGER,
                    flow_name TEXT,
                    step INTEGER,
                    triggered_at TEXT,
                    next_run_at TEXT,
                    last_message_at TEXT,
                    finished INTEGER,
                    PRIMARY KEY (user_id, flow_name)
                );
                """
            )
            await conn.commit()
        await self.ensure_settings(enable_automation)

    async def ensure_settings(self, enable_automation: bool) -> None:
        defaults = {
            "enable_price_followup": "true" if enable_automation else "false",
            "t1_hours": "6",
            "t2_hours": "24",
            "reminder_text": "Напоминаем про аэротрубу Aerodream — будем рады ответить на вопросы!",
            "offer_text": "Готовы подарить скидку 10% на первый полет. Нажмите кнопку ниже.",
        }
        async with self.connect() as conn:
            self._configure_connection(conn)
            for key, value in defaults.items():
                await conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value),
                )
            await conn.commit()

    async def upsert_user(self, user: dict, now: str) -> None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            cursor = await conn.execute(
                "SELECT user_id FROM users WHERE user_id = ?",
                (user["user_id"],),
            )
            existing = await cursor.fetchone()
            if existing:
                await conn.execute(
                    """
                    UPDATE users
                    SET username = ?, first_name = ?, last_name = ?, language_code = ?, last_seen_at = ?
                    WHERE user_id = ?
                    """,
                    (
                        user["username"],
                        user["first_name"],
                        user["last_name"],
                        user["language_code"],
                        now,
                        user["user_id"],
                    ),
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO users (user_id, username, first_name, last_name, language_code, first_seen_at, last_seen_at, is_subscribed, is_blocked)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0)
                    """,
                    (
                        user["user_id"],
                        user["username"],
                        user["first_name"],
                        user["last_name"],
                        user["language_code"],
                        now,
                        now,
                    ),
                )
            await conn.commit()

    async def touch_user(self, user_id: int, now: str) -> None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            await conn.execute(
                "UPDATE users SET last_seen_at = ? WHERE user_id = ?",
                (now, user_id),
            )
            await conn.commit()

    async def set_subscription(self, user_id: int, is_subscribed: bool) -> None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            await conn.execute(
                "UPDATE users SET is_subscribed = ? WHERE user_id = ?",
                (1 if is_subscribed else 0, user_id),
            )
            await conn.commit()

    async def set_blocked(self, user_id: int, is_blocked: bool) -> None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            await conn.execute(
                "UPDATE users SET is_blocked = ? WHERE user_id = ?",
                (1 if is_blocked else 0, user_id),
            )
            await conn.commit()

    async def log_event(self, user_id: int, event: str, now: str) -> None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            await conn.execute(
                "INSERT INTO events (user_id, event, created_at) VALUES (?, ?, ?)",
                (user_id, event, now),
            )
            await conn.commit()

    async def create_discount_request(self, user_id: int, now: str) -> int:
        async with self.connect() as conn:
            self._configure_connection(conn)
            cursor = await conn.execute(
                "INSERT INTO discount_requests (user_id, created_at, status) VALUES (?, ?, 'new')",
                (user_id, now),
            )
            await conn.commit()
            return cursor.lastrowid

    async def list_discount_requests(self, status: str = "new") -> list[aiosqlite.Row]:
        async with self.connect() as conn:
            self._configure_connection(conn)
            cursor = await conn.execute(
                "SELECT * FROM discount_requests WHERE status = ? ORDER BY created_at DESC",
                (status,),
            )
            return await cursor.fetchall()

    async def update_discount_status(self, request_id: int, status: str, comment: str | None = None) -> None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            await conn.execute(
                "UPDATE discount_requests SET status = ?, comment = ? WHERE id = ?",
                (status, comment, request_id),
            )
            await conn.commit()

    async def create_broadcast(self, admin_id: int, audience: str, text: str, now: str) -> int:
        async with self.connect() as conn:
            self._configure_connection(conn)
            cursor = await conn.execute(
                "INSERT INTO broadcasts (admin_id, created_at, audience, text, sent_count, failed_count) VALUES (?, ?, ?, ?, 0, 0)",
                (admin_id, now, audience, text),
            )
            await conn.commit()
            return cursor.lastrowid

    async def update_broadcast_counts(self, broadcast_id: int, sent: int, failed: int) -> None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            await conn.execute(
                "UPDATE broadcasts SET sent_count = ?, failed_count = ? WHERE id = ?",
                (sent, failed, broadcast_id),
            )
            await conn.commit()

    async def get_stats(self, now: datetime) -> dict:
        async with self.connect() as conn:
            self._configure_connection(conn)
            cursor = await conn.execute("SELECT COUNT(*) AS value FROM users")
            total_users = await cursor.fetchone()
            cursor = await conn.execute(
                "SELECT COUNT(*) AS value FROM users WHERE first_seen_at >= ?",
                ((now - timedelta(days=7)).isoformat(),),
            )
            new_7 = await cursor.fetchone()
            cursor = await conn.execute(
                "SELECT COUNT(*) AS value FROM users WHERE last_seen_at >= ?",
                ((now - timedelta(days=30)).isoformat(),),
            )
            active_30 = await cursor.fetchone()
            cursor = await conn.execute(
                "SELECT COUNT(*) AS value FROM users WHERE is_blocked = 1",
            )
            blocked = await cursor.fetchone()
            cursor = await conn.execute(
                "SELECT COUNT(*) AS value FROM users WHERE is_subscribed = 1",
            )
            subscribed = await cursor.fetchone()
            cursor = await conn.execute(
                "SELECT COUNT(*) AS value FROM events WHERE event = 'prices_open'",
            )
            prices_open = await cursor.fetchone()
            cursor = await conn.execute(
                "SELECT COUNT(*) AS value FROM discount_requests",
            )
            discount_requests = await cursor.fetchone()
            return {
                "total_users": total_users["value"],
                "new_7": new_7["value"],
                "active_30": active_30["value"],
                "blocked": blocked["value"],
                "subscribed": subscribed["value"],
                "prices_open": prices_open["value"],
                "discount_requests": discount_requests["value"],
            }

    async def get_setting(self, key: str) -> str | None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            cursor = await conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = await cursor.fetchone()
            if row:
                return row["value"]
            return None

    async def set_setting(self, key: str, value: str) -> None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            await conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            await conn.commit()

    async def get_broadcast_recipients(self, audience: dict) -> list[int]:
        query = "SELECT user_id FROM users WHERE is_blocked = 0 AND is_subscribed = 1"
        params: list = []
        if audience.get("type") == "test":
            query = "SELECT user_id FROM users WHERE user_id IN ({})".format(
                ",".join("?" for _ in audience.get("admin_ids", []))
            )
            params = list(audience.get("admin_ids", []))
        elif audience.get("type") == "active":
            query += " AND last_seen_at >= ?"
            params.append(audience["since"])
        elif audience.get("type") == "inactive":
            query += " AND last_seen_at < ?"
            params.append(audience["before"])
        async with self.connect() as conn:
            self._configure_connection(conn)
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [row["user_id"] for row in rows]

    async def upsert_user_flow(
        self,
        user_id: int,
        flow_name: str,
        step: int,
        triggered_at: str,
        next_run_at: str,
        last_message_at: str | None,
        finished: bool,
    ) -> None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            await conn.execute(
                """
                INSERT INTO user_flows (user_id, flow_name, step, triggered_at, next_run_at, last_message_at, finished)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, flow_name)
                DO UPDATE SET step = excluded.step, triggered_at = excluded.triggered_at,
                next_run_at = excluded.next_run_at, last_message_at = excluded.last_message_at, finished = excluded.finished
                """,
                (user_id, flow_name, step, triggered_at, next_run_at, last_message_at, 1 if finished else 0),
            )
            await conn.commit()

    async def get_flow(self, user_id: int, flow_name: str) -> aiosqlite.Row | None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            cursor = await conn.execute(
                "SELECT * FROM user_flows WHERE user_id = ? AND flow_name = ?",
                (user_id, flow_name),
            )
            return await cursor.fetchone()

    async def get_due_flows(self, flow_name: str, now: str) -> list[aiosqlite.Row]:
        async with self.connect() as conn:
            self._configure_connection(conn)
            cursor = await conn.execute(
                """
                SELECT * FROM user_flows
                WHERE flow_name = ? AND finished = 0 AND next_run_at <= ?
                """,
                (flow_name, now),
            )
            return await cursor.fetchall()

    async def finish_flow(self, user_id: int, flow_name: str) -> None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            await conn.execute(
                "UPDATE user_flows SET finished = 1 WHERE user_id = ? AND flow_name = ?",
                (user_id, flow_name),
            )
            await conn.commit()

    async def get_user(self, user_id: int) -> aiosqlite.Row | None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            cursor = await conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return await cursor.fetchone()

    async def get_flow_cooldown(self, user_id: int, flow_name: str) -> aiosqlite.Row | None:
        async with self.connect() as conn:
            self._configure_connection(conn)
            cursor = await conn.execute(
                "SELECT * FROM user_flows WHERE user_id = ? AND flow_name = ?",
                (user_id, flow_name),
            )
            return await cursor.fetchone()
