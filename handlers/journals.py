from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from handlers.orders import kb_cat_multipage, TEXT_MULTIPAGE
import os
import json
from datetime import datetime
from database import Database
from models import Order, User

router = Router()

# =======================================================
# 🛠 НАСТРОЙКИ И МАШИНА СОСТОЯНИЙ
# =======================================================

class JournalCalc(StatesGroup):
    # --- ОБЩИЕ ---
    step_quantity = State()     # 1. Тираж
    step_format = State()       # 2. Формат
    step_orientation = State()  # 3. Ориентация
    
    # --- ОБЛОЖКА ---
    step_cover_type = State()   # 4. Тип переплета
    step_binding = State()      # 5. Скрепление
    step_cover_paper = State()  # 6. Плотность бумаги обложки
    step_cover_color = State()  # 7. Красочность обложки
    step_cover_finish = State() # 8. Доп. покрытие обложки
    
    # --- БЛОК ---
    step_block_pages = State()        # 9. Кол-во страниц
    step_block_color = State()        # 10. Красочность блока
    step_block_paper_type = State()   # 11. Вид бумаги блока
    step_block_paper_weight = State() # 12. Плотность бумаги блока
    
    # --- ФИНАЛ ---
    step_services = State()           # 13. Доп. услуги

    # --- РЕГИСТРАЦИЯ ---
    reg_name = State()
    reg_phone = State()
    reg_city = State()
    reg_address = State()

def get_breadcrumbs(data: dict) -> str:
    """Генерирует историю выбора (Чек)."""
    sections = []

    # 1. ОБЩИЕ
    gen = []
    if data.get('quantity'): gen.append(f"• Тираж: <b>{data['quantity']} шт.</b>")
    if data.get('format_name'): gen.append(f"• Формат: <b>{data['format_name']}</b>")
    if data.get('orientation'): gen.append(f"• Ориентация: <b>{data['orientation']}</b>")
    if gen: sections.append("🔧 <b>ОБЩИЕ:</b>\n" + "\n".join(gen))

    # 2. ОБЛОЖКА
    cov = []
    if data.get('cover_type'): cov.append(f"• Переплет: <b>{data['cover_type']}</b>")
    if data.get('binding'): cov.append(f"• Скрепление: <b>{data['binding']}</b>")
    if data.get('cover_paper'): cov.append(f"• Бумага: <b>{data['cover_paper']}</b>")
    if data.get('cover_color'): cov.append(f"• Цветность: <b>{data['cover_color']}</b>")
    
    finishes = data.get('cover_finishes_list', [])
    if finishes: cov.append(f"• Отделка: <b>{', '.join(finishes)}</b>")
    elif data.get('cover_finish_done'): cov.append(f"• Отделка: <b>Нет</b>")
    
    if cov: sections.append("📕 <b>ОБЛОЖКА:</b>\n" + "\n".join(cov))

    # 3. БЛОК
    blk = []
    if data.get('block_pages'): blk.append(f"• Страниц: <b>{data['block_pages']}</b>")
    if data.get('block_color'): blk.append(f"• Печать: <b>{data['block_color']}</b>")
    if data.get('block_paper_type'): blk.append(f"• Бумага: <b>{data['block_paper_type']}</b>")
    if data.get('block_paper_weight'): blk.append(f"• Плотность: <b>{data['block_paper_weight']}</b>")
    
    if blk: sections.append("📄 <b>БЛОК:</b>\n" + "\n".join(blk))

    # 4. УСЛУГИ
    srv = data.get('services_list', [])
    if srv: sections.append("🛠 <b>УСЛУГИ:</b>\n• " + ", ".join(srv))
    elif data.get('services_done'): sections.append("🛠 <b>УСЛУГИ:</b>\n• Нет")

    if not sections: return ""
    return "📝 <b>Ваш заказ:</b>\n\n" + "\n\n".join(sections) + "\n➖➖➖➖➖➖➖➖\n"

async def smart_edit(message: types.Message, text: str, kb: InlineKeyboardMarkup):
    try:
        await message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await message.answer(text=text, reply_markup=kb, parse_mode="HTML")

# Функция для показа справки
async def show_help(callback: types.CallbackQuery, text: str, back_callback: str):
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Понятно, вернуться", callback_data=back_callback)]])
    await smart_edit(callback.message, text, kb)


# =======================================================
# 1️⃣ ШАГ 1: ТИРАЖ
# =======================================================

@router.callback_query(F.data.in_({"prod_Журналы", "start_calc_journal"}))
async def step_1_quantity(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(JournalCalc.step_quantity)
    
    text = "🔢 <b>Шаг 1. Тираж</b>\nВведите количество (числом) или выберите:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50", callback_data="qty_50"), 
         InlineKeyboardButton(text="100", callback_data="qty_100"), 
         InlineKeyboardButton(text="200", callback_data="qty_200")],
        [InlineKeyboardButton(text="300", callback_data="qty_300"), 
         InlineKeyboardButton(text="500", callback_data="qty_500"), 
         InlineKeyboardButton(text="1000", callback_data="qty_1000")],
        # Навигация в один ряд (2 столбца)
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_qty"),
         InlineKeyboardButton(text="🔙 В меню", callback_data="stop_calc_journal")]
    ])
    await smart_edit(callback.message, text, kb)

