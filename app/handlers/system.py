from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config import Config
from app.db.db import Database
from app.keyboards.inline import broadcast_audience_keyboard
from app.keyboards.reply import admin_menu_keyboard, main_menu_keyboard
from app.services.fsm import is_cancel_text, safe_clear_state
from app.services.utils import now_iso

router = Router()
logger = logging.getLogger(__name__)


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


def _user_dict(message: Message) -> dict:
    user = message.from_user
    return {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language_code": user.language_code,
    }


@router.message(CommandStart())
async def system_start(message: Message, state: FSMContext, db: Database, config: Config, content: dict) -> None:
    await safe_clear_state(state, message.from_user, "/start")
    now = now_iso(config.timezone)
    await db.upsert_user(_user_dict(message), now)
    await db.log_event(message.from_user.id, "start", now)
    await db.log_event(message.from_user.id, "menu_open", now)
    text = content.get("start", "Добро пожаловать в Aerodream!")
    if config.site_url:
        text = f"{text}\n\nСайт: {config.site_url}"
    await message.answer(text, reply_markup=main_menu_keyboard())


@router.message(Command("admin"))
async def system_admin(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await message.answer("Доступ запрещен")
        return
    await safe_clear_state(state, message.from_user, "/admin")
    await message.answer("Админ-панель", reply_markup=admin_menu_keyboard())


@router.message(F.text == "📣 Рассылка")
async def system_broadcast_start(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await safe_clear_state(state, message.from_user, "admin broadcast menu action")
    await message.answer("Выберите аудиторию", reply_markup=broadcast_audience_keyboard())


@router.message(Command("cancel"))
@router.message(F.text.func(is_cancel_text))
async def system_cancel(message: Message, state: FSMContext) -> None:
    cleared = await safe_clear_state(state, message.from_user, "cancel action")
    logger.info("FSM action cancelled: user_id=%s cleared=%s", message.from_user.id, cleared)
    await message.answer("Действие отменено", reply_markup=main_menu_keyboard())
