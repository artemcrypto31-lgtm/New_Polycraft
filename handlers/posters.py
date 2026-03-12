from aiogram import Router, F, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import Database
from models import Order
from handlers.common import send_order_to_managers
from handlers.orders import kb_cat_promo, TEXT_PROMO

router = Router()

# =======================================================
# ⚙️ НАСТРОЙКИ И ЭКСПЕРТНАЯ ЛОГИКА
# =======================================================

TOTAL_STEPS = 7

class CalcPosters(StatesGroup):
    step_format = State()
    step_custom_size = State()
    step_paper_type = State()
    step_paper_weight = State()
    step_color = State()
    step_coating = State()
    step_processing = State()
    step_circulation = State()

    # Регистрация
    reg_name = State()
    reg_phone = State()
    reg_city = State()
    reg_address = State()

def get_progress_bar(current: int, total: int) -> str:
    filled = int((current / total) * 10)
    bar = "▰" * filled + "▱" * (10 - filled)
    percent = int((current / total) * 100)
    return f"📊 <b>Шаг {current} из {total}</b> [{bar}] {percent}%\n\n"

def get_breadcrumbs(data: dict, current_step: int) -> str:
    progress = get_progress_bar(current_step, TOTAL_STEPS)
    sections = []
    
    gen = []
    if current_step > 1: gen.append(f"• Формат: <b>{data.get('format', '???')}</b>")
    if gen: sections.append("📐 <b>ГЕОМЕТРИЯ:</b>\n" + "\n".join(gen))

    mat = []
    if current_step > 2: mat.append(f"• Тип: <b>{data.get('p_type', '???')}</b>")
    if current_step > 3: mat.append(f"• Плотность: <b>{data.get('paper', '???')}</b>")
    if current_step > 4: mat.append(f"• Цвет: <b>{data.get('color', '???')}</b>")
    if mat: sections.append("📄 <b>МАТЕРИАЛ И ПЕЧАТЬ:</b>\n" + "\n".join(mat))

    fin = []
    if current_step > 5: fin.append(f"• Покрытие: <b>{data.get('coating', '???')}</b>")
    if current_step > 6: fin.append(f"• Обработка: <b>{data.get('processing', '???')}</b>")
    if fin: sections.append("✨ <b>ОТДЕЛКА:</b>\n" + "\n".join(fin))

    if not sections: return progress
    return progress + "📝 <b>Текущая конфигурация:</b>\n\n" + "\n\n".join(sections) + "\n➖➖➖➖➖➖➖➖\n"

async def smart_edit(message: types.Message, text: str, kb: InlineKeyboardMarkup):
    try:
        await message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await message.answer(text=text, reply_markup=kb, parse_mode="HTML")

async def show_help(callback: types.CallbackQuery, text: str, back_callback: str):
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Понятно, вернуться", callback_data=back_callback)]])
    await smart_edit(callback.message, text, kb)

def build_summary_text(data: dict) -> str:
    return (f"🧾 <b>ИТОГО: ПЛАКАТЫ</b>\n"
            f"➖➖➖➖➖➖➖➖\n"
            f"📐 <b>ГЕОМЕТРИЯ:</b>\n"
            f"• Формат: <b>{data.get('format', '?')}</b>\n\n"
            f"📄 <b>МАТЕРИАЛ И ПЕЧАТЬ:</b>\n"
            f"• Тип: <b>{data.get('p_type', '?')}</b>\n"
            f"• Плотность: <b>{data.get('paper', '?')}</b>\n"
            f"• Цвет: <b>{data.get('color', '?')}</b>\n\n"
            f"✨ <b>ОТДЕЛКА:</b>\n"
            f"• Покрытие: <b>{data.get('coating', '?')}</b>\n"
            f"• Обработка: <b>{data.get('processing', '?')}</b>\n\n"
            f"🔢 <b>Тираж:</b> <b>{data.get('count', '?')} шт.</b>")

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
        "💡 <i>От формата зависит не только цена, но и то, с какого расстояния будет виден ваш текст.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="А2 (420×594)", callback_data="pos_fmt_A2"),
         InlineKeyboardButton(text="А3 (297×420)", callback_data="pos_fmt_A3")],
        [InlineKeyboardButton(text="А4 (210×297)", callback_data="pos_fmt_A4"),
         InlineKeyboardButton(text="А5 (148×210)", callback_data="pos_fmt_A5")],
        [InlineKeyboardButton(text="📐 210×98 (Евро)", callback_data="pos_fmt_210x98"),
         InlineKeyboardButton(text="📏 Свой размер", callback_data="pos_fmt_custom")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_pos_fmt"),
         InlineKeyboardButton(text="🔙 В меню", callback_data="stop_calc_posters")]
    ])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "help_pos_fmt")
