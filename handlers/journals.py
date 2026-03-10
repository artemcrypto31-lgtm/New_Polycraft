from aiogram import Router, F, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
import os
import json
from datetime import datetime

from database import Database
from models import Order, User

router = Router()

# =======================================================
# 🛠 НАСТРОЙКИ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
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

def get_progress_bar(current: int, total: int) -> str:
    """Рисует визуальную полоску прогресса"""
    filled = int((current / total) * 10)
    bar = "▰" * filled + "▱" * (10 - filled)
    percent = int((current / total) * 100)
    return f"📊 <b>Шаг {current} из {total}</b> [{bar}] {percent}%\n\n"

def get_breadcrumbs(data: dict, current_step: int) -> str:
    """Генерирует прогресс-бар и историю выбора пользователя"""
    total_steps = 13
    progress = get_progress_bar(current_step, total_steps)
    
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

    history = ("📝 <b>Ваш заказ:</b>\n\n" + "\n\n".join(sections) + "\n➖➖➖➖➖➖➖➖\n") if sections else ""
    return progress + history

async def smart_edit(message: types.Message, text: str, kb: InlineKeyboardMarkup):
    """Умное редактирование сообщения (удаляет фото, если оно было)"""
    try:
        if message.photo:
            await message.delete()
            await message.answer(text=text, reply_markup=kb, parse_mode="HTML")
        else:
            await message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await message.answer(text=text, reply_markup=kb, parse_mode="HTML")

# =======================================================
# 1️⃣ ШАГ 1: ТИРАЖ
# =======================================================

@router.callback_query(F.data.in_({"prod_Журналы", "calc_journal_start"}))
async def step_1_quantity(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(JournalCalc.step_quantity)
    
    text = (
        f"{get_breadcrumbs({}, 1)}"
        "🔢 <b>Шаг 1. Тираж</b>\n"
        "Введите количество (числом) или выберите из списка ниже.\n\n"
        "<i>Чем больше тираж — тем дешевле стоимость за 1 экземпляр.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50", callback_data="j_qty_50"), 
         InlineKeyboardButton(text="100", callback_data="j_qty_100"), 
         InlineKeyboardButton(text="200", callback_data="j_qty_200")],
        [InlineKeyboardButton(text="300", callback_data="j_qty_300"), 
         InlineKeyboardButton(text="500", callback_data="j_qty_500"), 
         InlineKeyboardButton(text="1000", callback_data="j_qty_1000")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="j_help_1")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cat_promo")]
    ])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "j_help_1")
async def help_1(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "<b>Справка: Тираж</b>\n\n"
        "Количество экземпляров напрямую влияет на технологию и цену:\n"
        "• <b>До 300 шт:</b> Обычно используется цифровая печать. Это быстро, удобно для малых партий.\n"
        "• <b>От 500 шт:</b> Включается офсетная печать. Цена за штуку падает в разы, так как затраты на подготовку распределяются на весь объем."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться", callback_data="calc_journal_start")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(JournalCalc.step_quantity, F.data.startswith("j_qty_"))
async def process_qty_btn(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(quantity=int(callback.data.split("_")[2]))
    await callback.answer()
    await render_step_2(callback.message, state)

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
    await render_step_2(message, state)


# =======================================================
# 2️⃣ ШАГ 2: ФОРМАТ
# =======================================================

async def render_step_2(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_format)
    data = await state.get_data()
    text = f"{get_breadcrumbs(data, 2)}📏 <b>Шаг 2. Выберите формат журнала</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="А4 (210x297)", callback_data="j_fmt_A4"), 
         InlineKeyboardButton(text="А5 (148x210)", callback_data="j_fmt_A5")],
        [InlineKeyboardButton(text="А6 (105x148)", callback_data="j_fmt_A6"), 
         InlineKeyboardButton(text="165х240", callback_data="j_fmt_Crown")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="j_help_2")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="calc_journal_start")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "j_help_2")
