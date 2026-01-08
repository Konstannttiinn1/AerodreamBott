from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class FaqCallback(CallbackData, prefix="faq"):
    action: str
    item_id: int | None = None


class DiscountCallback(CallbackData, prefix="discount"):
    action: str
    request_id: int | None = None


class AdminDiscountCallback(CallbackData, prefix="admin_discount"):
    action: str
    request_id: int


class NotifyCallback(CallbackData, prefix="notify"):
    action: str


class AutomationCallback(CallbackData, prefix="automation"):
    action: str


class BroadcastCallback(CallbackData, prefix="broadcast"):
    action: str


def section_keyboard(admin_url: str, back_action: str = "menu") -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=FaqCallback(action=back_action).pack())],
        [InlineKeyboardButton(text="👤 Связаться с администратором", url=admin_url)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def faq_list_keyboard(faq_items: list[dict], admin_url: str) -> InlineKeyboardMarkup:
    rows = []
    for idx, item in enumerate(faq_items, start=1):
        rows.append(
            [InlineKeyboardButton(text=item["question"], callback_data=FaqCallback(action="item", item_id=idx).pack())]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=FaqCallback(action="menu").pack())])
    rows.append([InlineKeyboardButton(text="👤 Связаться с администратором", url=admin_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def faq_answer_keyboard(admin_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к FAQ", callback_data=FaqCallback(action="list").pack())],
            [InlineKeyboardButton(text="👤 Связаться с администратором", url=admin_url)],
        ]
    )


def prices_keyboard(admin_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Получить скидку 10%", callback_data=DiscountCallback(action="intro").pack())],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=FaqCallback(action="menu").pack())],
            [InlineKeyboardButton(text="👤 Связаться с администратором", url=admin_url)],
        ]
    )


def discount_intro_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Запросить скидку 10%", callback_data=DiscountCallback(action="request").pack())],
            [InlineKeyboardButton(text="⬅️ Назад к ценам", callback_data=DiscountCallback(action="back_to_prices").pack())],
        ]
    )


def contacts_keyboard(admin_url: str, is_subscribed: bool) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="👤 Связаться с администратором", url=admin_url)],
        [
            InlineKeyboardButton(
                text="✅ Получать уведомления" if not is_subscribed else "🚫 Не получать уведомления",
                callback_data=NotifyCallback(action="on" if not is_subscribed else "off").pack(),
            )
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=FaqCallback(action="menu").pack())],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_discount_keyboard(request_id: int, user_username: str | None, include_comment: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="✅ Отметить обработано", callback_data=AdminDiscountCallback(action="processed", request_id=request_id).pack())],
        [InlineKeyboardButton(text="🚫 Отклонить", callback_data=AdminDiscountCallback(action="declined", request_id=request_id).pack())],
    ]
    if user_username:
        buttons.insert(1, [InlineKeyboardButton(text="✍️ Написать пользователю", url=f"https://t.me/{user_username}")])
    if include_comment:
        buttons.append([InlineKeyboardButton(text="💬 Комментарий", callback_data=AdminDiscountCallback(action="comment", request_id=request_id).pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def automation_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{'🟢' if enabled else '⚪️'} Переключить", callback_data=AutomationCallback(action="toggle").pack())],
            [InlineKeyboardButton(text="🕒 Изменить T1 (часов)", callback_data=AutomationCallback(action="set_t1").pack())],
            [InlineKeyboardButton(text="🕒 Изменить T2 (часов)", callback_data=AutomationCallback(action="set_t2").pack())],
            [InlineKeyboardButton(text="✏️ Текст напоминания", callback_data=AutomationCallback(action="set_reminder").pack())],
            [InlineKeyboardButton(text="✏️ Текст предложения", callback_data=AutomationCallback(action="set_offer").pack())],
        ]
    )


def broadcast_audience_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Тест (только админам)", callback_data=BroadcastCallback(action="audience_test").pack())],
            [InlineKeyboardButton(text="Всем подписанным", callback_data=BroadcastCallback(action="audience_all").pack())],
            [InlineKeyboardButton(text="Сегмент", callback_data=BroadcastCallback(action="audience_segment").pack())],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=BroadcastCallback(action="cancel").pack())],
        ]
    )


def broadcast_segment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Активные за N дней", callback_data=BroadcastCallback(action="segment_active").pack())],
            [InlineKeyboardButton(text="Неактивные за N дней", callback_data=BroadcastCallback(action="segment_inactive").pack())],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=BroadcastCallback(action="back_to_audience").pack())],
        ]
    )


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить", callback_data=BroadcastCallback(action="confirm").pack())],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=BroadcastCallback(action="cancel").pack())],
        ]
    )