# СПРАВКА ШАГ 1
@router.callback_query(F.data == "help_journal_qty")
async def help_1(callback: types.CallbackQuery):
    await show_help(callback, "ℹ️ <b>Тираж</b>\n\nЧем больше тираж, тем дешевле один экземпляр.\n• <b>До 300 шт:</b> Цифровая печать (быстро).\n• <b>От 500 шт:</b> Офсетная печать (выгодно).", "journal_back_step_0")

@router.callback_query(F.data == "journal_back_step_0")
async def back_1(callback: types.CallbackQuery, state: FSMContext):
    await step_1_quantity(callback, state)


@router.callback_query(JournalCalc.step_quantity, F.data.startswith("qty_"))
async def process_qty_btn(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(quantity=int(callback.data.split("_")[1]))
    await callback.answer()
    await step_2_format(callback.message, state)

@router.message(JournalCalc.step_quantity)
async def process_qty_text(message: types.Message, state: FSMContext):
    try: await message.delete()
    except: pass
    if not message.text.isdigit(): 
        await message.answer("⚠️ Введите только число!")
        return
    qty = int(message.text)
    if qty < 10:
        await message.answer("⚠️ Минимальный тираж — <b>10 экземпляров</b>.", parse_mode="HTML")
        return
    await state.update_data(quantity=qty)
    await step_2_format(message, state)

@router.callback_query(F.data == "stop_calc_journal")
async def cancel_calc(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(TEXT_MULTIPAGE, reply_markup=kb_cat_multipage(), parse_mode="HTML")


# =======================================================
# 2️⃣ ШАГ 2: ФОРМАТ
# =======================================================

async def step_2_format(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_format)
    text = f"{get_breadcrumbs(await state.get_data())}📏 <b>Шаг 2. Формат</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        # Форматы сеткой 2х2
        [InlineKeyboardButton(text="А4 (210x297)", callback_data="fmt_A4"), 
         InlineKeyboardButton(text="А5 (148x210)", callback_data="fmt_A5")],
        [InlineKeyboardButton(text="А6 (105x148)", callback_data="fmt_A6"), 
         InlineKeyboardButton(text="165х240", callback_data="fmt_Crown")],
        # Навигация в один ряд
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_fmt"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_1")]
    ])
    await smart_edit(message, text, kb)

# СПРАВКА ШАГ 2
@router.callback_query(F.data == "help_journal_fmt")
async def help_2(callback: types.CallbackQuery):
    await show_help(callback, "ℹ️ <b>Форматы</b>\n\n🔹 <b>А4:</b> Стандартный альбомный лист. Глянцевые журналы.\n🔹 <b>А5:</b> Половина А4. Самый популярный.\n🔹 <b>А6:</b> Карманный формат.\n🔹 <b>165х240:</b> «Королевский» формат, выглядит премиально.", "journal_back_step_help_2")

@router.callback_query(F.data == "journal_back_step_help_2")
async def back_help_2(callback: types.CallbackQuery, state: FSMContext):
    await step_2_format(callback.message, state)


@router.callback_query(F.data == "journal_back_step_1")
async def back_to_step_1(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await step_1_quantity(callback, state)

@router.callback_query(JournalCalc.step_format, F.data.startswith("fmt_"))
async def process_fmt(callback: types.CallbackQuery, state: FSMContext):
    code = callback.data.split("_")[1]
    names = {"A4":"А4", "A5":"А5", "A6":"А6", "Crown":"165х240 мм"}
    await state.update_data(format_code=code, format_name=names.get(code, code))
    await callback.answer()
    await step_3_orientation(callback.message, state)


# =======================================================
# 3️⃣ ШАГ 3: ОРИЕНТАЦИЯ
# =======================================================

async def step_3_orientation(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_orientation)
    text = f"{get_breadcrumbs(await state.get_data())}🔄 <b>Шаг 3. Ориентация</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        # Выбор в один ряд
        [InlineKeyboardButton(text="↕️ Вертикальная", callback_data="orient_vert"), 
         InlineKeyboardButton(text="↔️ Горизонтальная", callback_data="orient_horiz")],
        # Навигация в один ряд
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_orient"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_2")]
    ])
    await smart_edit(message, text, kb)