async def help_2(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "<b>Справка: Форматы</b>\n\n"
        "🔹 <b>А4:</b> Классический альбомный лист. Идеален для глянца, презентаций и каталогов.\n"
        "🔹 <b>А5:</b> Половина А4. Самый популярный формат для методичек и небольших журналов.\n"
        "🔹 <b>А6:</b> Карманный формат для блокнотов или мини-инструкций.\n"
        "🔹 <b>165х240:</b> «Королевский» формат. Выглядит дороже и статуснее стандартных размеров."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться", callback_data="j_back_2")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "j_back_2")
async def back_2(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_2(callback.message, state)

@router.callback_query(JournalCalc.step_format, F.data.startswith("j_fmt_"))
async def process_fmt(callback: types.CallbackQuery, state: FSMContext):
    code = callback.data.split("_")[2]
    names = {"A4":"А4", "A5":"А5", "A6":"А6", "Crown":"165х240 мм"}
    await state.update_data(format_code=code, format_name=names.get(code, code))
    await callback.answer()
    await render_step_3(callback.message, state)


# =======================================================
# 3️⃣ ШАГ 3: ОРИЕНТАЦИЯ
# =======================================================

async def render_step_3(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_orientation)
    data = await state.get_data()
    text = f"{get_breadcrumbs(data, 3)}🔄 <b>Шаг 3. Ориентация</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↕️ Вертикальная", callback_data="j_orient_vert"), 
         InlineKeyboardButton(text="↔️ Горизонтальная", callback_data="j_orient_horiz")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="j_help_3")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="j_back_2")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "j_help_3")
async def help_3(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "<b>Справка: Ориентация</b>\n\n"
        "↕️ <b>Вертикальная:</b> Переплет по длинной стороне. Классика для большинства изданий.\n\n"
        "↔️ <b>Горизонтальная:</b> Переплет по короткой стороне. Отлично подходит для портфолио, фотоальбомов и чертежей."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться", callback_data="j_back_3")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "j_back_3")
async def back_3(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_3(callback.message, state)

@router.callback_query(JournalCalc.step_orientation, F.data.startswith("j_orient_"))
async def process_orient(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(orientation="Вертикальная" if "vert" in callback.data else "Горизонтальная")
    await callback.answer()
    await render_step_4(callback.message, state)


# =======================================================
# 4️⃣ ШАГ 4: ТИП ПЕРЕПЛЕТА
# =======================================================

async def render_step_4(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_cover_type)
    data = await state.get_data()
    text = f"{get_breadcrumbs(data, 4)}📕 <b>Шаг 4. Тип переплета</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📕 Мягкий", callback_data="j_cov_soft"), 
         InlineKeyboardButton(text="📘 Твердый (7БЦ)", callback_data="j_cov_hard")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="j_help_4")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="j_back_3")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "j_help_4")
async def help_4(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "<b>Справка: Переплет</b>\n\n"
        "📕 <b>Мягкий:</b> Гибкая обложка из плотной бумаги. Экономично, быстро, идеально для журналов.\n\n"
        "📘 <b>Твердый:</b> Обложка на жестком картоне. Долговечно, премиально, защищает блок от повреждений."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться", callback_data="j_back_4")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "j_back_4")
async def back_4(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_4(callback.message, state)

@router.callback_query(JournalCalc.step_cover_type, F.data.startswith("j_cov_"))
async def process_cov_type(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(cover_type="Мягкий" if "soft" in callback.data else "Твердый")
    await callback.answer()
    await render_step_5(callback.message, state)


# =======================================================
# 5️⃣ ШАГ 5: СКРЕПЛЕНИЕ
# =======================================================

async def render_step_5(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_binding)
    data = await state.get_data()
    text = f"{get_breadcrumbs(data, 5)}🔗 <b>Шаг 5. Способ скрепления</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Скоба", callback_data="j_bind_staple"), 
         InlineKeyboardButton(text="➰ Пружина", callback_data="j_bind_wire")],
        [InlineKeyboardButton(text="📚 Клей (КБС)", callback_data="j_bind_glue")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="j_help_5")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="j_back_4")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "j_help_5")
