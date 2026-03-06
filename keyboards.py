from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def get_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏗️ Конструктор заказа", callback_data="main_constructor")
    builder.button(text="🔥 Акции и скидки", callback_data="main_promos")
    builder.button(text="📍 Контакты", callback_data="main_contacts")
    builder.button(text="📂 Макеты и требования", callback_data="main_docs")
    builder.button(text="👤 Личный Кабинет", callback_data="main_profile")
    builder.adjust(2)
    return builder.as_markup()