async def help_fmt(callback: types.CallbackQuery):
    await show_help(callback, "<b>Совет технолога по форматам:</b>\n\n"
            "• <b>А2/А3</b> — Золотой стандарт для афиш. Видимость текста до 5-7 метров.\n"
            "• <b>210×98 (Евро)</b> — Идеально для узких витрин и кассовых зон.\n"
            "• <b>Свой размер</b> — Используйте, если у вас уже есть готовые рамки. Учтите: нестандартный крой может увеличить объем отходов бумаги и стоимость.", "pos_back_to_step_1")

@router.callback_query(F.data == "pos_back_to_step_1")
async def back_to_step_1(callback: types.CallbackQuery, state: FSMContext):
    await step_1_format(callback, state)

@router.callback_query(F.data == "stop_calc_posters")
async def stop_calc(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(TEXT_PROMO, reply_markup=kb_cat_promo(), parse_mode="HTML")

@router.callback_query(CalcPosters.step_format, F.data == "pos_fmt_custom")
async def custom_size_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CalcPosters.step_custom_size)
    await callback.message.edit_text("📏 <b>Введите Ширину x Высоту в мм через пробел:</b>\nПример: <code>400 500</code>", 
                                    parse_mode="HTML",
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="calc_posters_start")]]))

@router.message(CalcPosters.step_custom_size)
async def process_custom_size(message: types.Message, state: FSMContext):
    try: 
        await message.delete()
    except: 
        pass
    try:
        parts = message.text.split()
        if len(parts) != 2: raise ValueError
        w, h = map(int, parts)
        await state.update_data(format=f"{w}x{h} мм")
        await render_step_2(message, state)
    except:
        await message.answer("⚠️ Введите два числа через пробел (например: 300 600)")

@router.callback_query(CalcPosters.step_format, F.data.startswith("pos_fmt_"))
async def process_fmt(callback: types.CallbackQuery, state: FSMContext):
    fmt = callback.data.replace("pos_fmt_", "")
    await state.update_data(format=fmt)
    await callback.answer()
    await render_step_2(callback.message, state)

# =======================================================
# 2️⃣ ШАГ 2: ТИП МАТЕРИАЛА
# =======================================================

async def render_step_2(message: types.Message, state: FSMContext):
    await state.set_state(CalcPosters.step_paper_type)
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 2)}"
        "📄 <b>Шаг 2. Тип материала</b>\n"
        "Выберите основу для вашего плаката."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Мелованная", callback_data="pos_pt_Мелованная"),
         InlineKeyboardButton(text="📝 Офсетная", callback_data="pos_pt_Офсетная")],
        [InlineKeyboardButton(text="📦 Картон", callback_data="pos_pt_Картон"),
         InlineKeyboardButton(text="🎞 Самоклейка", callback_data="pos_pt_Самоклейка")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_pos_pt")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="calc_posters_start")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "help_pos_pt")
async def help_pt(callback: types.CallbackQuery):
    await show_help(callback, "<b>Разбор материалов:</b>\n\n"
            "• <b>Мелованная</b> — Для рекламы. Цвета сочные, черный — глубокий. Не подходит для письма ручкой.\n"
            "• <b>Офсетная</b> — Если плакат должен быть функциональным (например, расписание, где нужно делать пометки).\n"
            "• <b>Картон</b> — Для долговечных плакатов, которые стоят в держателях без рамки.\n"
            "• <b>Самоклейка</b> — Для наклейки на жесткие поверхности или витрины.", "pos_back_to_pt")

@router.callback_query(F.data == "pos_back_to_pt")
async def back_to_pt(callback: types.CallbackQuery, state: FSMContext):
    await render_step_2(callback.message, state)

@router.callback_query(CalcPosters.step_paper_type, F.data.startswith("pos_pt_"))
async def step_3_weight(callback: types.CallbackQuery, state: FSMContext):
    pt = callback.data.replace("pos_pt_", "")
    await state.update_data(p_type=pt)
    await callback.answer()
    
    if pt == "Самоклейка":
        await state.update_data(paper="Стандарт")
        return await render_step_4(callback.message, state)
        
    await state.set_state(CalcPosters.step_paper_weight)
    
    weights = []
    if pt == "Мелованная": weights = ["80", "90", "115", "130", "150", "170", "200", "250", "300", "350"]
    elif pt == "Офсетная": weights = ["70", "80", "100", "120"]
    elif pt == "Картон": weights = ["200", "250", "300"]

    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 3)}"
        "⚖️ <b>Шаг 3. Плотность бумаги</b>\n"
        f"Материал: <i>{pt}</i>\n\n"
        "Выберите желаемую толщину листа:"
    )
    buttons = []
    row = []
    for w in weights:
        row.append(InlineKeyboardButton(text=f"{w} г", callback_data=f"pos_pw_{w}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_pos_pw")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="pos_back_to_pt")])
    await smart_edit(callback.message, text, InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "help_pos_pw")