async def help_5(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "<b>Справка: Скрепление</b>\n\n"
        "📎 <b>Скоба:</b> Просто и надежно. Оптимально до 60 страниц.\n\n"
        "➰ <b>Пружина:</b> Позволяет раскрывать журнал на 360 градусов. Удобно для блокнотов.\n\n"
        "📚 <b>Клей:</b> Плоский корешок как у книги. Выглядит солидно, подходит для большого объема страниц."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться", callback_data="j_back_5")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "j_back_5")
async def back_5(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_5(callback.message, state)

@router.callback_query(JournalCalc.step_binding, F.data.startswith("j_bind_"))
async def process_bind(callback: types.CallbackQuery, state: FSMContext):
    names = {"staple":"Скоба", "wire":"Пружина", "glue":"Клей (КБС)"}
    code = callback.data.split("_")[2]
    await state.update_data(binding=names.get(code, code))
    await callback.answer()
    await render_step_6(callback.message, state)


# =======================================================
# 6️⃣ ШАГ 6: БУМАГА ОБЛОЖКИ
# =======================================================

async def render_step_6(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_cover_paper)
    data = await state.get_data()
    text = f"{get_breadcrumbs(data, 6)}📄 <b>Шаг 6. Плотность обложки</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="150 г", callback_data="j_cp_150"), 
         InlineKeyboardButton(text="170 г", callback_data="j_cp_170"), 
         InlineKeyboardButton(text="200 г", callback_data="j_cp_200")],
        [InlineKeyboardButton(text="250 г", callback_data="j_cp_250"), 
         InlineKeyboardButton(text="300 г", callback_data="j_cp_300"), 
         InlineKeyboardButton(text="350 г", callback_data="j_cp_350")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="j_help_6")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="j_back_5")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "j_help_6")
async def help_6(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "<b>Справка: Плотность</b>\n\n"
        "• <b>150-170 г:</b> Тонкая обложка, похожа на плотную страницу.\n"
        "• <b>200-250 г:</b> Стандарт для журналов. Хороший баланс гибкости и прочности.\n"
        "• <b>300-350 г:</b> Очень плотная, как у открытки. Держит форму годами."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться", callback_data="j_back_6")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "j_back_6")
async def back_6(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_6(callback.message, state)

@router.callback_query(JournalCalc.step_cover_paper, F.data.startswith("j_cp_"))
async def process_cov_pap(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(cover_paper=callback.data.split("_")[2] + " г/м²")
    await callback.answer()
    await render_step_7(callback.message, state)


# =======================================================
# 7️⃣ ШАГ 7: КРАСОЧНОСТЬ ОБЛОЖКИ
# =======================================================

async def render_step_7(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_cover_color)
    data = await state.get_data()
    text = f"{get_breadcrumbs(data, 7)}🎨 <b>Шаг 7. Цвет обложки</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="4+0 (Лицо)", callback_data="j_cc_4+0"), 
         InlineKeyboardButton(text="4+4 (Все)", callback_data="j_cc_4+4")],
        [InlineKeyboardButton(text="1+1 (ЧБ)", callback_data="j_cc_1+1"), 
         InlineKeyboardButton(text="4+1 (Цв+ЧБ)", callback_data="j_cc_4+1")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="j_help_7")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="j_back_6")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "j_help_7")
async def help_7(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "<b>Справка: Цветность</b>\n\n"
        "🎨 <b>4+0:</b> Цветная печать только снаружи. Внутри — белая бумага.\n"
        "🎨 <b>4+4:</b> Цветная печать и снаружи, и на внутренних разворотах обложки.\n"
        "⚫️ <b>1+1:</b> Черно-белая печать с двух сторон."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться", callback_data="j_back_7")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "j_back_7")
async def back_7(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_7(callback.message, state)

@router.callback_query(JournalCalc.step_cover_color, F.data.startswith("j_cc_"))
async def process_cov_col(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(cover_color=callback.data.split("_")[2])
    await callback.answer()
    await render_step_8(callback.message, state)


# =======================================================
# 8️⃣ ШАГ 8: ОТДЕЛКА ОБЛОЖКИ (МУЛЬТИ)
# =======================================================

def kb_finish(sel):
    def t(l, k): return f"✅ {l}" if k in sel else l
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("Ламинация", "Ламинация"), callback_data="j_cf_toggle_Ламинация"),
         InlineKeyboardButton(text=t("Тиснение", "Тиснение"), callback_data="j_cf_toggle_Тиснение")],
        [InlineKeyboardButton(text=t("УФ-лак", "УФ-лак"), callback_data="j_cf_toggle_УФ-лак")],
        [InlineKeyboardButton(text="👉 Продолжить", callback_data="j_cf_done")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="j_help_8")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="j_back_7")]
    ])