# СПРАВКА ШАГ 3
@router.callback_query(F.data == "help_journal_orient")
async def help_3(callback: types.CallbackQuery):
    await show_help(callback, "ℹ️ <b>Ориентация</b>\n\n↕️ <b>Вертикальная (Книжная):</b> Стандарт для большинства журналов. Переплет по длинной стороне.\n\n↔️ <b>Горизонтальная (Альбомная):</b> Для портфолио и фотокниг. Переплет по короткой стороне.", "journal_back_step_help_3")

@router.callback_query(F.data == "journal_back_step_help_3")
async def back_help_3(callback: types.CallbackQuery, state: FSMContext):
    await step_3_orientation(callback.message, state)

@router.callback_query(F.data == "journal_back_step_2")
async def back_to_step_2(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await step_2_format(callback.message, state)

@router.callback_query(JournalCalc.step_orientation, F.data.startswith("orient_"))
async def process_orient(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(orientation="Вертикальная" if "vert" in callback.data else "Горизонтальная")
    await callback.answer()
    await step_4_cover_type(callback.message, state)


# =======================================================
# 4️⃣ ШАГ 4: ТИП ПЕРЕПЛЕТА
# =======================================================

async def step_4_cover_type(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_cover_type)
    text = f"{get_breadcrumbs(await state.get_data())}📕 <b>Шаг 4. Переплет</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Мягкий", callback_data="cover_type_soft"), 
         InlineKeyboardButton(text="Твердый", callback_data="cover_type_hard")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_covtype"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_3")]
    ])
    await smart_edit(message, text, kb)

# СПРАВКА ШАГ 4
@router.callback_query(F.data == "help_journal_covtype")
async def help_4(callback: types.CallbackQuery):
    await show_help(callback, "ℹ️ <b>Переплет</b>\n\n📕 <b>Мягкий:</b> Обычная плотная бумага. Как у глянцевых журналов. Дешевле и быстрее.\n\n📘 <b>Твердый (7БЦ):</b> Картонная основа, как у серьезных книг. Долговечно, презентабельно, но дороже.", "journal_back_step_help_4")

@router.callback_query(F.data == "journal_back_step_help_4")
async def back_help_4(callback: types.CallbackQuery, state: FSMContext):
    await step_4_cover_type(callback.message, state)

@router.callback_query(F.data == "journal_back_step_3")
async def back_to_step_3(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await step_3_orientation(callback.message, state)

@router.callback_query(JournalCalc.step_cover_type, F.data.startswith("cover_type_"))
async def process_cov_type(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(cover_type="Мягкий" if "soft" in callback.data else "Твердый")
    await callback.answer()
    await step_5_binding(callback.message, state)


# =======================================================
# 5️⃣ ШАГ 5: СКРЕПЛЕНИЕ
# =======================================================

async def step_5_binding(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_binding)
    text = f"{get_breadcrumbs(await state.get_data())}🔗 <b>Шаг 5. Скрепление</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        # 3 кнопки в один ряд (они короткие, так что поместятся)
        [InlineKeyboardButton(text="Скоба", callback_data="bind_staple"), 
         InlineKeyboardButton(text="Пружина", callback_data="bind_wire"), 
         InlineKeyboardButton(text="Клей (КБС)", callback_data="bind_glue")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_bind"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_4")]
    ])
    await smart_edit(message, text, kb)

# СПРАВКА ШАГ 5
@router.callback_query(F.data == "help_journal_bind")
async def help_5(callback: types.CallbackQuery):
    await show_help(callback, "ℹ️ <b>Скрепление</b>\n\n📎 <b>Скоба:</b> Как школьная тетрадь. Идеально до 48-60 страниц.\n\n➰ <b>Пружина:</b> Удобно листать, раскрывается на 360°. Для блокнотов и каталогов.\n\n📚 <b>Клей (КБС):</b> Корешок проклеен. Выглядит как настоящая книга. Подходит для изданий от 60 страниц.", "journal_back_step_help_5")

@router.callback_query(F.data == "journal_back_step_help_5")
async def back_help_5(callback: types.CallbackQuery, state: FSMContext):
    await step_5_binding(callback.message, state)

@router.callback_query(F.data == "journal_back_step_4")
async def back_to_step_4(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await step_4_cover_type(callback.message, state)

@router.callback_query(JournalCalc.step_binding, F.data.startswith("bind_"))
async def process_bind(callback: types.CallbackQuery, state: FSMContext):
    names = {"staple":"Скоба", "wire":"Пружина", "glue":"Клей"}
    code = callback.data.split("_")[1]
    await state.update_data(binding=names.get(code, code))
    await callback.answer()
    await step_6_cover_paper(callback.message, state)


# =======================================================
# 6️⃣ ШАГ 6: БУМАГА ОБЛОЖКИ
# =======================================================

async def step_6_cover_paper(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_cover_paper)
    text = f"{get_breadcrumbs(await state.get_data())}📄 <b>Шаг 6. Бумага обложки</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        # Красивая сетка 3х2
        [InlineKeyboardButton(text="150 г", callback_data="cov_pap_150"), 
         InlineKeyboardButton(text="170 г", callback_data="cov_pap_170"), 
         InlineKeyboardButton(text="200 г", callback_data="cov_pap_200")],
        [InlineKeyboardButton(text="250 г", callback_data="cov_pap_250"), 
         InlineKeyboardButton(text="300 г", callback_data="cov_pap_300"), 
         InlineKeyboardButton(text="350 г", callback_data="cov_pap_350")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_covpap"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_5")]
    ])
    await smart_edit(message, text, kb)

