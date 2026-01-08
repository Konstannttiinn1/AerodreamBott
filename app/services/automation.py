from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from aiogram import Bot

from app.db.db import Database
from app.keyboards.inline import DiscountCallback
from app.services.utils import now_dt
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


FLOW_NAME = "price_followup"
COOLDOWN_HOURS = 24


def _get_discount_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Получить скидку 10%", callback_data=DiscountCallback(action="intro").pack())]
        ]
    )


async def maybe_start_price_flow(db: Database, user_id: int, timezone: str) -> None:
    enabled = (await db.get_setting("enable_price_followup")) == "true"
    if not enabled:
        return
    now = now_dt(timezone)
    existing = await db.get_flow_cooldown(user_id, FLOW_NAME)
    if existing:
        if existing["finished"] == 0:
            return
        last_message = existing["last_message_at"]
        if last_message:
            last_dt = datetime.fromisoformat(last_message)
            if now - last_dt < timedelta(hours=COOLDOWN_HOURS):
                return
    t1_hours = int((await db.get_setting("t1_hours")) or 6)
    next_run = now + timedelta(hours=t1_hours)
    await db.upsert_user_flow(
        user_id=user_id,
        flow_name=FLOW_NAME,
        step=1,
        triggered_at=now.isoformat(),
        next_run_at=next_run.isoformat(),
        last_message_at=None,
        finished=False,
    )


async def stop_price_flow(db: Database, user_id: int) -> None:
    await db.finish_flow(user_id, FLOW_NAME)


async def automation_loop(bot: Bot, db: Database, timezone: str) -> None:
    while True:
        enabled = (await db.get_setting("enable_price_followup")) == "true"
        if enabled:
            now = now_dt(timezone)
            flows = await db.get_due_flows(FLOW_NAME, now.isoformat())
            for flow in flows:
                user = await db.get_user(flow["user_id"])
                if not user or user["is_blocked"] == 1:
                    await db.finish_flow(flow["user_id"], FLOW_NAME)
                    continue
                if user["is_subscribed"] != 1:
                    await db.finish_flow(flow["user_id"], FLOW_NAME)
                    continue
                step = flow["step"]
                if step == 1:
                    reminder_text = (await db.get_setting("reminder_text")) or ""
                    await bot.send_message(user["user_id"], reminder_text)
                    t2_hours = int((await db.get_setting("t2_hours")) or 24)
                    next_run = now + timedelta(hours=t2_hours)
                    await db.upsert_user_flow(
                        user_id=user["user_id"],
                        flow_name=FLOW_NAME,
                        step=2,
                        triggered_at=flow["triggered_at"],
                        next_run_at=next_run.isoformat(),
                        last_message_at=now.isoformat(),
                        finished=False,
                    )
                elif step == 2:
                    offer_text = (await db.get_setting("offer_text")) or ""
                    await bot.send_message(user["user_id"], offer_text, reply_markup=_get_discount_keyboard())
                    await db.upsert_user_flow(
                        user_id=user["user_id"],
                        flow_name=FLOW_NAME,
                        step=2,
                        triggered_at=flow["triggered_at"],
                        next_run_at=now.isoformat(),
                        last_message_at=now.isoformat(),
                        finished=True,
                    )
        await asyncio.sleep(300)