async def help_pw(callback: types.CallbackQuery):
    await show_help(callback, "<b>Как не ошибиться с плотностью:</b>\n\n"
            "• <b>130-150 г/м²</b> — Оптимально. Плакат не идет волной от влажности воздуха.\n"
            "• <b>90-115 г/м²</b> — Эконом-вариант. Может слегка просвечивать.\n"
            "• <b>250+ г/м²</b> — Ощущается как тонкий картон. Хорошо держит форму.", "pos_back_to_pw")

@router.callback_query(F.data == "pos_back_to_pw")
async def back_to_pw(callback: types.CallbackQuery, state: FSMContext):
    await step_3_weight(callback, state)

# =======================================================
# 3️⃣ ШАГ 4: ЦВЕТНОСТЬ
# =======================================================

@router.callback_query(CalcPosters.step_paper_weight, F.data.startswith("pos_pw_"))
async def process_pw(callback: types.CallbackQuery, state: FSMContext):
    w = callback.data.replace("pos_pw_", "")
    await state.update_data(paper=f"{w} г/м²")
    await callback.answer()
    await render_step_4(callback.message, state)

async def render_step_4(message: types.Message, state: FSMContext):
    await state.set_state(CalcPosters.step_color)
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 4)}"
        "🎨 <b>Шаг 4. Красочность печати</b>\n"
        "Выберите формат цветности."
    )
    colors = ["4+4", "4+0", "1+1", "1+0", "2+2", "2+0", "3+3", "3+0", "5+5", "5+0"]
    buttons = []
    row = []
    for c in colors:
        row.append(InlineKeyboardButton(text=c, callback_data=f"pos_col_{c}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_pos_col")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="pos_back_to_pt")]) # Упростим навигацию
    await smart_edit(message, text, InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "help_pos_col")
async def help_col(callback: types.CallbackQuery):
    await show_help(callback, "<b>Полиграфические формулы:</b>\n\n"
            "• <b>4+0</b> — Цветная печать с одной стороны (90% плакатов).\n"
            "• <b>4+4</b> — Цветная с двух сторон.\n"
            "• <b>1+0</b> — Черно-белая с одной стороны.\n"
            "• <b>К+0</b> — Печать спеццветом (Золото, Серебро, Белила).\n"
            "• <b>5+0</b> — CMYK + Пантон или лак.", "pos_back_to_col")

@router.callback_query(F.data == "pos_back_to_col")
async def back_to_col(callback: types.CallbackQuery, state: FSMContext):
    await render_step_4(callback.message, state)

# =======================================================
# 4️⃣ ШАГ 5: ПОКРЫТИЕ И ОБРАБОТКА
# =======================================================

@router.callback_query(CalcPosters.step_color, F.data.startswith("pos_col_"))
async def step_5_coating(callback: types.CallbackQuery, state: FSMContext):
    col = callback.data.replace("pos_col_", "")
    await state.update_data(color=col)
    await callback.answer()
    await render_step_5(callback.message, state)

