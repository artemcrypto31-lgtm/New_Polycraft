from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import Database
from models import Order
from datetime import datetime

router = Router()

class OrderConstructor(StatesGroup):
    waiting_for_category = State()
    waiting_for_params = State()
    waiting_for_description = State()
    waiting_for_files = State()

# --- ТЕКСТЫ ---

TEXT_CATALOG_ROOT = (
    "🏗 <b>Мастер создания заказа</b>\n\n"
    "Добро пожаловать в конструктор! Здесь мы поэтапно соберем параметры вашего идеального заказа. 🧩\n\n"
    "<b>Как это работает?</b>\n"
    "1️⃣ Вы выбираете категорию изделия.\n"
    "2️⃣ Отвечаете на простые вопросы (тираж, бумага, размер).\n"
    "3️⃣ Я формирую готовую заявку и отправляю её менеджеру.\n\n"
    "🚀 <b>В чем плюсы?</b>\n"
    "Менеджер получит <i>полную картину</i> и сможет максимально быстро просчитать стоимость, не задавая вам лишних вопросов.\n\n"
    "👇 <b>Выберите категорию, чтобы начать сборку:</b>"
)

TEXT_PROMO = (
    "📢 <b>Рекламная полиграфия</b>\n\n"
    "Отлично! Чтобы менеджер сделал точный расчет, давайте уточним формат изделия.\n\n"
    "Многие путают эти позиции, но мы поможем разобраться:\n\n"
    "⚡️ <b>Флаеры</b>\n"
    "Компактный формат (обычно 1/3 А4). Идеально для быстрых раздач, акций и приглашений. Минимум текста — максимум выгоды.\n\n"
    "📄 <b>Листовки</b>\n"
    "Ваша «рабочая лошадка» (А4, А5, А6). Больше места для информации, схем проезда или прайс-листов.\n\n"
    "📖 <b>Буклеты</b>\n"
    "Лист, сфальцованный (сложенный) в несколько раз. Имиджевый продукт, мини-каталог или меню.\n\n"
    "🖼 <b>Плакаты</b>\n"
    "Крупные форматы (А3, А2) для стен, витрин и афиш.\n\n"
    "<i>Выберите нужный пункт меню ниже, чтобы перейти к параметрам заказа:</i> 👇"
)

TEXT_MULTIPAGE = (
    "📚 <b>Многостраничная продукция</b>\n\n"
    "Это самые сложные, но и самые интересные изделия. Книги, журналы, каталоги — лицо вашей компании или творчества.\n\n"
    "Здесь очень важно не ошибиться с типом изделия, так как от этого зависит способ сборки (пружина, клей, скрепка) и цена.\n\n"
    "ℹ️ Если не уверены — нажмите <b>«Справка»</b>. Там есть подробное описание и примеры, которые помогут выбрать правильный вариант.\n\n"
    "👇 <b>Что именно вы хотите напечатать?</b>"
)

TEXT_MULTIPAGE_HELP = (
    "📚 <b>Книги</b>\n\n"
    "<b>Когда нужен серьёзный, долговечный и статусный продукт</b>\n\n"
    "Книга — это издание, которое читают, хранят и возвращаются к нему снова.\n"
    "Обычно имеет твёрдый или усиленный переплёт и рассчитана на долгий срок использования.\n\n"
    "<b>Преимущества:</b>\n"
    "• Максимальная долговечность\n"
    "• Создаёт ощущение ценности и авторитетности\n"
    "• Подходит для больших объёмов текста\n\n"
    "📰 <b>Журналы</b>\n\n"
    "<b>Когда нужен регулярный, живой и визуально привлекательный формат</b>\n\n"
    "Журнал — это периодическое издание. Обычно мягкая обложка, много фото и лёгкое перелистывание.\n\n"
    "📖 <b>Каталоги</b>\n\n"
    "<b>Когда нужно продавать товары</b>\n\n"
    "Главная задача — показать ассортимент и подтолкнуть к покупке. Минимум текста, максимум структуры.\n\n"
    "📑 <b>Брошюры</b>\n\n"
    "<b>Когда нужно быстро и недорого донести информацию</b>\n\n"
    "Компактное издание. Используется для презентаций, инструкций и раздатки.\n\n"
    "<b>Короткая подсказка:</b>\n"
    "Много текста и надолго → Книга\n"
    "Регулярные статьи → Журнал\n"
    "Товары и цены → Каталог\n"
    "Краткая информация → Брошюра"
)