async def render_step_8(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_cover_finish)
    data = await state.get_data()
    text = f"{get_breadcrumbs(data, 8)}✨ <b>Шаг 8. Отделка обложки</b>\n<i>(Можно выбрать несколько вариантов)</i>"
    await smart_edit(message, text, kb_finish(data.get("cover_finishes_list", [])))

@router.callback_query(F.data == "j_help_8")
async def help_8(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "<b>Справка: Отделка</b>\n\n"
        "✨ <b>Ламинация:</b> Пленка (матовая или глянец). Защищает от износа.\n"
        "🔥 <b>Тиснение:</b> Рельефный логотип или текст.\n"
        "💧 <b>УФ-лак:</b> Глянцевый блеск на отдельных элементах макета."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться", callback_data="j_back_8")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "j_back_8")
async def back_8(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_8(callback.message, state)

@router.callback_query(JournalCalc.step_cover_finish, F.data.startswith("j_cf_toggle_"))
async def toggle_finish(callback: types.CallbackQuery, state: FSMContext):
    item = callback.data.split("_")[3]
    d = await state.get_data()
    sel = d.get("cover_finishes_list", [])
    
    if item in sel: sel.remove(item)
    else: sel.append(item)
    
    await state.update_data(cover_finishes_list=sel)
    try: await callback.message.edit_reply_markup(reply_markup=kb_finish(sel))
    except: pass
    await callback.answer()

@router.callback_query(F.data == "j_cf_done")
async def finish_done(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(cover_finish_done=True)
    await callback.answer()
    await render_step_9(callback.message, state)


# =======================================================
# 9️⃣ ШАГ 9: СТРАНИЦЫ БЛОКА
# =======================================================

async def render_step_9(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_block_pages)
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 9)}"
        "📄 <b>Шаг 9. Страниц в блоке</b>\n\n"
        "Введите количество (минимум 4).\n"
        "❗️ <b>Число должно быть кратно 4</b> (4, 8, 12...)\n\n"
        "<i>Напишите в чат или выберите:</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="8", callback_data="j_p_8"), 
         InlineKeyboardButton(text="12", callback_data="j_p_12"), 
         InlineKeyboardButton(text="24", callback_data="j_p_24"), 
         InlineKeyboardButton(text="48", callback_data="j_p_48")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="j_help_9")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="j_back_8")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "j_help_9")
async def help_9(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "<b>Справка: Страницы</b>\n\n"
        "В полиграфии 1 лист = 4 страницы (полосы) при сгибе.\n"
        "Поэтому общее количество страниц в журнале всегда должно делиться на 4."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться", callback_data="j_back_9")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "j_back_9")
async def back_9(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_9(callback.message, state)

@router.callback_query(JournalCalc.step_block_pages, F.data.startswith("j_p_"))
async def process_pages_btn(callback: types.CallbackQuery, state: FSMContext):
    pages = int(callback.data.split("_")[2])
    await state.update_data(block_pages=pages)
    await callback.answer()
    await render_step_10(callback.message, state)

@router.message(JournalCalc.step_block_pages)
async def process_pages_text(message: types.Message, state: FSMContext):
    try: await message.delete()
    except: pass
    if not message.text.isdigit(): 
        await message.answer("⚠️ Введите только число!")
        return
    pages = int(message.text)
    if pages < 4 or pages % 4 != 0:
        await message.answer("⚠️ Минимум 4 страницы, число должно быть кратно 4!")
        return
    await state.update_data(block_pages=pages)
    await render_step_10(message, state)


# =======================================================
# 🔟 ШАГ 10: ЦВЕТ БЛОКА
# =======================================================

async def render_step_10(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_block_color)
    data = await state.get_data()
    text = f"{get_breadcrumbs(data, 10)}🎨 <b>Шаг 10. Печать внутри блока</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1+1 (ЧБ)", callback_data="j_bc_1+1"), 
         InlineKeyboardButton(text="2+2 (2 цвета)", callback_data="j_bc_2+2")],
        [InlineKeyboardButton(text="4+4 (Полноцвет)", callback_data="j_bc_4+4")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="j_help_10")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="j_back_9")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "j_help_10")