async def render_step_5(message: types.Message, state: FSMContext):
    await state.set_state(CalcPosters.step_coating)
    data = await state.get_data()
    sel = data.get("coat_list", [])
    
    def t(l, k): return f"✅ {l}" if k in sel else l
    kb = [
        [InlineKeyboardButton(text=t("Без покрытия", "Нет"), callback_data="pos_coat_toggle_Нет")],
        [InlineKeyboardButton(text=t("Лам. Глянец", "Лам_Гл"), callback_data="pos_coat_toggle_Лам_Гл"),
         InlineKeyboardButton(text=t("Лам. Матовая", "Лам_Мат"), callback_data="pos_coat_toggle_Лам_Мат")],
        [InlineKeyboardButton(text=t("УФ-Лак выборочный", "УФ"), callback_data="pos_coat_toggle_УФ"),
         InlineKeyboardButton(text=t("Тиснение фольгой", "Тиснение"), callback_data="pos_coat_toggle_Тиснение")]
    ]
    if sel: kb.append([InlineKeyboardButton(text="➡️ Продолжить", callback_data="pos_coat_done")])
    kb.append([InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_pos_coat")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="pos_back_to_col")])
    
    text = (
        f"{get_breadcrumbs(data, 5)}"
        "✨ <b>Шаг 5. Дополнительное покрытие</b>\n"
        "Выберите один или несколько вариантов защиты и украшения."
    )
    await smart_edit(message, text, InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data == "help_pos_coat")
async def help_coat(callback: types.CallbackQuery):
    await show_help(callback, "<b>Зачем плакату покрытие?</b>\n\n"
            "• <b>Ламинация</b> — Защищает от выцветания и влаги. Обязательна, если плакат будет часто браться руками.\n"
            "• <b>Выборочный УФ-лак</b> — Эффектное выделение логотипа или ключевых элементов блеском.\n"
            "• <b>Тиснение</b> — Для премиальных афиш, грамот и сертификатов.", "pos_back_to_coat")

@router.callback_query(F.data == "pos_back_to_coat")
async def back_to_coat(callback: types.CallbackQuery, state: FSMContext):
    await render_step_5(callback.message, state)

@router.callback_query(CalcPosters.step_coating, F.data.startswith("pos_coat_toggle_"))
async def toggle_coat(callback: types.CallbackQuery, state: FSMContext):
    item = callback.data.replace("pos_coat_toggle_", "")
    data = await state.get_data()
    sel = data.get("coat_list", [])
    
    if item == "Нет": 
        await state.update_data(coat_list=["Нет"], coating="Без покрытия")
        await callback.answer()
        return await render_step_6(callback.message, state)
    
    if "Нет" in sel: 
        sel.remove("Нет")
    
    if item in sel:
        sel.remove(item)
    else:
        # Взаимоисключающая логика для ламинации
        if item == "Лам_Гл" and "Лам_Мат" in sel:
            sel.remove("Лам_Мат")
        elif item == "Лам_Мат" and "Лам_Гл" in sel:
            sel.remove("Лам_Гл")
        
        sel.append(item)
    
    # Сортируем названия для красивого вывода
    names_map = {
        "Лам_Гл": "Лам. Глянец", 
        "Лам_Мат": "Лам. Матовая", 
        "УФ": "УФ-Лак", 
        "Тиснение": "Тиснение"
    }
    display_names = [names_map.get(x, x) for x in sel]
    
    await state.update_data(coat_list=sel, coating=", ".join(display_names) if sel else "Без покрытия")
    await callback.answer()
    await render_step_5(callback.message, state)

@router.callback_query(F.data == "pos_coat_done")
async def coat_done(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_6(callback.message, state)

# =======================================================
# 5️⃣ ШАГ 6: ПОСТПЕЧАТЬ
# =======================================================

async def render_step_6(message: types.Message, state: FSMContext):
    await state.set_state(CalcPosters.step_processing)
    data = await state.get_data()
    sel = data.get("proc_list", [])
    
    def t(l, k): return f"✅ {l}" if k in sel else l
    kb = [
        [InlineKeyboardButton(text=t("Без обработки", "Нет"), callback_data="pos_proc_toggle_Нет")],
        [InlineKeyboardButton(text=t("Биговка (1-4)", "Биговка"), callback_data="pos_proc_toggle_Биговка"),
         InlineKeyboardButton(text=t("Перфорация", "Перфорация"), callback_data="pos_proc_toggle_Перфорация")],
        [InlineKeyboardButton(text=t("Скругление углов", "Скругление"), callback_data="pos_proc_toggle_Скругление"),
         InlineKeyboardButton(text=t("Вырубка (штамп)", "Вырубка"), callback_data="pos_proc_toggle_Вырубка")]
    ]
    if sel: kb.append([InlineKeyboardButton(text="➡️ Продолжить", callback_data="pos_proc_done")])
    kb.append([InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_pos_proc")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="pos_back_to_coat")])
    
    text = (
        f"{get_breadcrumbs(data, 6)}"
        "⚙️ <b>Шаг 6. Послепечатная обработка</b>\n"
        "Дополнительные операции с листом после печати."
    )
    await smart_edit(message, text, InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data == "help_pos_proc")
async def help_proc(callback: types.CallbackQuery):
    await show_help(callback, "<b>Нюансы обработки:</b>\n\n"
            "• <b>Биговка</b> — Линия сгиба. Нужна для плотных бумаг (>170г), чтобы они не ломались.\n"
            "• <b>Перфорация</b> — Линия отрыва (например, для купонов).\n"
            "• <b>Вырубка</b> — Придание плакату сложной формы по штампу.", "pos_back_to_proc")

@router.callback_query(F.data == "pos_back_to_proc")
async def back_to_proc(callback: types.CallbackQuery, state: FSMContext):
    await render_step_6(callback.message, state)

@router.callback_query(CalcPosters.step_processing, F.data.startswith("pos_proc_toggle_"))
async def toggle_proc(callback: types.CallbackQuery, state: FSMContext):
    item = callback.data.replace("pos_proc_toggle_", "")
    data = await state.get_data()
    sel = data.get("proc_list", [])
    if item == "Нет": 
        await state.update_data(proc_list=["Нет"], processing="Без обработки")
        await callback.answer()
        return await render_step_7(callback.message, state)
        
    if "Нет" in sel: sel.remove("Нет")
    if item in sel: sel.remove(item)
    else: sel.append(item)
    
    await state.update_data(proc_list=sel, processing=", ".join(sel) if sel else "???")
    await callback.answer()
    await render_step_6(callback.message, state)

@router.callback_query(F.data == "pos_proc_done")
async def proc_done(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_7(callback.message, state)

# =======================================================
# 6️⃣ ШАГ 7: ТИРАЖ И ФИНАЛ
# =======================================================

async def render_step_7(message: types.Message, state: FSMContext):
    await state.set_state(CalcPosters.step_circulation)
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 7)}"
        "🔢 <b>Шаг 7. Тираж</b>\n"
        "Сколько экземпляров плаката вам нужно?\n\n"
        "<i>Введите число вручную или выберите из списка:</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50", callback_data="pos_cnt_50"), InlineKeyboardButton(text="100", callback_data="pos_cnt_100")],
        [InlineKeyboardButton(text="500", callback_data="pos_cnt_500"), InlineKeyboardButton(text="1000", callback_data="pos_cnt_1000")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="pos_back_to_proc")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(CalcPosters.step_circulation, F.data.startswith("pos_cnt_"))
async def process_cnt_btn(callback: types.CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    cnt = callback.data.replace("pos_cnt_", "")
    await state.update_data(count=cnt)
    await callback.answer()
    await step_final_summary(callback.message, state, db, bot)

@router.message(CalcPosters.step_circulation)
async def process_cnt_text(message: types.Message, state: FSMContext, db: Database, bot: Bot):
    try: await message.delete()
    except: pass
    if not message.text.isdigit(): 
        await message.answer("⚠️ Введите только число!")
        return
    await state.update_data(count=message.text)
    await step_final_summary(message, state, db, bot)

async def step_final_summary(message: types.Message, state: FSMContext, db: Database, bot: Bot):
    data = await state.get_data()
    summary = build_summary_text(data)
    await state.update_data(final_summary=summary)
    
    profile = await db.get_user(message.chat.id)
    is_profile_complete = (
        profile and profile.full_name and profile.phone and profile.city and profile.address
    )
    
    if is_profile_complete:
        text = (
            "🏁 <b>Почти готово! Проверьте ваш заказ</b>\n\n"
            f"{summary}\n\n"
            "➖➖➖➖➖➖➖➖\n"
            "🚀 <b>Что произойдет после отправки?</b>\n"
            "Ваш заказ будет передан менеджеру для точного расчета. Ответ с ценой придет прямо в этот чат в течение 15-30 минут."
        )
        kb = [[InlineKeyboardButton(text="🚀 ОТПРАВИТЬ МЕНЕДЖЕРУ", callback_data="pos_submit")]]
    else:
        text = (
            "🏁 <b>Ваш заказ сформирован!</b>\n\n"
            f"{summary}\n\n"
            "➖➖➖➖➖➖➖➖\n"
            "👋 <b>Давайте познакомимся!</b>\n"
            "Для отправки расчета менеджеру нам нужны ваши контакты. Это нужно сделать всего один раз."
        )
        kb = [[InlineKeyboardButton(text="📝 ПРЕДСТАВИТЬСЯ И ОТПРАВИТЬ", callback_data="pos_reg_start")]]
    
    kb.append([InlineKeyboardButton(text="🔄 Начать сначала", callback_data="calc_posters_start")])
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

# =======================================================
# 📝 РЕГИСТРАЦИЯ
# =======================================================

@router.callback_query(F.data == "pos_reg_start")
async def reg_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CalcPosters.reg_name)
    await callback.message.answer("✍️ Введите ваше <b>Имя</b>:", parse_mode="HTML")

@router.message(CalcPosters.reg_name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(reg_name=message.text)
    try: await message.delete()
    except: pass
    await state.set_state(CalcPosters.reg_phone)
    await message.answer("📞 Введите ваш <b>Телефон</b>:", parse_mode="HTML")

@router.message(CalcPosters.reg_phone)
async def reg_phone(message: types.Message, state: FSMContext):
    await state.update_data(reg_phone=message.text)
    try: await message.delete()
    except: pass
    await state.set_state(CalcPosters.reg_city)
    await message.answer("🏙 Введите ваш <b>Город</b>:", parse_mode="HTML")

@router.message(CalcPosters.reg_city)
async def reg_city(message: types.Message, state: FSMContext):
    await state.update_data(reg_city=message.text)
    try: await message.delete()
    except: pass
    await state.set_state(CalcPosters.reg_address)
    await message.answer("🚚 Введите <b>Адрес доставки</b>:", parse_mode="HTML")

@router.message(CalcPosters.reg_address)
async def reg_address(message: types.Message, state: FSMContext, bot: Bot, db: Database):
    data = await state.get_data()
    await db.update_user_profile(
        message.chat.id, 
        full_name=data['reg_name'], 
        phone=data['reg_phone'], 
        city=data['reg_city'], 
        address=message.text
    )
    try: await message.delete()
    except: pass
    await message.answer("✅ Контакты сохранены! Отправляем заказ...")
    await finalize_order(message.chat, state, bot, message, db)

# =======================================================
# 🚀 ОТПРАВКА
# =======================================================

@router.callback_query(F.data == "pos_submit")
async def submit_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    await callback.answer()
    await finalize_order(callback.message.chat, state, bot, callback.message, db)

async def finalize_order(user_obj, state: FSMContext, bot: Bot, message_obj, db: Database):
    data = await state.get_data()
    summary = data.get('final_summary')
    order = Order(user_id=user_obj.id, category="Плакаты", params=data, description=summary)
    order_id = await db.create_order(order)
    
    await send_order_to_managers(order_id, user_obj.id, summary, "Плакаты", bot, db)
    await state.clear()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="main_profile")],
        [InlineKeyboardButton(text="🏗 В каталог товаров", callback_data="main_constructor")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])
    
    await message_obj.answer(
        f"✨ <b>Спасибо! Заказ #{order_id} успешно отправлен!</b> ✨\n\n"
        "Наш менеджер уже получил уведомление и скоро подготовит расчет стоимости плакатов. 🚀\n\n"
        "Ответ придет прямо сюда. Обычно это занимает не более 30 минут.\n\n"
        "<b>Благодарим за выбор типографии «Поликрафт»!</b>", 
        reply_markup=kb,
        parse_mode="HTML"
    )