# СПРАВКА ШАГ 6
@router.callback_query(F.data == "help_journal_covpap")
async def help_6(callback: types.CallbackQuery):
    await show_help(callback, "ℹ️ <b>Бумага обложки</b>\n\nИзмеряется в граммах на кв.метр.\n• <b>150-170 г/м²:</b> Тонкая, гибкая обложка (буклет).\n• <b>200-250 г/м²:</b> Стандарт для журналов. Плотная, держит форму.\n• <b>300-350 г/м²:</b> Очень жесткая, как открытка или визитка.", "journal_back_step_help_6")

@router.callback_query(F.data == "journal_back_step_help_6")
async def back_help_6(callback: types.CallbackQuery, state: FSMContext):
    await step_6_cover_paper(callback.message, state)

@router.callback_query(F.data == "journal_back_step_5")
async def back_to_step_5(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await step_5_binding(callback.message, state)

@router.callback_query(JournalCalc.step_cover_paper, F.data.startswith("cov_pap_"))
async def process_cov_pap(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(cover_paper=callback.data.split("_")[2] + " гр/м²")
    await callback.answer()
    await step_7_cover_color(callback.message, state)


# =======================================================
# 7️⃣ ШАГ 7: КРАСОЧНОСТЬ ОБЛОЖКИ
# =======================================================

async def step_7_cover_color(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_cover_color)
    text = f"{get_breadcrumbs(await state.get_data())}🎨 <b>Шаг 7. Цвет обложки</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        # Сетка 2х2
        [InlineKeyboardButton(text="4+0 (Лицо)", callback_data="cov_col_4+0"), 
         InlineKeyboardButton(text="4+4 (Все)", callback_data="cov_col_4+4")],
        [InlineKeyboardButton(text="1+1 (ЧБ)", callback_data="cov_col_1+1"), 
         InlineKeyboardButton(text="4+1 (Цв+ЧБ)", callback_data="cov_col_4+1")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_covcol"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_6")]
    ])
    await smart_edit(message, text, kb)

# СПРАВКА ШАГ 7
@router.callback_query(F.data == "help_journal_covcol")
async def help_7(callback: types.CallbackQuery):
    await show_help(callback, "ℹ️ <b>Красочность</b>\n\n🎨 <b>4+0:</b> Цветная только снаружи, внутри обложка белая.\n🎨 <b>4+4:</b> Цветная и снаружи, и внутри.\n⚫️ <b>1+1:</b> Черно-белая печать.\n\n<i>Первая цифра - лицо, вторая - оборот.</i>", "journal_back_step_help_7")

@router.callback_query(F.data == "journal_back_step_help_7")
async def back_help_7(callback: types.CallbackQuery, state: FSMContext):
    await step_7_cover_color(callback.message, state)