async def help_10(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "<b>Справка: Печать блока</b>\n\n"
        "⚫️ <b>1+1:</b> Только черная краска. Самый бюджетный вариант.\n"
        "🎨 <b>4+4:</b> Полноцветная печать всех страниц.\n"
        "🔴 <b>2+2:</b> Две краски (например, Черный + Пантон)."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться", callback_data="j_back_10")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "j_back_10")
async def back_10(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_10(callback.message, state)

@router.callback_query(JournalCalc.step_block_color, F.data.startswith("j_bc_"))
async def process_blk_col(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(block_color=callback.data.split("_")[2])
    await callback.answer()
    await render_step_11(callback.message, state)


# =======================================================
# 1️⃣1️⃣ ШАГ 11: ТИП БУМАГИ БЛОКА
# =======================================================

async def render_step_11(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_block_paper_type)
    data = await state.get_data()
    text = f"{get_breadcrumbs(data, 11)}📄 <b>Шаг 11. Вид бумаги внутри</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Офсетная", callback_data="j_bt_Offset")],
        [InlineKeyboardButton(text="✨ Меловка Глянец", callback_data="j_bt_Glossy"),
         InlineKeyboardButton(text="☁️ Меловка Мат", callback_data="j_bt_Matte")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="j_help_11")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="j_back_10")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "j_help_11")
async def help_11(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "<b>Справка: Бумага</b>\n\n"
        "📄 <b>Офсетная:</b> Привычная матовая бумага, на ней удобно писать.\n"
        "✨ <b>Мелованная:</b> Гладкая, «журнальная» бумага. Глянец блестит, Мат более сдержан."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться", callback_data="j_back_11")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "j_back_11")
async def back_11(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_11(callback.message, state)

@router.callback_query(JournalCalc.step_block_paper_type, F.data.startswith("j_bt_"))
async def process_blk_type(callback: types.CallbackQuery, state: FSMContext):
    names = {"Offset":"Офсетная", "Glossy":"Меловка Глянец", "Matte":"Меловка Мат"}
    code = callback.data.split("_")[2]
    await state.update_data(block_paper_type=names.get(code, code))
    await callback.answer()
    await render_step_12(callback.message, state)


# =======================================================
# 1️⃣2️⃣ ШАГ 12: ПЛОТНОСТЬ БЛОКА
# =======================================================

async def render_step_12(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_block_paper_weight)
    data = await state.get_data()
    ptype = data.get('block_paper_type', '')
    text = f"{get_breadcrumbs(data, 12)}📄 <b>Шаг 12. Плотность бумаги блока</b>\n(Выбрано: <i>{ptype}</i>)"
    
    buttons = []
    if "Офсетная" in ptype:
        buttons.append([InlineKeyboardButton(text="65 г", callback_data="j_bw_65"), InlineKeyboardButton(text="80 г", callback_data="j_bw_80")])
        buttons.append([InlineKeyboardButton(text="100 г", callback_data="j_bw_100"), InlineKeyboardButton(text="120 г", callback_data="j_bw_120")])
    else:
        buttons.append([InlineKeyboardButton(text="90 г", callback_data="j_bw_90"), InlineKeyboardButton(text="115 г", callback_data="j_bw_115"), InlineKeyboardButton(text="130 г", callback_data="j_bw_130")])
        buttons.append([InlineKeyboardButton(text="150 г", callback_data="j_bw_150"), InlineKeyboardButton(text="170 г", callback_data="j_bw_170"), InlineKeyboardButton(text="200 г", callback_data="j_bw_200")])
        buttons.append([InlineKeyboardButton(text="250 г", callback_data="j_bw_250")])
    
    buttons.append([InlineKeyboardButton(text="ℹ️ Справка", callback_data="j_help_12")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="j_back_11")])
    await smart_edit(message, text, InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "j_help_12")
async def help_12(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "<b>Справка: Плотность</b>\n\n"
        "• <b>65-80 г:</b> Тонкая бумага, как в книгах.\n"
        "• <b>115-150 г:</b> Стандарт для глянцевых страниц.\n"
        "• <b>170-250 г:</b> Очень плотная бумага для элитных изданий."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться", callback_data="j_back_12")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "j_back_12")
async def back_12(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_12(callback.message, state)

@router.callback_query(JournalCalc.step_block_paper_weight, F.data.startswith("j_bw_"))
async def process_blk_weight(callback: types.CallbackQuery, state: FSMContext):
    weight = callback.data.split("_")[2] + " г/м²"
    await state.update_data(block_paper_weight=weight)
    await callback.answer()
    await render_step_13(callback.message, state)


# =======================================================
# 1️⃣3️⃣ ШАГ 13: ДОП. УСЛУГИ (МУЛЬТИ)
# =======================================================

def kb_services(selected_list: list):
    def t(l, k): return f"✅ {l}" if k in selected_list else l
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("💻 Верстка", "Верстка"), callback_data="j_srv_toggle_Верстка"),
         InlineKeyboardButton(text=t("📖 ISBN", "ISBN"), callback_data="j_srv_toggle_ISBN")],
        [InlineKeyboardButton(text=t("📝 Корректор", "Корректор"), callback_data="j_srv_toggle_Корректор")],
        [InlineKeyboardButton(text="➡️ Рассчитать заказ", callback_data="j_srv_done")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="j_help_13")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="j_back_12")]
    ])

