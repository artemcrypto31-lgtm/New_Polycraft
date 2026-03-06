import os
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.exceptions import TelegramBadRequest

# Импорты из существующих файлов проекта
from database import Database
from handlers.start import WELCOME_TEXT
from keyboards import get_main_menu

router = Router()

# --- СОСТОЯНИЯ (FSM) ---
class PromoOrder(StatesGroup):
    step_format = State()      # Выбор формата (листовки)
    step_qty = State()         # Выбор тиража (листовки)
    step_folder_qty = State()  # Ввод тиража вручную (папки)

# --- ГЛАВНОЕ МЕНЮ АКЦИЙ ---
@router.callback_query(F.data.in_(["menu_promo", "main_promos"]))
async def show_promo_menu(callback: types.CallbackQuery, state: FSMContext):
    """Вход в раздел акций"""
    await state.clear()
    await callback.answer()
    
    text = (
        "🎁 <b>Актуальные акции типографии «Поликрафт»</b>\n\n"
        "Мы собрали специальные предложения, которые позволяют вам печатать больше — и платить меньше.\n"
        "Все акции рассчитаны на реальную экономию без потери качества:\n\n"
        "✔️ профессиональная печать\n"
        "✔️ четкие сроки\n"
        "✔️ фиксированная цена с НДС\n"
        "✔️ прозрачные условия\n\n"
        "Выберите интересующее предложение ниже и получите подробную информацию 👇"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 Листовки", callback_data="promo_leaflets"),
            InlineKeyboardButton(text="📁 Папки", callback_data="promo_folders")
        ],
        [InlineKeyboardButton(text="📚 Каталоги", callback_data="promo_catalog_info")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
    ])
    
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    except TelegramBadRequest:
        pass

# --- ЛОГИКА: ЛИСТОВКИ ---

@router.callback_query(F.data == "promo_leaflets")
async def show_leaflets_promo(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "<b>ПЕЧАТЬ ЛИСТОВОК В СБОРНОМ ТИРАЖЕ — ДО 3 РАЗ ДЕШЕВЛЕ</b>\n\n"
        "💸 <b>Нужно напечатать листовки, но бюджет ограничен?</b>\n"
        "Типография «Поликрафт» предлагает печать в сборном тираже — это способ снизить стоимость до 3 раз без потери качества.\n\n"
        "📌 <b>В чем суть?</b>\n"
        "В сборном тираже расходы на запуск оборудования делятся между несколькими заказами.\n"
        "➡️ <b>В результате вы платите значительно меньше.</b>\n\n"
        "📊 <b>ЦЕНЫ И ФОРМАТЫ (с НДС 20%)</b>\n"
        "<i>Бумага: мелованная, глянцевая 150 г/м²</i>\n\n"
        "🔹 <b>А6 (105×148 мм):</b>\n"
        "1000 шт — 96,00 BYN\n"
        "2000 шт — 144,00 BYN\n"
        "3000 шт — 216,00 BYN\n\n"
        "🔹 <b>Еврофлаер (99×210 мм):</b>\n"
        "1000 шт — 120,00 BYN\n"
        "2000 шт — 192,00 BYN\n"
        "3000 шт — 252,00 BYN\n\n"
        "🔹 <b>А5 (148×210 мм):</b>\n"
        "1000 шт — 144,00 BYN\n"
        "2000 шт — 240,00 BYN\n"
        "3000 шт — 360,00 BYN\n\n"
        "🔹 <b>А4 (210×297 мм):</b>\n"
        "1000 шт — 240,00 BYN\n"
        "2000 шт — 480,00 BYN\n"
        "3000 шт — 684,00 BYN\n\n"
        "🎯 <i>Это оптимальное решение для промо-акций.</i>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Хочу заказать", callback_data="promo_leaflets_order_menu")],
        [InlineKeyboardButton(text="🔙 Назад к акциям", callback_data="main_promos")]
    ])
    await callback.message.edit_text(text=text, reply_markup=keyboard)

@router.callback_query(F.data == "promo_leaflets_order_menu")
async def step_1_promo_format(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PromoOrder.step_format)
    text = "🛒 <b>Оформление акционного заказа: Шаг 1</b>\n\nВыберите формат продукции:"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="А3", callback_data="promo_fmt_A3"),
         InlineKeyboardButton(text="А4", callback_data="promo_fmt_A4")],
        [InlineKeyboardButton(text="А5", callback_data="promo_fmt_A5"),
         InlineKeyboardButton(text="А6", callback_data="promo_fmt_A6")],
        [InlineKeyboardButton(text="Флаер (Евро)", callback_data="promo_fmt_Flyer")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="promo_leaflets")]
    ])
    await callback.message.edit_text(text=text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("promo_fmt_"))
