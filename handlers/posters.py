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
from handlers.common import send_order_to_managers

router = Router()

# =======================================================
# 🛠 НАСТРОЙКИ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =======================================================

TOTAL_STEPS = 7

class CalcPosters(StatesGroup):
    step_format = State()         # 1. Формат (стандарт или свой размер)
    step_custom_width = State()   # Ввод своей ширины
    step_custom_height = State()  # Ввод своей высоты
    
    step_paper_type = State()     # 2. Тип бумаги
    step_paper_weight = State()   # 3. Плотность бумаги
    step_color = State()          # 4. Красочность
    step_coating = State()        # 5. Доп. покрытие
    step_processing = State()     # 6. Обработка
    step_circulation = State()    # 7. Тираж

    # Данные для регистрации
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
    progress = get_progress_bar(current_step, TOTAL_STEPS)
    
    lines = []
    if current_step > 1: lines.append(f"📏 Формат: <b>{data.get('format', '???')}</b>")
    if current_step > 2: lines.append(f"📄 Бумага: <b>{data.get('p_type', '???')}</b>")
    if current_step > 3: lines.append(f"⚖️ Плотность: <b>{data.get('paper', '???')}</b>")
    if current_step > 4: lines.append(f"🎨 Цвет: <b>{data.get('color', '???')}</b>")
    if current_step > 5: lines.append(f"✨ Покрытие: <b>{data.get('coating', '???')}</b>")
    if current_step > 6: lines.append(f"⚙️ Обработка: <b>{data.get('processing', '???')}</b>")
    if current_step > 7: lines.append(f"🔢 Тираж: <b>{data.get('count', '???')} шт.</b>")
    
    history = ("📝 <b>Ваш заказ:</b>\n" + "\n".join(lines) + "\n➖➖➖➖➖➖➖➖\n") if lines else ""
    return progress + history

async def smart_edit(message: types.Message, text: str, kb: InlineKeyboardMarkup):
    """Умное редактирование сообщения"""
    try:
        if message.photo:
            await message.delete()
            await message.answer(text=text, reply_markup=kb, parse_mode="HTML")
        else:
            await message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await message.answer(text=text, reply_markup=kb, parse_mode="HTML")

async def show_help(callback: types.CallbackQuery, text: str, back_callback: str):
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Понятно, вернуться", callback_data=back_callback)]])
    await smart_edit(callback.message, text, kb)

# =======================================================
# 1️⃣ ШАГ 1: ФОРМАТ
# =======================================================

@router.callback_query(F.data.in_({"prod_Плакаты", "calc_posters_start"}))
async def step_1_format(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(CalcPosters.step_format)
    
    text = (
        f"{get_breadcrumbs({}, 1)}"
        "📐 <b>Шаг 1. Формат плаката</b>\n"
        "Выберите стандартный размер или укажите свои параметры.\n\n"
        "• <b>А2</b> (420×594 мм) — классика афиш\n"
        "• <b>А3</b> (297×420 мм) — инфо-стенды\n"
        "• <b>А4</b> (210×297 мм) — объявления\n"
        "• <b>210×98 мм</b> — евро-формат"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="А2 (420×594)", callback_data="pos_fmt_A2"),
         InlineKeyboardButton(text="А3 (297×420)", callback_data="pos_fmt_A3")],
        [InlineKeyboardButton(text="А4 (210×297)", callback_data="pos_fmt_A4"),
         InlineKeyboardButton(text="А5 (148×210)", callback_data="pos_fmt_A5")],
        [InlineKeyboardButton(text="А6 (105×148)", callback_data="pos_fmt_A6"),
         InlineKeyboardButton(text="А7 (74×105)", callback_data="pos_fmt_A7")],
        [InlineKeyboardButton(text="📐 210×98", callback_data="pos_fmt_210x98"),
         InlineKeyboardButton(text="📏 Свой размер", callback_data="pos_fmt_custom")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_pos_fmt"),
         InlineKeyboardButton(text="🔙 В меню", callback_data="main_constructor")]
    ])
    
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "help_pos_fmt")
async def help_fmt(callback: types.CallbackQuery):
    await show_help(callback, 
        "<b>Как выбрать формат?</b>\n\n"
        "🏢 <b>А2 и А3</b> — лучше всего подходят для настенного размещения, они заметны издалека.\n"
        "📄 <b>А4 и А5</b> — идеальны для информационных листков и прайсов на уровне глаз.\n"
        "📏 <b>Свой размер</b> — если вам нужен нестандартный крой под конкретную рамку или нишу.", 
        "calc_posters_start")

