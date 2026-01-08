from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from app.config import Config
from app.db.db import Database
from app.keyboards.reply import main_menu_keyboard
from app.keyboards.inline import (
    faq_list_keyboard,
    faq_answer_keyboard,
    prices_keyboard,
    DiscountCallback,
    FaqCallback,
    discount_intro_keyboard,
    contacts_keyboard,
    NotifyCallback,
    admin_discount_keyboard,
    section_keyboard,
)
from app.services.utils import now_iso
from app.services.automation import maybe_start_price_flow, stop_price_flow

router = Router()


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
async def start(message: Message, db: Database, config: Config, content: dict) -> None:
    now = now_iso(config.timezone)
    await db.upsert_user(_user_dict(message), now)
    await db.log_event(message.from_user.id, "start", now)
    await db.log_event(message.from_user.id, "menu_open", now)
    text = content.get("start", "Добро пожаловать в Aerodream!")
    if config.site_url:
        text = f"{text}\n\nСайт: {config.site_url}"
    await message.answer(text, reply_markup=main_menu_keyboard())


@router.message(F.text == "🏁 О сервисе")
async def about_service(message: Message, db: Database, config: Config, content: dict) -> None:
    now = now_iso(config.timezone)
    await db.touch_user(message.from_user.id, now)
    text = content.get("about", "")
    if config.site_url:
        text = f"{text}\n\nСайт: {config.site_url}"
    await message.answer(text, reply_markup=section_keyboard(config.admin_tg_url))


@router.message(F.text == "❓ FAQ")
async def faq_section(message: Message, db: Database, config: Config, content: dict) -> None:
    now = now_iso(config.timezone)
    await db.touch_user(message.from_user.id, now)
    await db.log_event(message.from_user.id, "faq_open", now)
    text = content.get("faq_intro", "")
    keyboard = faq_list_keyboard(content.get("faq", []), config.admin_tg_url)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(FaqCallback.filter(F.action == "item"))
async def faq_item(callback: CallbackQuery, callback_data: FaqCallback, config: Config, content: dict, db: Database) -> None:
    now = now_iso(config.timezone)
    await db.touch_user(callback.from_user.id, now)
    faq_items = content.get("faq", [])
    item_id = callback_data.item_id or 1
    if 1 <= item_id <= len(faq_items):
        item = faq_items[item_id - 1]
        text = f"<b>{item['question']}</b>\n\n{item['answer']}"
    else:
        text = "Вопрос не найден."
    await callback.message.edit_text(text, reply_markup=faq_answer_keyboard(config.admin_tg_url), parse_mode="HTML")
    await callback.answer()


@router.callback_query(FaqCallback.filter(F.action.in_({"menu", "list"})))
async def faq_back(callback: CallbackQuery, callback_data: FaqCallback, config: Config, content: dict, db: Database) -> None:
    now = now_iso(config.timezone)
    await db.touch_user(callback.from_user.id, now)
    if callback_data.action == "menu":
        await db.log_event(callback.from_user.id, "menu_open", now)
        await callback.message.answer(content.get("menu_hint", "Главное меню"), reply_markup=main_menu_keyboard())
        await callback.message.delete()
    else:
        text = content.get("faq_intro", "")
        keyboard = faq_list_keyboard(content.get("faq", []), config.admin_tg_url)
        await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.message(F.text == "💳 Цены")
async def prices_section(message: Message, db: Database, config: Config, content: dict) -> None:
    now = now_iso(config.timezone)
    await db.touch_user(message.from_user.id, now)
    await db.log_event(message.from_user.id, "prices_open", now)
    await maybe_start_price_flow(db, message.from_user.id, config.timezone)
    await message.answer(content.get("prices", ""), reply_markup=prices_keyboard(config.admin_tg_url))


@router.callback_query(DiscountCallback.filter(F.action == "intro"))
async def discount_intro(callback: CallbackQuery, config: Config, content: dict, db: Database) -> None:
    now = now_iso(config.timezone)
    await db.touch_user(callback.from_user.id, now)
    text = content.get("discount_intro", "")
    await callback.message.edit_text(text, reply_markup=discount_intro_keyboard())
    await callback.answer()