async def render_step_13(message: types.Message, state: FSMContext):
    await state.set_state(JournalCalc.step_services)
    data = await state.get_data()
    text = f"{get_breadcrumbs(data, 13)}🛠 <b>Шаг 13. Дополнительные услуги</b>"
    await smart_edit(message, text, kb_services(data.get("services_list", [])))

@router.callback_query(F.data == "j_help_13")
async def help_13(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "<b>Справка: Услуги</b>\n\n"
        "💻 <b>Верстка:</b> Создадим макет из ваших текстов и фото.\n"
        "📖 <b>ISBN:</b> Регистрация в Книжной палате (для продаж).\n"
        "📝 <b>Корректор:</b> Проверим текст на ошибки."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться", callback_data="j_back_13")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "j_back_13")
async def back_13(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_13(callback.message, state)

@router.callback_query(JournalCalc.step_services, F.data.startswith("j_srv_toggle_"))
async def toggle_service(callback: types.CallbackQuery, state: FSMContext):
    item = callback.data.split("_")[3]
    data = await state.get_data()
    sel = data.get("services_list", [])
    if item in sel: sel.remove(item)
    else: sel.append(item)
    await state.update_data(services_list=sel)
    try: await callback.message.edit_reply_markup(reply_markup=kb_services(sel))
    except: pass
    await callback.answer()


# =======================================================
# 🏁 ФИНАЛ: ПРОВЕРКА И ОТПРАВКА
# =======================================================

@router.callback_query(F.data == "j_srv_done")
async def step_finish_summary(callback: types.CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    await state.update_data(services_done=True)
    data = await state.get_data()
    
    summary_text = get_breadcrumbs(data, 13).split("➖➖➖➖➖➖➖➖")[0] + "➖➖➖➖➖➖➖➖"
    summary_text = summary_text.replace(get_progress_bar(13, 13), "🧾 <b>ПРОВЕРКА ДАННЫХ: ЖУРНАЛЫ</b>\n")
    
    await state.update_data(final_summary=summary_text)
    user_id = callback.message.chat.id
    profile = await db.get_user(user_id)

    is_complete = profile and profile.full_name and profile.phone and profile.city and profile.address

    if is_complete:
        text = f"🏁 <b>Почти готово! Проверьте ваш заказ</b>\n\n{summary_text}\n\n🚀 <b>Что дальше?</b>\nМенеджер свяжется с вами для расчета."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 ОТПРАВИТЬ МЕНЕДЖЕРУ", callback_data="j_submit")],
            [InlineKeyboardButton(text="🔄 Изменить параметры", callback_data="calc_journal_start")]
        ])
    else:
        text = f"🏁 <b>Ваш заказ сформирован!</b>\n\n{summary_text}\n\n👋 <b>Давайте знакомиться!</b>\nНужны контакты для связи."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 ПРЕДСТАВИТЬСЯ И ОТПРАВИТЬ", callback_data="j_reg_start")],
            [InlineKeyboardButton(text="🔄 Начать сначала", callback_data="calc_journal_start")]
        ])
    
    await smart_edit(callback.message, text, kb)