# --- ЛОГИКА СВОЕГО РАЗМЕРА ---

@router.callback_query(CalcPosters.step_format, F.data == "pos_fmt_custom")
async def custom_fmt_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CalcPosters.step_custom_width)
    await callback.message.edit_text("📐 <b>Введите ширину</b> изделия в мм (только число):", 
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="calc_posters_start")]]))

@router.message(CalcPosters.step_custom_width)
async def process_custom_width(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Введите числовое значение (мм).")
        return
    await state.update_data(c_width=message.text)
    await state.set_state(CalcPosters.step_custom_height)
    await message.answer("📐 <b>Введите высоту</b> изделия в мм (только число):")

@router.message(CalcPosters.step_custom_height)
async def process_custom_height(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Введите числовое значение (мм).")
        return
    data = await state.get_data()
    w = data.get('c_width')
    h = message.text
    await state.update_data(format=f"{w}×{h} мм")
    await render_step_2(message, state)

@router.callback_query(CalcPosters.step_format, F.data.startswith("pos_fmt_"))
async def process_std_fmt(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    fmt = callback.data.replace("pos_fmt_", "")
    names = {"A2":"A2 (420×594)", "A3":"A3 (297×420)", "A4":"A4 (210×297)", "A5":"A5 (148×210)", "A6":"A6 (105×148)", "A7":"A7 (74×105)", "210x98":"210×98 мм"}
    await state.update_data(format=names.get(fmt, fmt))
    await render_step_2(callback.message, state)


# =======================================================
# 2️⃣ ШАГ 2: ТИП БУМАГИ
# =======================================================

async def render_step_2(message: types.Message, state: FSMContext):
    await state.set_state(CalcPosters.step_paper_type)
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 2)}"
        "📄 <b>Шаг 2. Выберите тип бумаги</b>\n"
        "От материала зависит, как будут выглядеть цвета и насколько долговечным будет плакат."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Мелованная", callback_data="pos_pt_Мелованная"),
         InlineKeyboardButton(text="📝 Офсетная", callback_data="pos_pt_Офсетная")],
        [InlineKeyboardButton(text="📦 Картон", callback_data="pos_pt_Картон"),
         InlineKeyboardButton(text="🎞 Самоклейка", callback_data="pos_pt_Самоклейка")],
        [InlineKeyboardButton(text="🌿 Крафт", callback_data="pos_pt_Крафт"),
         InlineKeyboardButton(text="👑 Дизайнерская", callback_data="pos_pt_Дизайнерская")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_pos_pt"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="calc_posters_start")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "help_pos_pt")
async def help_pt(callback: types.CallbackQuery):
    await show_help(callback,
        "<b>Краткий гид по бумаге:</b>\n\n"
        "✨ <b>Мелованная</b> — гладкая, идеальна для фото и яркой рекламы.\n"
        "📝 <b>Офсетная</b> — обычная бумага, на ней удобно писать, цвета более приглушенные.\n"
        "🎞 <b>Самоклейка</b> — если плакат нужно наклеить на стену или витрину.\n"
        "👑 <b>Дизайнерская</b> — подчеркнет статус, имеет уникальную текстуру.",
        "pos_back_to_pt")

@router.callback_query(F.data == "pos_back_to_pt")
async def back_to_pt_handler(callback: types.CallbackQuery, state: FSMContext):
    await render_step_2(callback.message, state)

@router.callback_query(CalcPosters.step_paper_type, F.data.startswith("pos_pt_"))
async def process_pt(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    pt = callback.data.replace("pos_pt_", "")
    await state.update_data(p_type=pt)
    await render_step_3(callback.message, state)


# =======================================================
# 3️⃣ ШАГ 3: ПЛОТНОСТЬ БУМАГИ
# =======================================================

async def render_step_3(message: types.Message, state: FSMContext):
    await state.set_state(CalcPosters.step_paper_weight)
    data = await state.get_data()
    pt = data.get('p_type')
    
    weights = []
    if pt in ["Мелованная"]:
        weights = ["90", "115", "130", "150", "170", "200", "250", "300", "350"]
    elif pt == "Офсетная":
        weights = ["80", "100", "120", "160", "190"]
    elif pt == "Картон":
        weights = ["215", "235", "250", "270", "300"]
    elif pt == "Крафт":
        weights = ["80", "120", "200"]
    else:
        await state.update_data(paper="Стандарт")
        await render_step_4(message, state)
        return

    text = (
        f"{get_breadcrumbs(data, 3)}"
        f"⚖️ <b>Шаг 3. Плотность ({pt})</b>\n"
        "Выберите толщину материала. Чем выше граммовка, тем жестче будет изделие."
    )
    
    buttons = []
    row = []
    for w in weights:
        row.append(InlineKeyboardButton(text=f"{w} г", callback_data=f"pos_pw_{w}"))
        if len(row) == 3:
            buttons.append(row); row = []
    if row: buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_pos_pw")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="pos_back_to_pt")])
    await smart_edit(message, text, InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "help_pos_pw")
async def help_pw(callback: types.CallbackQuery):
    await show_help(callback,
        "<b>Как выбрать плотность?</b>\n\n"
        "🔹 <b>90-115 г/м²</b> — тонкая бумага, подходит для массовой расклейки.\n"
        "🔹 <b>130-170 г/м²</b> — стандарт для качественного плаката.\n"
        "🔹 <b>200-300 г/м²</b> — плотная бумага, почти картон, долго сохраняет вид.",
        "pos_back_to_pw")

@router.callback_query(F.data == "pos_back_to_pw")
async def back_to_pw_handler(callback: types.CallbackQuery, state: FSMContext):
    await render_step_3(callback.message, state)

@router.callback_query(CalcPosters.step_paper_weight, F.data.startswith("pos_pw_"))
async def process_pw(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    w = callback.data.replace("pos_pw_", "")
    await state.update_data(paper=f"{w} г/м²")
    await render_step_4(callback.message, state)


# =======================================================
# 4️⃣ ШАГ 4: КРАСОЧНОСТЬ
# =======================================================

async def render_step_4(message: types.Message, state: FSMContext):
    await state.set_state(CalcPosters.step_color)
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 4)}"
        "🎨 <b>Шаг 4. Красочность печати</b>\n"
        "Выберите количество цветов. Первая цифра — лицо, вторая — оборот.\n"
        "<i>«К» — печать кроющим цветом (например, белым или Pantone).</i>"
    )
    
    colors = [
        "5+5", "4+4", "3+3", "2+2", "1+1", "К+К",
        "5+0", "4+0", "3+0", "2+0", "1+0", "К+0"
    ]
    
    buttons = []
    row = []
    for c in colors:
        row.append(InlineKeyboardButton(text=c, callback_data=f"pos_col_{c}"))
        if len(row) == 3:
            buttons.append(row); row = []
    if row: buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_pos_col")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="pos_back_to_pw")])
    await smart_edit(message, text, InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "help_pos_col")