@router.callback_query(F.data == "journal_back_step_6")
async def back_to_step_6(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await step_6_cover_paper(callback.message, state)

@router.callback_query(JournalCalc.step_cover_color, F.data.startswith("cov_col_"))
async def process_cov_col(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(cover_color=callback.data.split("_")[2])
    await callback.answer()
    await step_8_cover_finish(callback.message, state)


# =======================================================
# 8️⃣ ШАГ 8: ОТДЕЛКА ОБЛОЖКИ (МУЛЬТИ)
# =======================================================

def kb_finish(sel):
    def t(l, k): return f"✅ {l}" if k in sel else l
    return InlineKeyboardMarkup(inline_keyboard=[
        # Удобное распределение кнопок с галочками
        [InlineKeyboardButton(text=t("Ламинация", "Ламинация"), callback_data="finish_toggle_Ламинация"),
         InlineKeyboardButton(text=t("Тиснение", "Тиснение"), callback_data="finish_toggle_Тиснение")],
        [InlineKeyboardButton(text=t("УФ-лак", "УФ-лак"), callback_data="finish_toggle_УФ-лак")],
        [InlineKeyboardButton(text="➡️ Готово / Дальше", callback_data="finish_done")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_finish"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_7")]
    ])

async def step_8_cover_finish(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_cover_finish)
    d = await state.get_data()
    await smart_edit(message, f"{get_breadcrumbs(d)}✨ <b>Шаг 8. Отделка обложки</b>", kb_finish(d.get("cover_finishes_list", [])))

# СПРАВКА ШАГ 8
@router.callback_query(F.data == "help_journal_finish")
async def help_8(callback: types.CallbackQuery):
    await show_help(callback, "ℹ️ <b>Отделка</b>\n\n✨ <b>Ламинация:</b> Защитная пленка (матовая или глянцевая). Защищает от влаги и царапин.\n🔥 <b>Тиснение:</b> Выдавливание логотипа или букв (рельеф).\n💧 <b>УФ-лак:</b> Глянцевое выделение отдельных элементов (например, логотипа) на матовом фоне.", "journal_back_step_help_8")

@router.callback_query(F.data == "journal_back_step_help_8")
async def back_help_8(callback: types.CallbackQuery, state: FSMContext):
    await step_8_cover_finish(callback.message, state)

@router.callback_query(JournalCalc.step_cover_finish, F.data.startswith("finish_toggle_"))
async def toggle_finish(callback: types.CallbackQuery, state: FSMContext):
    item = callback.data.split("_")[2]
    d = await state.get_data()
    sel = d.get("cover_finishes_list", [])
    
    if item in sel: sel.remove(item)
    else: sel.append(item)
    
    await state.update_data(cover_finishes_list=sel)
    try: await callback.message.edit_reply_markup(reply_markup=kb_finish(sel))
    except: pass
    await callback.answer()

@router.callback_query(F.data == "journal_back_step_7")
async def back_to_step_7(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await step_7_cover_color(callback.message, state)

@router.callback_query(F.data == "finish_done")
async def finish_done(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(cover_finish_done=True)
    await callback.answer()
    await step_9_block_pages(callback.message, state)


# =======================================================
# 9️⃣ ШАГ 9: СТРАНИЦЫ БЛОКА
# =======================================================

async def step_9_block_pages(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_block_pages)
    text = (
        f"{get_breadcrumbs(await state.get_data())}"
        "📄 <b>Шаг 9. Страниц в блоке</b>\n\n"
        "Введите количество (минимум 4).\n"
        "❗️ <b>Число должно быть кратно 4</b> (4, 8, 12, 16...)\n\n"
        "<i>Выберите из списка или введите вручную:</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        # 4 компактные кнопки в ряд
        [InlineKeyboardButton(text="8", callback_data="pages_8"), 
         InlineKeyboardButton(text="12", callback_data="pages_12"), 
         InlineKeyboardButton(text="24", callback_data="pages_24"), 
         InlineKeyboardButton(text="48", callback_data="pages_48")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_pages"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_8")]
    ])
    await smart_edit(message, text, kb)

# СПРАВКА ШАГ 9
@router.callback_query(F.data == "help_journal_pages")
async def help_9(callback: types.CallbackQuery):
    await show_help(callback, "ℹ️ <b>Количество страниц</b>\n\nВ полиграфии страница (полоса) — это одна сторона листа.\n\n❗️ <b>Почему кратно 4?</b>\nЛист складывается пополам, образуя 4 страницы. Нельзя сделать журнал на 5 или 7 страниц, только 4, 8, 12 и т.д.", "journal_back_step_help_9")

@router.callback_query(F.data == "journal_back_step_help_9")
async def back_help_9(callback: types.CallbackQuery, state: FSMContext):
    await step_9_block_pages(callback.message, state)

@router.callback_query(F.data == "journal_back_step_8")
async def back_to_step_8(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await step_8_cover_finish(callback.message, state)

# КНОПКИ БЫСТРОГО ВЫБОРА СТРАНИЦ
@router.callback_query(JournalCalc.step_block_pages, F.data.startswith("pages_"))
async def process_pages_btn(callback: types.CallbackQuery, state: FSMContext):
    pages = int(callback.data.split("_")[1])
    await state.update_data(block_pages=pages)
    await callback.answer()
    await step_10_block_color(callback.message, state)

# РУЧНОЙ ВВОД СТРАНИЦ
@router.message(JournalCalc.step_block_pages)
async def process_pages_text(message: types.Message, state: FSMContext):
    try: await message.delete()
    except: pass
    
    if not message.text.isdigit(): 
        await message.answer("⚠️ Введите только число!")
        return
    
    pages = int(message.text)
    
    if pages < 4:
        await message.answer("⚠️ Минимум 4 страницы!")
        return
    
    if pages % 4 != 0:
        await message.answer(
            "⚠️ Количество страниц должно делиться на 4 без остатка!\n"
            f"<i>Ближайшие варианты: {pages - (pages%4)} или {pages + (4 - pages%4)}</i>", 
            parse_mode="HTML"
        )
        return

    await state.update_data(block_pages=pages)
    await step_10_block_color(message, state)


# =======================================================
# 🔟 ШАГ 10: ЦВЕТ БЛОКА
# =======================================================

async def step_10_block_color(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_block_color)
    text = f"{get_breadcrumbs(await state.get_data())}🎨 <b>Шаг 10. Печать блока</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1+1 (ЧБ)", callback_data="blk_col_1+1"), 
         InlineKeyboardButton(text="2+2 (Два цв.)", callback_data="blk_col_2+2")],
        [InlineKeyboardButton(text="4+4 (Полноцвет)", callback_data="blk_col_4+4")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_blkcol"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_9")]
    ])
    await smart_edit(message, text, kb)