@router.callback_query(DiscountCallback.filter(F.action == "back_to_prices"))
async def discount_back(callback: CallbackQuery, config: Config, content: dict, db: Database) -> None:
    now = now_iso(config.timezone)
    await db.touch_user(callback.from_user.id, now)
    await callback.message.edit_text(content.get("prices", ""), reply_markup=prices_keyboard(config.admin_tg_url))
    await callback.answer()


@router.callback_query(DiscountCallback.filter(F.action == "request"))
async def discount_request(callback: CallbackQuery, config: Config, content: dict, db: Database) -> None:
    now = now_iso(config.timezone)
    await db.touch_user(callback.from_user.id, now)
    await db.log_event(callback.from_user.id, "discount_request", now)
    await stop_price_flow(db, callback.from_user.id)
    request_id = await db.create_discount_request(callback.from_user.id, now)
    await callback.message.edit_text(content.get("discount_confirm", ""))
    user = callback.from_user
    username = user.username
    username_label = f"@{username}" if username else "без username"
    for admin_id in config.admin_ids:
        text = (
            "🎁 Новый запрос на скидку\n"
            f"Пользователь: {username_label} ({user.id})\n"
            f"Время: {now}\n"
            f"ID запроса: {request_id}"
        )
        await callback.bot.send_message(
            admin_id,
            text,
            reply_markup=admin_discount_keyboard(request_id, username),
        )
    await callback.answer()


@router.message(F.text == "📍 Как добраться")
async def map_section(message: Message, db: Database, config: Config, content: dict) -> None:
    now = now_iso(config.timezone)
    await db.touch_user(message.from_user.id, now)
    await db.log_event(message.from_user.id, "map_open", now)
    text = content.get("map", "")
    if config.map_url:
        text = f"{text}\n\nКарта: {config.map_url}"
    await message.answer(text, reply_markup=section_keyboard(config.admin_tg_url))


@router.message(F.text == "📋 Подготовка / Правила")
async def rules_section(message: Message, db: Database, config: Config, content: dict) -> None:
    now = now_iso(config.timezone)
    await db.touch_user(message.from_user.id, now)
    await message.answer(content.get("rules", ""), reply_markup=section_keyboard(config.admin_tg_url))


@router.message(F.text == "👤 Контакты")
async def contacts_section(message: Message, db: Database, config: Config, content: dict) -> None:
    now = now_iso(config.timezone)
    await db.touch_user(message.from_user.id, now)
    await db.log_event(message.from_user.id, "contact_open", now)
    await stop_price_flow(db, message.from_user.id)
    user_row = await db.get_user(message.from_user.id)
    is_subscribed = True if user_row and user_row["is_subscribed"] == 1 else False
    await message.answer(
        content.get("contacts", ""),
        reply_markup=contacts_keyboard(config.admin_tg_url, is_subscribed),
    )


@router.callback_query(NotifyCallback.filter())
async def toggle_notifications(callback: CallbackQuery, callback_data: NotifyCallback, db: Database, config: Config, content: dict) -> None:
    now = now_iso(config.timezone)
    await db.touch_user(callback.from_user.id, now)
    is_subscribed = callback_data.action == "on"
    await db.set_subscription(callback.from_user.id, is_subscribed)
    user_row = await db.get_user(callback.from_user.id)
    await callback.message.edit_text(
        content.get("contacts", ""),
        reply_markup=contacts_keyboard(config.admin_tg_url, user_row and user_row["is_subscribed"] == 1),
    )
    await callback.answer("Настройки уведомлений обновлены")


@router.message()
async def fallback(message: Message, db: Database, config: Config, content: dict) -> None:
    now = now_iso(config.timezone)
    await db.touch_user(message.from_user.id, now)
    await message.answer(content.get("menu_hint", "Выберите раздел из меню"), reply_markup=main_menu_keyboard())