async def help_col(callback: types.CallbackQuery):
    await show_help(callback,
        "<b>Справка по цветности:</b>\n\n"
        "🎨 <b>4+0</b> — полноцветная печать с одной стороны (самый частый выбор).\n"
        "🎨 <b>4+4</b> — полноцветная печать с двух сторон.\n"
        "⚫️ <b>1+0</b> — печать в один черный цвет.\n"
        "⚪️ <b>К+0</b> — печать спеццветом (золото, серебро, белила).",
        "pos_back_to_col")

@router.callback_query(F.data == "pos_back_to_col")
async def back_to_col_handler(callback: types.CallbackQuery, state: FSMContext):
    await render_step_4(callback.message, state)

@router.callback_query(CalcPosters.step_color, F.data.startswith("pos_col_"))
async def process_col(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    c = callback.data.replace("pos_col_", "")
    await state.update_data(color=c)
    await render_step_5(callback.message, state)


# =======================================================
# 5️⃣ ШАГ 5: ДОП. ПОКРЫТИЕ (МУЛЬТИВЫБОР)
# =======================================================

def kb_coating(sel):
    def t(l, k): return f"✅ {l}" if k in sel else l
    kb = [
        [InlineKeyboardButton(text=t("Без покрытия", "Нет"), callback_data="pos_coat_toggle_Нет")],
        [InlineKeyboardButton(text=t("Лам. Глянец (1-ст)", "Лам_Гл_1"), callback_data="pos_coat_toggle_Лам_Гл_1"),
         InlineKeyboardButton(text=t("Лам. Глянец (2-ст)", "Лам_Гл_2"), callback_data="pos_coat_toggle_Лам_Гл_2")],
        [InlineKeyboardButton(text=t("Лам. Матовая (1-ст)", "Лам_Мат_1"), callback_data="pos_coat_toggle_Лам_Мат_1"),
         InlineKeyboardButton(text=t("Лам. Матовая (2-ст)", "Лам_Мат_2"), callback_data="pos_coat_toggle_Лам_Мат_2")],
        [InlineKeyboardButton(text=t("Лак офсетный", "Лак_Офс"), callback_data="pos_coat_toggle_Лак_Офс"),
         InlineKeyboardButton(text=t("УФ-лак", "УФ_Лак"), callback_data="pos_coat_toggle_УФ_Лак")],
        [InlineKeyboardButton(text=t("Тиснение фольгой", "Тиснение"), callback_data="pos_coat_toggle_Тиснение")]
    ]
    if sel and "Нет" not in sel:
        kb.append([InlineKeyboardButton(text="➡️ Продолжить", callback_data="pos_coat_done")])
    
    kb.append([InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_pos_coat"),
               InlineKeyboardButton(text="🔙 Назад", callback_data="pos_back_to_col")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def render_step_5(message: types.Message, state: FSMContext):
    await state.set_state(CalcPosters.step_coating)
    data = await state.get_data()
    sel = data.get("coat_list", [])
    text = (
        f"{get_breadcrumbs(data, 5)}"
        "✨ <b>Шаг 5. Дополнительное покрытие</b>\n"
        "Защитите свой плакат или добавьте ему премиальный блеск."
    )
    await smart_edit(message, text, kb_coating(sel))

@router.callback_query(F.data == "help_pos_coat")
async def help_coat(callback: types.CallbackQuery):
    await show_help(callback,
        "<b>Зачем нужно покрытие?</b>\n\n"
        "🛡 <b>Ламинация</b> — защищает от влаги и царапин, делает бумагу прочнее.\n"
        "💧 <b>УФ-лак</b> — выделяет детали блеском, создает эффект объема.\n"
        "✨ <b>Тиснение</b> — придает металлический блеск (золото/серебро) логотипам.",
        "pos_back_to_coat")

@router.callback_query(F.data == "pos_back_to_coat")
async def back_to_coat_handler(callback: types.CallbackQuery, state: FSMContext):
    await render_step_5(callback.message, state)

@router.callback_query(CalcPosters.step_coating, F.data.startswith("pos_coat_toggle_"))
async def toggle_coat(callback: types.CallbackQuery, state: FSMContext):
    item = callback.data.replace("pos_coat_toggle_", "")
    data = await state.get_data()
    sel = data.get("coat_list", [])
    
    if item == "Нет":
        await state.update_data(coat_list=["Нет"], coating="Без покрытия")
        await render_step_6(callback.message, state)
        return
    
    if "Нет" in sel: sel.remove("Нет")
    
    if item in sel: sel.remove(item)
    else: sel.append(item)
    
    await state.update_data(coat_list=sel, coating=", ".join(sel) if sel else "Не выбрано")
    try: await callback.message.edit_reply_markup(reply_markup=kb_coating(sel))
    except: pass
    await callback.answer()

@router.callback_query(F.data == "pos_coat_done")
async def coat_done(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_6(callback.message, state)


# =======================================================
# 6️⃣ ШАГ 6: ОБРАБОТКА (МУЛЬТИВЫБОР)
# =======================================================

def kb_proc(sel):
    def t(l, k): return f"✅ {l}" if k in sel else l
    kb = [
        [InlineKeyboardButton(text=t("Без обработки", "Нет"), callback_data="pos_proc_toggle_Нет")],
        [InlineKeyboardButton(text=t("Фальцовка (сгиб)", "Фальцовка"), callback_data="pos_proc_toggle_Фальцовка"),
         InlineKeyboardButton(text=t("Биговка", "Биговка"), callback_data="pos_proc_toggle_Биговка")],
        [InlineKeyboardButton(text=t("Перфорация", "Перфорация"), callback_data="pos_proc_toggle_Перфорация"),
         InlineKeyboardButton(text=t("Скругление углов", "Скругление"), callback_data="pos_proc_toggle_Скругление")],
        [InlineKeyboardButton(text=t("Нумерация", "Нумерация"), callback_data="pos_proc_toggle_Нумерация"),
         InlineKeyboardButton(text=t("Вырубка", "Вырубка"), callback_data="pos_proc_toggle_Вырубка")]
    ]
    if sel and "Нет" not in sel:
        kb.append([InlineKeyboardButton(text="➡️ Продолжить", callback_data="pos_proc_done")])
    
    kb.append([InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_pos_proc"),
               InlineKeyboardButton(text="🔙 Назад", callback_data="pos_back_to_coat")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def render_step_6(message: types.Message, state: FSMContext):
    await state.set_state(CalcPosters.step_processing)
    data = await state.get_data()
    sel = data.get("proc_list", [])
    text = (
        f"{get_breadcrumbs(data, 6)}"
        "⚙️ <b>Шаг 6. Послепечатная обработка</b>\n"
        "Выберите дополнительные операции с вашим изделием."
    )
    await smart_edit(message, text, kb_proc(sel))

@router.callback_query(F.data == "help_pos_proc")
async def help_proc(callback: types.CallbackQuery):
    await show_help(callback,
        "<b>Виды обработки:</b>\n\n"
        "📂 <b>Фальцовка</b> — складывание плаката (например, в буклет).\n"
        "🎟 <b>Перфорация</b> — линия отрыва для купона.\n"
        "🫧 <b>Скругление</b> — делает углы аккуратными и долговечными.\n"
        "🔢 <b>Нумерация</b> — если нужен учет каждого экземпляра.",
        "pos_back_to_proc")

@router.callback_query(F.data == "pos_back_to_proc")
async def back_to_proc_handler(callback: types.CallbackQuery, state: FSMContext):
    await render_step_6(callback.message, state)

@router.callback_query(CalcPosters.step_processing, F.data.startswith("pos_proc_toggle_"))
async def toggle_proc(callback: types.CallbackQuery, state: FSMContext):
    item = callback.data.replace("pos_proc_toggle_", "")
    data = await state.get_data()
    sel = data.get("proc_list", [])
    
    if item == "Нет":
        await state.update_data(proc_list=["Нет"], processing="Без обработки")
        await render_step_7(callback.message, state)
        return
    
    if "Нет" in sel: sel.remove("Нет")
    
    if item in sel: sel.remove(item)
    else: sel.append(item)
    
    await state.update_data(proc_list=sel, processing=", ".join(sel) if sel else "Не выбрано")
    try: await callback.message.edit_reply_markup(reply_markup=kb_proc(sel))
    except: pass
    await callback.answer()

@router.callback_query(F.data == "pos_proc_done")
async def proc_done(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_7(callback.message, state)


# =======================================================
# 7️⃣ ШАГ 7: ТИРАЖ
# =======================================================

async def render_step_7(message: types.Message, state: FSMContext):
    await state.set_state(CalcPosters.step_circulation)
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 7)}"
        "🔢 <b>Шаг 7. Тираж</b>\n"
        "Укажите необходимое количество. Выберите из списка или введите число вручную."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1", callback_data="pos_cnt_1"),
         InlineKeyboardButton(text="5", callback_data="pos_cnt_5"),
         InlineKeyboardButton(text="10", callback_data="pos_cnt_10")],
        [InlineKeyboardButton(text="50", callback_data="pos_cnt_50"),
         InlineKeyboardButton(text="100", callback_data="pos_cnt_100")],
        [InlineKeyboardButton(text="500", callback_data="pos_cnt_500"),
         InlineKeyboardButton(text="1000", callback_data="pos_cnt_1000")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="pos_back_to_proc")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(CalcPosters.step_circulation, F.data.startswith("pos_cnt_"))
async def process_cnt_btn(callback: types.CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    await callback.answer()
    cnt = callback.data.replace("pos_cnt_", "")
    await state.update_data(count=cnt)
    await step_final_summary(callback.message, state, db, bot)

@router.message(CalcPosters.step_circulation)
async def process_cnt_text(message: types.Message, state: FSMContext, db: Database, bot: Bot):
    if not message.text.isdigit():
        await message.answer("⚠️ Введите числовое значение.")
        return
    await state.update_data(count=message.text)
    await step_final_summary(message, state, db, bot)


# =======================================================
# 🏁 ФИНАЛ: ПРОВЕРКА И ОТПРАВКА
# =======================================================

async def step_final_summary(message: types.Message, state: FSMContext, db: Database, bot: Bot):
    data = await state.get_data()
    
    summary = (
        f"🧾 <b>ПРОВЕРКА ДАННЫХ: ПЛАКАТЫ</b>\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"📏 Формат: <b>{data.get('format')}</b>\n"
        f"📄 Бумага: <b>{data.get('p_type')}</b>\n"
        f"⚖️ Плотность: <b>{data.get('paper')}</b>\n"
        f"🎨 Цвет: <b>{data.get('color')}</b>\n"
        f"✨ Покрытие: <b>{data.get('coating')}</b>\n"
        f"⚙️ Обработка: <b>{data.get('processing')}</b>\n"
        f"🔢 Тираж: <b>{data.get('count')} шт.</b>"
    )
    
    await state.update_data(final_summary=summary)
    user_id = message.chat.id
    profile = await db.get_user(user_id)
    
    is_profile_complete = (profile and profile.full_name and profile.phone and profile.city and profile.address)
    
    if is_profile_complete:
        text = (
            "🏁 <b>Почти готово! Проверьте ваш заказ</b>\n\n"
            f"{summary}\n\n"
            "Менеджер рассчитает стоимость и ответит вам здесь."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 ОТПРАВИТЬ МЕНЕДЖЕРУ", callback_data="pos_submit")],
            [InlineKeyboardButton(text="🔄 Изменить параметры", callback_data="calc_posters_start")]
        ])
    else:
        text = (
            "🏁 <b>Ваш заказ сформирован!</b>\n\n"
            f"{summary}\n\n"
            "➖➖➖➖➖➖➖➖\n"
            "👋 <b>Давайте знакомиться!</b>\n"
            "Нужно один раз заполнить контакты, чтобы менеджер мог связаться с вами."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 ЗАПОЛНИТЬ И ОТПРАВИТЬ", callback_data="pos_reg_start")],
            [InlineKeyboardButton(text="🔄 Начать сначала", callback_data="calc_posters_start")]
        ])
    
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

# --- РЕГИСТРАЦИЯ И ЗАПИСЬ ---

@router.callback_query(F.data == "pos_reg_start")
async def reg_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CalcPosters.reg_name)
    await callback.message.answer("✍️ Введите ваше <b>Имя</b>:", parse_mode="HTML")

@router.message(CalcPosters.reg_name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(reg_name=message.text)
    await state.set_state(CalcPosters.reg_phone)
    await message.answer("📞 Введите ваш <b>Телефон</b>:", parse_mode="HTML")

@router.message(CalcPosters.reg_phone)
async def reg_phone(message: types.Message, state: FSMContext):
    await state.update_data(reg_phone=message.text)
    await state.set_state(CalcPosters.reg_city)
    await message.answer("🏙 Введите ваш <b>Город</b>:", parse_mode="HTML")

@router.message(CalcPosters.reg_city)
async def reg_city(message: types.Message, state: FSMContext):
    await state.update_data(reg_city=message.text)
    await state.set_state(CalcPosters.reg_address)
    await message.answer("🚚 Введите <b>Адрес доставки</b>:", parse_mode="HTML")

@router.message(CalcPosters.reg_address)
async def reg_address(message: types.Message, state: FSMContext, bot: Bot, db: Database):
    data = await state.get_data()
    await db.update_user_profile(message.chat.id, full_name=data['reg_name'], phone=data['reg_phone'], city=data['reg_city'], address=message.text)
    await message.answer("✅ Контакты сохранены! Отправляем заказ...")
    await finalize_order(message.chat, state, bot, message, db)

@router.callback_query(F.data == "pos_submit")
async def submit_order_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    await callback.answer()
    await finalize_order(callback.message.chat, state, bot, callback.message, db)

async def finalize_order(user_obj, state: FSMContext, bot: Bot, message_obj, db: Database):
    data = await state.get_data()
    summary = data.get('final_summary', '')
    
    order = Order(
        user_id=user_obj.id,
        category="Плакаты",
        params=data,
        description=summary
    )
    
    order_id = await db.create_order(order)
    await send_order_to_managers(order_id, user_obj.id, summary, "Плакаты", bot, db)
    await state.clear()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="main_profile")],
        [InlineKeyboardButton(text="🏗 В каталог товаров", callback_data="main_constructor")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])
    
    await message_obj.answer(
        f"🎉 <b>Заказ #{order_id} отправлен!</b>\n\n"
        "Менеджер скоро свяжется с вами для подтверждения стоимости.",
        reply_markup=kb,
        parse_mode="HTML"
    )
