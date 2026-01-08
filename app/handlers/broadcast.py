from __future__ import annotations

import asyncio
from datetime import timedelta

from aiogram import Router, F
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from app.config import Config
from app.db.db import Database
from app.keyboards.inline import (
    BroadcastCallback,
    broadcast_audience_keyboard,
    broadcast_confirm_keyboard,
    broadcast_segment_keyboard,
)
from app.services.utils import now_dt

router = Router()


class BroadcastState(StatesGroup):
    audience = State()
    segment_days = State()
    text = State()
    preview = State()


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


@router.message(F.text == "📣 Рассылка")
async def broadcast_start(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await state.clear()
    await message.answer("Выберите аудиторию", reply_markup=broadcast_audience_keyboard())


@router.callback_query(BroadcastCallback.filter(F.action == "cancel"))
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not _is_admin(callback.from_user.id, config):
        return
    await state.clear()
    await callback.message.edit_text("Рассылка отменена")
    await callback.answer()


@router.callback_query(BroadcastCallback.filter(F.action == "audience_test"))
async def broadcast_audience_test(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not _is_admin(callback.from_user.id, config):
        return
    await state.update_data(audience={"type": "test", "admin_ids": list(config.admin_ids)})
    await state.set_state(BroadcastState.text)
    await callback.message.edit_text("Введите текст рассылки (HTML поддерживается)")
    await callback.answer()


@router.callback_query(BroadcastCallback.filter(F.action == "audience_all"))
async def broadcast_audience_all(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not _is_admin(callback.from_user.id, config):
        return
    await state.update_data(audience={"type": "all"})
    await state.set_state(BroadcastState.text)
    await callback.message.edit_text("Введите текст рассылки (HTML поддерживается)")
    await callback.answer()


@router.callback_query(BroadcastCallback.filter(F.action == "audience_segment"))
async def broadcast_audience_segment(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not _is_admin(callback.from_user.id, config):
        return
    await state.set_state(BroadcastState.audience)
    await callback.message.edit_text("Выберите сегмент", reply_markup=broadcast_segment_keyboard())
    await callback.answer()


@router.callback_query(BroadcastCallback.filter(F.action == "back_to_audience"))
async def broadcast_back_audience(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not _is_admin(callback.from_user.id, config):
        return
    await state.clear()
    await callback.message.edit_text("Выберите аудиторию", reply_markup=broadcast_audience_keyboard())
    await callback.answer()


@router.callback_query(BroadcastCallback.filter(F.action.in_({"segment_active", "segment_inactive"})))
async def broadcast_segment_type(callback: CallbackQuery, state: FSMContext, callback_data: BroadcastCallback, config: Config) -> None:
    if not _is_admin(callback.from_user.id, config):
        return
    await state.update_data(segment_type=callback_data.action)
    await state.set_state(BroadcastState.segment_days)
    await callback.message.edit_text("Введите число дней для сегмента")
    await callback.answer()


@router.message(BroadcastState.segment_days)
async def broadcast_segment_days(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await state.clear()
        return
    try:
        days = int(message.text.strip())
    except ValueError:
        await message.answer("Введите число дней (целое значение)")
        return
    data = await state.get_data()
    segment_type = data.get("segment_type")
    now = now_dt(config.timezone)
    if segment_type == "segment_active":
        audience = {"type": "active", "since": (now - timedelta(days=days)).isoformat()}
    else:
        audience = {"type": "inactive", "before": (now - timedelta(days=days)).isoformat()}
    await state.update_data(audience=audience)
    await state.set_state(BroadcastState.text)
    await message.answer("Введите текст рассылки (HTML поддерживается)")


@router.message(BroadcastState.text)
async def broadcast_text(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await state.clear()
        return
    await state.update_data(text=message.html_text)
    await state.set_state(BroadcastState.preview)
    await message.answer("Превью:")
    await message.answer(message.html_text, parse_mode="HTML", reply_markup=broadcast_confirm_keyboard())


@router.callback_query(BroadcastCallback.filter(F.action == "confirm"))
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not _is_admin(callback.from_user.id, config):
        return
    data = await state.get_data()
    audience = data.get("audience")
    text = data.get("text")
    now = now_dt(config.timezone)
    broadcast_id = await db.create_broadcast(callback.from_user.id, str(audience), text, now.isoformat())
    if audience.get("type") == "test":
        recipients = list(config.admin_ids)
    else:
        recipients = await db.get_broadcast_recipients(audience)
    sent = 0
    failed = 0
    for user_id in recipients:
        try:
            await callback.bot.send_message(user_id, text, parse_mode="HTML")
            sent += 1
        except TelegramForbiddenError:
            failed += 1
            await db.set_blocked(user_id, True)
        except Exception:
            failed += 1
        await asyncio.sleep(config.broadcast_rate_limit / 1000)
    await db.update_broadcast_counts(broadcast_id, sent, failed)
    await callback.message.answer(f"Рассылка завершена. Отправлено: {sent}, ошибок: {failed}")
    await state.clear()
    await callback.answer()