# СПРАВКА ШАГ 10
@router.callback_query(F.data == "help_journal_blkcol")
async def help_10(callback: types.CallbackQuery):
    await show_help(callback, "ℹ️ <b>Цветность блока</b>\n\n⚫️ <b>1+1 (ЧБ):</b> Текст, схемы, черно-белые фото. Дешевле всего.\n\n🎨 <b>4+4 (Цвет):</b> Полноцветные фото и иллюстрации на каждой странице.\n\n🔴 <b>2+2:</b> Использование двух красок (например, Черный + Красный для заголовков).", "journal_back_step_help_10")

@router.callback_query(F.data == "journal_back_step_help_10")
async def back_help_10(callback: types.CallbackQuery, state: FSMContext):
    await step_10_block_color(callback.message, state)

@router.callback_query(F.data == "journal_back_step_9")
async def back_to_step_9(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await step_9_block_pages(callback.message, state)

@router.callback_query(JournalCalc.step_block_color, F.data.startswith("blk_col_"))
async def process_blk_col(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(block_color=callback.data.split("_")[2])
    await callback.answer()
    await step_11_block_paper_type(callback.message, state)


# =======================================================
# 1️⃣1️⃣ ШАГ 11: ТИП БУМАГИ БЛОКА
# =======================================================

async def step_11_block_paper_type(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_block_paper_type)
    text = f"{get_breadcrumbs(await state.get_data())}📄 <b>Шаг 11. Бумага блока</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        # Из-за длины текста "Офсетная" на одном ряду, меловка на другом
        [InlineKeyboardButton(text="Офсетная", callback_data="blk_type_Offset")],
        [InlineKeyboardButton(text="Мелованная Глянец", callback_data="blk_type_Glossy"),
         InlineKeyboardButton(text="Мелованная Мат", callback_data="blk_type_Matte")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_blktype"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_10")]
    ])
    await smart_edit(message, text, kb)

# СПРАВКА ШАГ 11
@router.callback_query(F.data == "help_journal_blktype")
async def help_11(callback: types.CallbackQuery):
    await show_help(callback, "ℹ️ <b>Тип бумаги</b>\n\n📄 <b>Офсетная:</b> Обычная офисная бумага. Шершавая, хорошо писать ручкой. Для текстовых журналов.\n\n✨ <b>Мелованная:</b> Гладкая, приятная на ощупь. Идеальна для фото и ярких картинок.\n<i>Глянец блестит, Мат не бликует.</i>", "journal_back_step_help_11")

@router.callback_query(F.data == "journal_back_step_help_11")
async def back_help_11(callback: types.CallbackQuery, state: FSMContext):
    await step_11_block_paper_type(callback.message, state)

@router.callback_query(F.data == "journal_back_step_10")
async def back_to_step_10(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await step_10_block_color(callback.message, state)

@router.callback_query(JournalCalc.step_block_paper_type, F.data.startswith("blk_type_"))
async def process_blk_type(callback: types.CallbackQuery, state: FSMContext):
    names = {"Offset":"Офсетная", "Glossy":"Меловка Глянец", "Matte":"Меловка Мат"}
    code = callback.data.split("_")[2]
    await state.update_data(block_paper_type=names.get(code, code))
    await callback.answer()
    await step_12_block_paper_weight(callback.message, state)


# =======================================================
# 1️⃣2️⃣ ШАГ 12: ПЛОТНОСТЬ БЛОКА (ВЕТВЛЕНИЕ)
# =======================================================

async def step_12_block_paper_weight(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_block_paper_weight)
    data = await state.get_data()
    ptype = data.get('block_paper_type', '')
    
    text = (
        f"{get_breadcrumbs(data)}"
        "📄 <b>Шаг 12. Плотность бумаги блока</b>\n"
        f"Выбрана бумага: <i>{ptype}</i>\n"
        "Выберите подходящую плотность:"
    )
    
    buttons = []
    
    if "Офсетная" in ptype:
        # Для офсета сетка 2х2
        buttons.append([
            InlineKeyboardButton(text="65 г/м²", callback_data="blk_w_65"),
            InlineKeyboardButton(text="80 г/м²", callback_data="blk_w_80")
        ])
        buttons.append([
            InlineKeyboardButton(text="100 г/м²", callback_data="blk_w_100"),
            InlineKeyboardButton(text="120 г/м²", callback_data="blk_w_120")
        ])
    else:
        # Для меловки сетка 3х2 + 1
        buttons.append([
            InlineKeyboardButton(text="90 г", callback_data="blk_w_90"),
            InlineKeyboardButton(text="115 г", callback_data="blk_w_115"),
            InlineKeyboardButton(text="130 г", callback_data="blk_w_130")
        ])
        buttons.append([
            InlineKeyboardButton(text="150 г", callback_data="blk_w_150"),
            InlineKeyboardButton(text="170 г", callback_data="blk_w_170"),
            InlineKeyboardButton(text="200 г", callback_data="blk_w_200")
        ])
        buttons.append([
            InlineKeyboardButton(text="250 г/м²", callback_data="blk_w_250")
        ])
    
    # Навигация в один ряд
    buttons.append([
        InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_blkweight"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_11")
    ])
    
    await smart_edit(message, text, InlineKeyboardMarkup(inline_keyboard=buttons))

