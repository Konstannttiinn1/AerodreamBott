from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from app.config import Config
from app.db.db import Database
from app.keyboards.reply import admin_menu_keyboard
from app.keyboards.inline import (
    admin_discount_keyboard,
    AutomationCallback,
    automation_keyboard,
    AdminDiscountCallback,
)
from app.services.utils import now_dt

router = Router()


class AdminStates(StatesGroup):
    discount_comment = State()
    automation_t1 = State()
    automation_t2 = State()
    automation_reminder = State()
    automation_offer = State()


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


@router.message(Command("admin"))
async def admin_start(message: Message, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await message.answer("Доступ запрещен")
        return
    await message.answer("Админ-панель", reply_markup=admin_menu_keyboard())


@router.message(F.text == "📊 Статистика")
async def admin_stats(message: Message, db: Database, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    stats = await db.get_stats(now_dt(config.timezone))
    text = (
        "📊 Статистика\n"
        f"Всего пользователей: {stats['total_users']}\n"
        f"Новых за 7 дней: {stats['new_7']}\n"
        f"Активных за 30 дней: {stats['active_30']}\n"
        f"Заблокировано: {stats['blocked']}\n"
        f"Подписаны: {stats['subscribed']}\n"
        f"Открывали цены: {stats['prices_open']}\n"
        f"Запросов скидки: {stats['discount_requests']}"
    )
    await message.answer(text)


@router.message(F.text == "🎁 Запросы на скидку")
async def admin_discount_requests(message: Message, db: Database, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    requests = await db.list_discount_requests("new")
    if not requests:
        await message.answer("Новых заявок нет")
        return
    for req in requests:
        user = await db.get_user(req["user_id"])
        username = user["username"] if user else None
        username_label = f"@{username}" if username else "без username"
        text = (
            "🎁 Запрос на скидку\n"
            f"ID: {req['id']}\n"
            f"Пользователь: {username_label} ({req['user_id']})\n"
            f"Время: {req['created_at']}"
        )
        await message.answer(
            text,
            reply_markup=admin_discount_keyboard(req["id"], username, include_comment=True),
        )


@router.callback_query(AutomationCallback.filter())
async def automation_actions(callback: CallbackQuery, callback_data: AutomationCallback, state: FSMContext, db: Database, config: Config) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("Нет доступа")
        return
    action = callback_data.action
    if action == "toggle":
        current = (await db.get_setting("enable_price_followup")) == "true"
        await db.set_setting("enable_price_followup", "false" if current else "true")
        await callback.answer("Обновлено")
    elif action == "set_t1":
        await state.set_state(AdminStates.automation_t1)
        await callback.message.answer("Введите T1 в часах")
    elif action == "set_t2":
        await state.set_state(AdminStates.automation_t2)
        await callback.message.answer("Введите T2 в часах")
    elif action == "set_reminder":
        await state.set_state(AdminStates.automation_reminder)
        await callback.message.answer("Введите текст напоминания")
    elif action == "set_offer":
        await state.set_state(AdminStates.automation_offer)
        await callback.message.answer("Введите текст предложения")
    try:
        await callback.message.edit_reply_markup(
            reply_markup=automation_keyboard((await db.get_setting("enable_price_followup")) == "true")
        )
    except TelegramBadRequest as exc:
        # Ignore redundant edit when reply markup is unchanged (avoids "message is not modified").
        if "message is not modified" not in str(exc):
            raise
    await callback.answer()


@router.message(F.text == "🤖 Автоматизация")
async def admin_automation(message: Message, db: Database, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    enabled = (await db.get_setting("enable_price_followup")) == "true"
    t1 = await db.get_setting("t1_hours")
    t2 = await db.get_setting("t2_hours")
    reminder = await db.get_setting("reminder_text")
    offer = await db.get_setting("offer_text")
    text = (
        "🤖 Автоматизация\n"
        f"Включено: {'да' if enabled else 'нет'}\n"
        f"T1 (часов): {t1}\n"
        f"T2 (часов): {t2}\n\n"
        f"Напоминание: {reminder}\n\n"
        f"Предложение: {offer}"
    )
    await message.answer(text, reply_markup=automation_keyboard(enabled))


@router.message(F.text == "⚙️ Настройки")
async def admin_settings(message: Message, db: Database, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    enabled = (await db.get_setting("enable_price_followup")) == "true"
    t1 = await db.get_setting("t1_hours")
    t2 = await db.get_setting("t2_hours")
    reminder = await db.get_setting("reminder_text")
    offer = await db.get_setting("offer_text")
    text = (
        "⚙️ Настройки\n"
        f"Rate limit: {config.broadcast_rate_limit} ms\n"
        f"Автоматизация: {'включена' if enabled else 'выключена'}\n"
        f"T1: {t1} ч\n"
        f"T2: {t2} ч\n"
        f"Reminder: {reminder}\n"
        f"Offer: {offer}"
    )
    await message.answer(text)


@router.callback_query(AdminDiscountCallback.filter())
async def admin_discount_actions(
    callback: CallbackQuery,
    callback_data: AdminDiscountCallback,
    state: FSMContext,
    db: Database,
    config: Config,
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("Нет доступа")
        return
    action = callback_data.action
    request_id = callback_data.request_id
    if action == "processed":
        await db.update_discount_status(request_id, "processed")
        await callback.message.answer(f"Заявка {request_id} обработана")
    elif action == "declined":
        await db.update_discount_status(request_id, "declined")
        await callback.message.answer(f"Заявка {request_id} отклонена")
    elif action == "comment":
        await state.set_state(AdminStates.discount_comment)
        await state.update_data(request_id=request_id)
        await callback.message.answer("Введите комментарий к заявке")
    await callback.answer()


@router.message(AdminStates.discount_comment)
async def admin_discount_comment(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await state.clear()
        return
    data = await state.get_data()
    request_id = data.get("request_id")
    await db.update_discount_status(request_id, "processed", comment=message.text)
    await message.answer(f"Комментарий сохранен для заявки {request_id}")
    await state.clear()


@router.message(AdminStates.automation_t1)
async def update_t1(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await state.clear()
        return
    await db.set_setting("t1_hours", message.text.strip())
    await message.answer("T1 обновлен")
    await state.clear()


@router.message(AdminStates.automation_t2)
async def update_t2(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await state.clear()
        return
    await db.set_setting("t2_hours", message.text.strip())
    await message.answer("T2 обновлен")
    await state.clear()


@router.message(AdminStates.automation_reminder)
async def update_reminder(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await state.clear()
        return
    await db.set_setting("reminder_text", message.text)
    await message.answer("Текст напоминания обновлен")
    await state.clear()


@router.message(AdminStates.automation_offer)
async def update_offer(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await state.clear()
        return
    await db.set_setting("offer_text", message.text)
    await message.answer("Текст предложения обновлен")
    await state.clear()