# --- КЛАВИАТУРЫ ---

def kb_catalog_root():
    return InlineKeyboardMarkup(inline_keyboard=[
        #[InlineKeyboardButton(text="💳 Визитки", callback_data="prod_Визитки")],
        [InlineKeyboardButton(text="📢 Листовки/Реклама", callback_data="cat_promo"),
         InlineKeyboardButton(text="📚 Книги/Журналы", callback_data="cat_multipage")],
        [InlineKeyboardButton(text="📦 Упаковка/Наклейки", callback_data="prod_Упаковка"),
         InlineKeyboardButton(text="📎 Офис/Календари", callback_data="prod_Офис")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")]
    ])

def kb_cat_promo():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Листовки", callback_data="prod_Листовки"),
         InlineKeyboardButton(text="🎫 Флаеры", callback_data="prod_Флаеры")],
        [InlineKeyboardButton(text="🖼 Плакаты", callback_data="prod_Плакаты"),
         InlineKeyboardButton(text="🗺 Буклеты", callback_data="prod_Буклеты")],
        [InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="main_constructor")]
    ])

def kb_cat_multipage():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📕 Книги", callback_data="prod_Книги"),
         InlineKeyboardButton(text="📓 Журналы", callback_data="prod_Журналы")],
        [InlineKeyboardButton(text="📒 Каталоги", callback_data="prod_Каталоги"),
         InlineKeyboardButton(text="📄 Брошюры", callback_data="prod_Брошюры")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_multipage")],
        [InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="main_constructor")]
    ])

def kb_back_to_multipage():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Понятно, вернуться к выбору", callback_data="cat_multipage")]
    ])

# --- ХЕНДЛЕРЫ ---

@router.callback_query(F.data == "main_constructor")
async def show_catalog_root(callback: types.CallbackQuery, state: FSMContext):
    """Отображает главное меню конструктора заказов."""
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        text=TEXT_CATALOG_ROOT, 
        reply_markup=kb_catalog_root()
    )

@router.callback_query(F.data == "cat_promo")
async def show_promo(callback: types.CallbackQuery):
    """Отображает подменю рекламной полиграфии."""
    await callback.answer()
    await callback.message.edit_text(
        text=TEXT_PROMO, 
        reply_markup=kb_cat_promo()
    )

@router.callback_query(F.data == "cat_multipage")
async def show_multipage(callback: types.CallbackQuery):
    """Отображает подменю многостраничной продукции."""
    await callback.answer()
    await callback.message.edit_text(
        text=TEXT_MULTIPAGE,
        reply_markup=kb_cat_multipage()
    )

@router.callback_query(F.data == "help_multipage")
async def show_multipage_help(callback: types.CallbackQuery):
    """Показывает текст справки."""
    await callback.answer()
    await callback.message.edit_text(
        text=TEXT_MULTIPAGE_HELP,
        reply_markup=kb_back_to_multipage()
    )

@router.callback_query(F.data.startswith("prod_"))
async def process_product_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора конкретного изделия и переход к параметрам"""
    product_name = callback.data.replace("prod_", "")
    await state.update_data(category=product_name)
    
    await state.set_state(OrderConstructor.waiting_for_params)
    
    text = (
        f"✅ <b>Выбрано: {product_name}</b>\n\n"
        f"📝 <b>Шаг 2: Параметры изделия</b>\n"
        f"Пожалуйста, напишите основные характеристики:\n"
        f"— Тираж (сколько штук?)\n"
        f"— Размер (А4, А5, 10х15...)\n"
        f"— Цветность (ч/б или цветное)\n"
        f"— Тип бумаги (если знаете)\n\n"
        f"<i>Просто введите всё одним сообщением:</i>"
    )
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_constructor")]
    ]))