# СПРАВКА ШАГ 12
@router.callback_query(F.data == "help_journal_blkweight")
async def help_12(callback: types.CallbackQuery):
    await show_help(callback, "ℹ️ <b>Плотность блока</b>\n\n🔹 <b>65-80 г/м²:</b> Стандартная офисная, тонкая. Для книг и инструкций.\n🔹 <b>115-130 г/м²:</b> Плотная журнальная страница. Не просвечивает.\n🔹 <b>170+ г/м²:</b> Очень плотная, почти как тонкий картон. Для фотоальбомов.", "journal_back_step_help_12")

@router.callback_query(F.data == "journal_back_step_help_12")
async def back_help_12(callback: types.CallbackQuery, state: FSMContext):
    await step_12_block_paper_weight(callback.message, state)

@router.callback_query(F.data == "journal_back_step_11")
async def back_to_step_11(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await step_11_block_paper_type(callback.message, state)

@router.callback_query(JournalCalc.step_block_paper_weight, F.data.startswith("blk_w_"))
async def process_blk_weight(callback: types.CallbackQuery, state: FSMContext):
    weight = callback.data.split("_")[2] + " гр/м²"
    await state.update_data(block_paper_weight=weight)
    await callback.answer()
    await step_13_services(callback.message, state)


# =======================================================
# 1️⃣3️⃣ ШАГ 13: ДОП. УСЛУГИ (МУЛЬТИВЫБОР)
# =======================================================

def kb_services(selected_list: list):
    def t(l, k): return f"✅ {l}" if k in selected_list else l
    return InlineKeyboardMarkup(inline_keyboard=[
        # Услуги удобно распределены
        [InlineKeyboardButton(text=t("Верстка", "Верстка"), callback_data="srv_toggle_Верстка"),
         InlineKeyboardButton(text=t("ISBN", "ISBN"), callback_data="srv_toggle_ISBN")],
        [InlineKeyboardButton(text=t("Корректура / Редактура", "Корректура"), callback_data="srv_toggle_Корректура")],
        
        [InlineKeyboardButton(text="➡️ Рассчитать заказ", callback_data="srv_done")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_srv"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_12")]
    ])

async def step_13_services(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_services)
    data = await state.get_data()
    selected = data.get("services_list", [])
    
    text = (
        f"{get_breadcrumbs(data)}"
        "🛠 <b>Шаг 13. Дополнительные услуги</b>\n"
        "Нужна ли помощь с макетом или регистрацией издания?\n"
        "<i>Отметьте нужное и нажмите «Рассчитать».</i>"
    )
    
    await smart_edit(message, text, kb_services(selected))

# СПРАВКА ШАГ 13
@router.callback_query(F.data == "help_journal_srv")
async def help_13(callback: types.CallbackQuery):
    await show_help(callback, "ℹ️ <b>Услуги</b>\n\n💻 <b>Верстка:</b> Сборка макета из вашего текста и картинок.\n📖 <b>ISBN:</b> Присвоение номера в Книжной палате (для официального издания).\n📝 <b>Корректура:</b> Исправление ошибок в тексте.", "journal_back_step_help_13")

@router.callback_query(F.data == "journal_back_step_help_13")
async def back_help_13(callback: types.CallbackQuery, state: FSMContext):
    await step_13_services(callback.message, state)

@router.callback_query(JournalCalc.step_services, F.data.startswith("srv_toggle_"))
async def toggle_service(callback: types.CallbackQuery, state: FSMContext):
    item = callback.data.split("_")[2]
    data = await state.get_data()
    selected = data.get("services_list", [])
    
    if item in selected: selected.remove(item)
    else: selected.append(item)
    
    await state.update_data(services_list=selected)
    try: await callback.message.edit_reply_markup(reply_markup=kb_services(selected))
    except: pass
    await callback.answer()