# --- РЕГИСТРАЦИЯ ---

@router.callback_query(F.data == "j_reg_start")
async def reg_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(JournalCalc.reg_name)
    await callback.message.answer("✍️ Введите ваше <b>Имя</b>:", parse_mode="HTML")

@router.message(JournalCalc.reg_name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(reg_name=message.text)
    await state.set_state(JournalCalc.reg_phone)
    await message.answer("📞 Введите ваш <b>Телефон</b>:", parse_mode="HTML")

@router.message(JournalCalc.reg_phone)
async def reg_phone(message: types.Message, state: FSMContext):
    await state.update_data(reg_phone=message.text)
    await state.set_state(JournalCalc.reg_city)
    await message.answer("🏙 Введите ваш <b>Город</b>:", parse_mode="HTML")

@router.message(JournalCalc.reg_city)
async def reg_city(message: types.Message, state: FSMContext):
    await state.update_data(reg_city=message.text)
    await state.set_state(JournalCalc.reg_address)
    await message.answer("🚚 Введите <b>Адрес доставки</b>:", parse_mode="HTML")

@router.message(JournalCalc.reg_address)
async def reg_address(message: types.Message, state: FSMContext, bot: Bot, db: Database):
    data = await state.get_data()
    await db.update_user_profile(message.chat.id, full_name=data['reg_name'], phone=data['reg_phone'], city=data['reg_city'], address=message.text)
    await message.answer("✅ Контакты сохранены! Отправляем заказ...")
    await finalize_order(message.chat, state, bot, message, db)

# --- ФИНАЛИЗАЦИЯ ---

@router.callback_query(F.data == "j_submit")
async def submit_order_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    await callback.answer()
    await finalize_order(callback.message.chat, state, bot, callback.message, db)

async def finalize_order(user_obj, state: FSMContext, bot: Bot, message_obj, db: Database):
    data = await state.get_data()
    
    order = Order(
        user_id=user_obj.id,
        category="Журналы",
        params=data,
        description=data.get('final_summary')
    )
    
    order_id = await db.create_order(order)
    admin_ids = [x.strip() for x in os.getenv("ADMIN_ID", "").split(",") if x.strip()]
    manager_ids = await db.get_managers()
    all_notif_ids = list(set(admin_ids + [str(mid) for mid in manager_ids]))
    
    db_user = await db.get_user(user_obj.id)
    username_str = f"(@{user_obj.username})" if hasattr(user_obj, 'username') and user_obj.username else ""

    admin_text = (
        f"⚡️ <b>НОВЫЙ ЗАКАЗ #{order_id} (Журналы)</b>\n"
        f"👤 {db_user.full_name} {username_str}\n"
        f"📞 {db_user.phone}\n\n"
        f"{data.get('final_summary')}"
    )
    
    for adm in all_notif_ids:
        try: await bot.send_message(chat_id=adm, text=admin_text, parse_mode="HTML")
        except: pass

    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="main_profile")],
        [InlineKeyboardButton(text="🏗 В каталог товаров", callback_data="main_constructor")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])
    
    await message_obj.answer(
        f"🎉 <b>Заказ #{order_id} успешно отправлен!</b>\n\n"
        "Менеджер уже получил уведомление и приступил к расчету.\n\n"
        "<b>Куда отправимся дальше?</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )
