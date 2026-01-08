from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏁 О сервисе"), KeyboardButton(text="❓ FAQ")],
            [KeyboardButton(text="💳 Цены"), KeyboardButton(text="📍 Как добраться")],
            [KeyboardButton(text="📋 Подготовка / Правила"), KeyboardButton(text="👤 Контакты")],
        ],
        resize_keyboard=True,
    )


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📣 Рассылка")],
            [KeyboardButton(text="🎁 Запросы на скидку"), KeyboardButton(text="🤖 Автоматизация")],
            [KeyboardButton(text="⚙️ Настройки")],
        ],
        resize_keyboard=True,
    )