@router.callback_query(F.data == "journal_back_step_12")
async def back_to_step_12(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await step_12_block_paper_weight(callback.message, state)


# =======================================================
# 🏁 ФИНАЛ: ПРОВЕРКА И ОТПРАВКА
# =======================================================

@router.callback_query(F.data == "srv_done")
async def step_finish_summary(callback: types.CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    await state.update_data(services_done=True)
    data = await state.get_data()
    
    summary = get_breadcrumbs(data)
    await state.update_data(final_summary=summary)

    # ПРОВЕРКА ПРОФИЛЯ
    user_id = callback.message.chat.id
    profile = await db.get_user(user_id)

    if not profile or not profile.full_name or not profile.phone:
        btn_text = "📝 Заполнить контакты"
        call_action = "journal_reg_start"
        alert_text = "⚠️ <b>Почти готово!</b>\nНам нужны контакты для связи."
    else:
        btn_text = "✅ Отправить менеджеру"
        call_action = "journal_submit_order"
        alert_text = "🎉 <b>Заказ сформирован!</b>"

    text = (
        f"{alert_text}\n\n"
        f"{summary}"
        "Менеджер проверит параметры и сделает точный расчет стоимости."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, callback_data=call_action)],
        [InlineKeyboardButton(text="🔄 Заполнить заново", callback_data="start_calc_journal")]
    ])
    
    await smart_edit(callback.message, text, kb)

# =======================================================
# 📝 РЕГИСТРАЦИЯ (Если нет контактов)
# =======================================================

@router.callback_query(F.data == "journal_reg_start")
async def reg_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(JournalCalc.reg_name)
    await callback.message.answer("✍️ Введите ваше <b>Имя</b>:", parse_mode="HTML")

@router.message(JournalCalc.reg_name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(reg_name=message.text)
    try: await message.delete() 
    except: pass
    await state.set_state(JournalCalc.reg_phone)
    await message.answer("📞 Введите ваш <b>Телефон</b>:", parse_mode="HTML")

@router.message(JournalCalc.reg_phone)
async def reg_phone(message: types.Message, state: FSMContext):
    await state.update_data(reg_phone=message.text)
    try: await message.delete() 
    except: pass
    await state.set_state(JournalCalc.reg_city)
    await message.answer("🏙 Введите ваш <b>Город</b>:", parse_mode="HTML")

@router.message(JournalCalc.reg_city)
async def reg_city(message: types.Message, state: FSMContext):
    await state.update_data(reg_city=message.text)
    try: await message.delete() 
    except: pass
    await state.set_state(JournalCalc.reg_address)
    await message.answer("🚚 Введите <b>Адрес доставки</b>:", parse_mode="HTML")

@router.message(JournalCalc.reg_address)
async def reg_address(message: types.Message, state: FSMContext, bot: Bot, db: Database):
    data = await state.get_data()
    # Сохраняем в базу
    await db.update_user_profile(
        message.chat.id, 
        full_name=data['reg_name'], 
        phone=data['reg_phone'], 
        city=data['reg_city'], 
        address=message.text
    )
    try: await message.delete() 
    except: pass
    await message.answer("✅ Контакты сохранены!")
    await finalize_order(message.chat, state, bot, message, db)


# =======================================================
# 🚀 ОТПРАВКА ЗАКАЗА (Финализация)
# =======================================================

@router.callback_query(F.data == "journal_submit_order")
async def submit_order_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    await callback.answer()
    try: await callback.message.delete()
    except: pass
    await finalize_order(callback.message.chat, state, bot, callback.message, db)

async def finalize_order(user_obj, state: FSMContext, bot: Bot, message_obj, db: Database):
    data = await state.get_data()
    summary = data.get('final_summary', 'Нет данных')
    
    # 1. Сохраняем заказ в базу
    order = Order(
        user_id=user_obj.id,
        category="Журналы",
        params=data,
        description=summary
    )
    order_id = await db.create_order(order)
    
    # 2. Уведомляем админов
    admin_ids = [x.strip() for x in os.getenv("ADMIN_ID", "").split(",") if x.strip()]
    manager_ids = await db.get_managers()
    all_notif_ids = list(set(admin_ids + [str(mid) for mid in manager_ids]))
    
    db_user = await db.get_user(user_obj.id)
    client_name = db_user.full_name if db_user else user_obj.first_name
    client_phone = db_user.phone if db_user else "-"
    username = f"(@{user_obj.username})" if getattr(user_obj, 'username', None) else ""

    admin_text = (
        f"⚡️ <b>НОВЫЙ ЗАКАЗ #{order_id} (Журналы)</b>\n"
        f"👤 {client_name} {username}\n"
        f"📞 {client_phone}\n\n"
        f"{summary}"
    )
    
    for adm in all_notif_ids:
        try: await bot.send_message(chat_id=adm, text=admin_text, parse_mode="HTML")
        except: pass

    # 3. Ответ пользователю
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="main_profile")],
        [InlineKeyboardButton(text="🏗 В каталог товаров", callback_data="main_constructor")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])
    await message_obj.answer(f"✅ <b>Заказ #{order_id} отправлен!</b>\nМенеджер скоро свяжется с вами.", reply_markup=kb, parse_mode="HTML")