async def step_2_promo_quantity(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    fmt_code = callback.data.split("_")[2]
    await state.update_data(format=fmt_code)
    await state.set_state(PromoOrder.step_qty)
    
    buttons = []
    if fmt_code in ["A6", "A5", "Flyer"]:
        qtys = ["1000", "2000", "3000", "4000", "5000", "10000"]
    elif fmt_code == "A4":
        qtys = ["1000", "2000", "3000", "4000"]
    else: # A3
        qtys = ["1000", "2000"]

    row = []
    for q in qtys:
        row.append(InlineKeyboardButton(text=f"{int(q):,}".replace(",", " "), callback_data=f"promo_qty_{q}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="promo_leaflets_order_menu")])
    await callback.message.edit_text(text=f"📄 Формат: <b>{fmt_code}</b>\n🔢 <b>Выберите тираж:</b>", 
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(PromoOrder.step_qty, F.data.startswith("promo_qty_"))
async def step_3_promo_summary(callback: types.CallbackQuery, state: FSMContext):
    qty = callback.data.split("_")[2]
    await state.update_data(quantity=qty)
    data = await state.get_data()
    
    text = (
        f"✅ <b>Ваш выбор:</b>\n📄 Формат: <b>{data['format']}</b>\n🔢 Тираж: <b>{qty} экз.</b>\n\n"
        "📦 <b>Условия:</b>\n• Цены с НДС 20%\n• Бумага: 150 г/м²\n• Срок: 3-6 дней"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Отправить на просчет", callback_data="promo_submit_final")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"promo_fmt_{data['format']}")]
    ])
    await callback.message.edit_text(text=text, reply_markup=kb)

@router.callback_query(F.data == "promo_submit_final")
async def promo_submit_final(callback: types.CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    data = await state.get_data()
    user = callback.from_user
    managers = await db.get_managers()
    
    admin_msg = (
        f"🔥 <b>ЗАЯВКА (АКЦИЯ - ЛИСТОВКИ)</b>\n"
        f"👤 Клиент: {user.full_name} (@{user.username})\n"
        f"📄 Формат: <b>{data.get('format')}</b>\n"
        f"🔢 Тираж: <b>{data.get('quantity')}</b>"
    )
    
    for m_id in managers:
        try: await bot.send_message(m_id, admin_msg)
        except: pass
            
    await callback.message.edit_text(
        text="✅ <b>Заявка отправлена менеджеру!</b>\n\nМы свяжемся с вами в ближайшее время.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]])
    )
    await state.clear()

# --- ЛОГИКА: ПАПКИ ---

@router.callback_query(F.data == "promo_folders")
async def show_folders_promo(callback: types.CallbackQuery):
    text = (
        "<b>ЛУЧШАЯ ЦЕНА НА ВЫРУБНЫЕ ПАПКИ А4</b>\n\n"
        "📁 <b>Характеристики:</b>\n– Картон: 270 г/м²\n– Печать: 4+0\n– Ламинация: глянцевая\n\n"
        "💰 <b>ЦЕНЫ:</b>\n🔹 100 шт. — 420,00 BYN\n🔹 500 шт. — 1170,00 BYN"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Скачать макет папки", callback_data="promo_download_template")],
        [InlineKeyboardButton(text="💬 Заказать расчет", callback_data="promo_folder_ask")],
        [InlineKeyboardButton(text="🔙 Назад к акциям", callback_data="main_promos")]
    ])
    await callback.message.edit_text(text=text, reply_markup=kb)

@router.callback_query(F.data == "promo_download_template")
async def send_folder_template(callback: types.CallbackQuery):
    file_path = "files/Shtamp-papka-5mm-kontur.cdr"
    if os.path.exists(file_path):
        await callback.message.answer_document(FSInputFile(file_path), caption="📂 Макет папки А4")
    else:
        await callback.answer("⚠️ Файл временно недоступен", show_alert=True)

@router.callback_query(F.data == "promo_folder_ask")
async def ask_folder_qty(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(PromoOrder.step_folder_qty)
    await callback.message.edit_text(
        "📁 <b>Заказ вырубных папок</b>\n\nВведите необходимое <b>количество</b> сообщением:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="promo_folders")]])
    )

@router.message(PromoOrder.step_folder_qty)
async def get_folder_qty_and_summary(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Пожалуйста, введите число (например: 100).")
        return

    qty = message.text
    await state.update_data(folder_qty=qty)
    text = f"✅ <b>Ваш выбор:</b>\n📁 Папка А4\n🔢 Кол-во: <b>{qty} шт.</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Отправить на просчет", callback_data="promo_folder_submit")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="promo_folder_ask")]
    ])
    await message.answer(text=text, reply_markup=kb)

@router.callback_query(F.data == "promo_folder_submit")
async def submit_folder_order(callback: types.CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    data = await state.get_data()
    managers = await db.get_managers()
    admin_msg = f"🔥 <b>ЗАЯВКА (ПАПКИ)</b>\n👤 Клиент: {callback.from_user.full_name}\n🔢 Тираж: {data.get('folder_qty')}"
    
    for m_id in managers:
        try: await bot.send_message(m_id, admin_msg)
        except: pass
            
    await callback.message.edit_text("✅ <b>Заявка на папки принята!</b>", 
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]]))
    await state.clear()

# --- ЛОГИКА: КАТАЛОГИ ---

@router.callback_query(F.data == "promo_catalog_info")
async def show_catalog_promo(callback: types.CallbackQuery):
    text = "<b>КАТАЛОГ А5 — СПЕЦИАЛЬНАЯ ЦЕНА</b>\n\n"
    "📘 <b>Полноценный каталог по цене ниже рынка</b>\n\n"
    "📋 <b>Характеристики:</b>\n"
    "– Формат: А5 (14,5 × 20,5 см)\n"
    "– Объем: 8 страниц\n"
    "– Печать: 4+4\n"
    "– Бумага: 150 г/м²\n"
    "– Скрепление: скоба\n"
    "– Тираж: 1 000 шт.\n\n"
    "💰 <b>ЦЕНА:</b>\n"
    "❌ Старая цена — <strike>840,00 руб.</strike>\n"
    "✅ <b>Новая цена — 648,00 руб. с НДС</b>\n"
    "🔥 <i>Экономия — 192 руб.</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Хочу заказать", callback_data="back_to_main")], 
        [InlineKeyboardButton(text="🔙 Назад к акциям", callback_data="main_promos")]
    ])
    await callback.message.edit_text(text=text, reply_markup=kb)

# --- ВОЗВРАТ В МЕНЮ ---

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(text=WELCOME_TEXT, reply_markup=get_main_menu())
