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
    step_quantity = State()
    step_format = State()
    step_orientation = State()

    step_cover_type = State()
    step_binding = State()
    step_cover_paper = State()
    step_cover_color = State()
    step_cover_finish = State()

    step_block_pages = State()
    step_block_color = State()
    step_block_paper_type = State()
    step_block_paper_weight = State()

    step_services = State()

    reg_name = State()
    reg_phone = State()
    reg_city = State()
    reg_address = State()

TOTAL_STEPS = 13

def get_progress_bar(current: int, total: int) -> str:
    filled = int((current / total) * 10)
    bar = "▰" * filled + "▱" * (10 - filled)
    percent = int((current / total) * 100)
    return f"📊 <b>Шаг {current} из {total}</b> [{bar}] {percent}%\n\n"

def get_breadcrumbs(data: dict, current_step: int) -> str:
    progress = get_progress_bar(current_step, TOTAL_STEPS)

    sections = []

    gen = []
    if current_step > 1 and data.get('quantity'): gen.append(f"• Тираж: <b>{data['quantity']} шт.</b>")
    if current_step > 2 and data.get('format_name'): gen.append(f"• Формат: <b>{data['format_name']}</b>")
    if current_step > 3 and data.get('orientation'): gen.append(f"• Ориентация: <b>{data['orientation']}</b>")
    if gen: sections.append("🔧 <b>ОБЩИЕ:</b>\n" + "\n".join(gen))

    cov = []
    if current_step > 4 and data.get('cover_type'): cov.append(f"• Переплет: <b>{data['cover_type']}</b>")
    if current_step > 5 and data.get('binding'): cov.append(f"• Скрепление: <b>{data['binding']}</b>")
    if current_step > 6 and data.get('cover_paper'): cov.append(f"• Бумага: <b>{data['cover_paper']}</b>")
    if current_step > 7 and data.get('cover_color'): cov.append(f"• Цветность: <b>{data['cover_color']}</b>")

    finishes = data.get('cover_finishes_list', [])
    if current_step > 8:
        if finishes: cov.append(f"• Отделка: <b>{', '.join(finishes)}</b>")
        elif data.get('cover_finish_done'): cov.append(f"• Отделка: <b>Нет</b>")

    if cov: sections.append("📕 <b>ОБЛОЖКА:</b>\n" + "\n".join(cov))

    blk = []
    if current_step > 9 and data.get('block_pages'): blk.append(f"• Страниц: <b>{data['block_pages']}</b>")
    if current_step > 10 and data.get('block_color'): blk.append(f"• Печать: <b>{data['block_color']}</b>")
    if current_step > 11 and data.get('block_paper_type'): blk.append(f"• Бумага: <b>{data['block_paper_type']}</b>")
    if current_step > 12 and data.get('block_paper_weight'): blk.append(f"• Плотность: <b>{data['block_paper_weight']}</b>")

    if blk: sections.append("📄 <b>БЛОК:</b>\n" + "\n".join(blk))

    srv = data.get('services_list', [])
    if current_step > 13:
        if srv: sections.append("🛠 УСЛУГИ:\n" + "\n".join(f"• <b>{s}</b>" for s in srv))
        elif data.get('services_done'): sections.append("🛠 УСЛУГИ:\n• <b>Нет</b>")

    if not sections:
        return progress
    return progress + "📝 <b>Ваш заказ:</b>\n\n" + "\n\n".join(sections) + "\n➖➖➖➖➖➖➖➖\n"

async def smart_edit(message: types.Message, text: str, kb: InlineKeyboardMarkup):
    try:
        await message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await message.answer(text=text, reply_markup=kb, parse_mode="HTML")

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

    text = (
        f"{get_breadcrumbs({}, 1)}"
        "🔢 <b>Шаг 1. Выберите тираж</b>\n"
        "Укажите, сколько экземпляров журнала или каталога вам нужно.\n\n"
        "💡 <i>Правило типографии: чем больше тираж, тем дешевле обходится один экземпляр.</i>\n\n"
        "Выберите количество из списка или напишите свое число в чат (от 10 шт):"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50", callback_data="qty_50"),
         InlineKeyboardButton(text="100", callback_data="qty_100"),
         InlineKeyboardButton(text="200", callback_data="qty_200")],
        [InlineKeyboardButton(text="300", callback_data="qty_300"),
         InlineKeyboardButton(text="500", callback_data="qty_500"),
         InlineKeyboardButton(text="1000", callback_data="qty_1000")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_qty"),
         InlineKeyboardButton(text="🔙 В меню", callback_data="stop_calc_journal")]
    ])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "help_journal_qty")
async def help_1(callback: types.CallbackQuery):
    await show_help(callback, "<b>Как тираж влияет на цену и сроки?</b>\n\n"
        "🖨 <b>До 300 шт. (Цифровая печать)</b>\n"
        "• Идеально для пилотных выпусков, корпоративных отчетов и узких презентаций.\n"
        "• Печатается быстро (от 1 дня).\n\n"
        "🏭 <b>От 500 шт. (Офсетная печать)</b>\n"
        "• Выбор для массовых каталогов и глянцевых журналов.\n"
        "• Требует времени на приладку, но цена за 1 штуку падает в разы.\n\n"
        "👉 <i>Если сомневаетесь, выбирайте примерное число — менеджер при расчете может предложить более выгодную партию.</i>", "journal_back_step_0")

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
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 2)}"
        "📏 <b>Шаг 2. Формат издания</b>\n"
        "Размер определяет, насколько удобно будет держать журнал в руках и сколько информации поместится на странице.\n\n"
        "1️⃣ <b>А4</b> — Классический крупный глянец и рабочие каталоги.\n"
        "2️⃣ <b>А5</b> — Компактный формат (половина А4), удобно брать с собой.\n"
        "3️⃣ <b>А6</b> — Карманный формат (блокнот/памятка).\n"
        "4️⃣ <b>165х240 мм</b> — Нестандартный «королевский» размер, выглядит дорого."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="А4 (210x297)", callback_data="fmt_A4"),
         InlineKeyboardButton(text="А5 (148x210)", callback_data="fmt_A5")],
        [InlineKeyboardButton(text="А6 (105x148)", callback_data="fmt_A6"),
         InlineKeyboardButton(text="165х240", callback_data="fmt_Crown")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_fmt"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_1")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "help_journal_fmt")
async def help_2(callback: types.CallbackQuery):
    await show_help(callback, "<b>Как выбрать правильный размер?</b>\n\n"
        "📘 <b>А4 (210x297 мм)</b>\n"
        "Много места для крупных фото, схем и прайсов. Стандарт для B2B-каталогов и глянца.\n\n"
        "📗 <b>А5 (148x210 мм)</b>\n"
        "Универсально и экономно. Отлично подходит для корпоративных журналов, инструкций и меню.\n\n"
        "📙 <b>А6 (105x148 мм)</b>\n"
        "Мини-формат. Используется для брошюр-памяток, гарантийных талонов или промо-каталогов.\n\n"
        "👑 <b>Crown (165х240 мм)</b>\n"
        "Шире, чем А5, но изящнее, чем А4. Выбор для fashion-каталогов, портфолио и арт-изданий. Сразу выделяется в стопке других бумаг.", "journal_back_step_help_2")

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
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 3)}"
        "🔄 <b>Шаг 3. Ориентация страниц</b>\n"
        "Как будут переворачиваться страницы?\n\n"
        "↕️ <b>Вертикальная (Книжная)</b> — Классика. Переплет по длинной стороне.\n"
        "↔️ <b>Горизонтальная (Альбомная)</b> — Широкие страницы. Переплет по короткой стороне."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↕️ Вертикальная", callback_data="orient_vert"),
         InlineKeyboardButton(text="↔️ Горизонтальная", callback_data="orient_horiz")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_orient"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_2")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "help_journal_orient")
async def help_3(callback: types.CallbackQuery):
    await show_help(callback, "<b>Какая ориентация лучше?</b>\n\n"
        "↕️ <b>Вертикальная (Книжная)</b>\n"
        "Привычный формат для 95% журналов и книг. Читателю удобно держать его одной рукой. Выбирайте этот вариант по умолчанию.\n\n"
        "↔️ <b>Горизонтальная (Альбомная)</b>\n"
        "Широкий формат. Раскрывается в длинную полосу. Идеально для фотокниг, портфолио архитекторов, каталогов недвижимости или презентаций с широкими графиками.", "journal_back_step_help_3")

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
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 4)}"
        "📕 <b>Шаг 4. Тип переплета (обложка)</b>\n"
        "Определите, насколько плотной и жесткой должна быть внешняя часть издания.\n\n"
        "1️⃣ <b>Мягкий переплет</b> — Плотная гибкая бумага (как у Cosmopolitan или каталога IKEA).\n"
        "2️⃣ <b>Твердый переплет</b> — Жесткий негнущийся картон (как у классических книг)."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Мягкий", callback_data="cover_type_soft"),
         InlineKeyboardButton(text="Твердый", callback_data="cover_type_hard")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_covtype"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_3")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "help_journal_covtype")
async def help_4(callback: types.CallbackQuery):
    await show_help(callback, "<b>В чем разница?</b>\n\n"
        "📄 <b>Мягкий переплет</b>\n"
        "Быстрее в производстве и дешевле. Журнал получается легким, его удобно свернуть в трубочку. Подходит для ежемесячных изданий, промо-каталогов и брошюр.\n\n"
        "📚 <b>Твердый переплет (7БЦ)</b>\n"
        "Жесткая основа из переплетного картона. Журнал превращается в полноценную книгу. Защищает страницы от заломов, выглядит максимально статусно. Подходит для юбилейных корпоративных изданий, премиум-портфолио и подарочных книг. Значительно удорожает тираж.", "journal_back_step_help_4")

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
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 5)}"
        "🔗 <b>Шаг 5. Способ скрепления страниц</b>\n"
        "Как листы будут держаться вместе? От этого зависит долговечность и внешний вид корешка.\n\n"
        "📎 <b>Скоба</b> — Две металлические скрепки по центру (бюджетно).\n"
        "📚 <b>Клей (КБС)</b> — Проклеенный ровный корешок (как у глянца).\n"
        "➰ <b>Пружина</b> — Металлическая спираль (удобно листать)."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Скоба", callback_data="bind_staple"),
         InlineKeyboardButton(text="Пружина", callback_data="bind_wire"),
         InlineKeyboardButton(text="Клей (КБС)", callback_data="bind_glue")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_bind"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_4")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "help_journal_bind")
async def help_5(callback: types.CallbackQuery):
    await show_help(callback, "<b>Какое скрепление подойдет вашему тиражу?</b>\n\n"
        "📎 <b>Скоба (Скрепка)</b>\n"
        "• Только для тонких журналов (обычно до 48-60 страниц).\n"
        "• Раскрывается на 180 градусов, надежно и дешево.\n\n"
        "📚 <b>Клеевое бесшвейное скрепление (КБС)</b>\n"
        "• Для изданий от 48 страниц.\n"
        "• Образует красивый квадратный корешок, на котором можно напечатать название.\n"
        "• Стандарт для толстых каталогов и глянцевых журналов.\n\n"
        "➰ <b>Пружина</b>\n"
        "• Журнал можно полностью вывернуть наизнанку (на 360 градусов).\n"
        "• Идеально для меню, рабочих тетрадей, инструкций и презентаций, которые должны лежать открытыми на столе.", "journal_back_step_help_5")

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
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 6)}"
        "📄 <b>Шаг 6. Плотность обложки</b>\n"
        "Чем плотнее бумага, тем дольше журнал сохранит товарный вид.\n\n"
        "<i>(Обычная офисная бумага имеет плотность 80 г/м², стандартная визитка — 300 г/м²)</i>\n\n"
        "Выберите подходящий вариант для вашей обложки:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
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

@router.callback_query(F.data == "help_journal_covpap")
async def help_6(callback: types.CallbackQuery):
    await show_help(callback, "<b>Как выбрать плотность обложки?</b>\n\n"
        "🔹 <b>150 - 170 г/м²</b>\nТонкая гибкая обложка. Часто используется для массовых недорогих каталогов или если обложка не должна сильно отличаться по толщине от внутренних страниц.\n\n"
        "🔹 <b>200 - 250 г/м² (Рекомендуем)</b>\nЗолотой стандарт. Обложка хорошо держит форму, не рвется и скрывает внутренний блок. Классический глянец.\n\n"
        "🔹 <b>300 - 350 г/м²</b>\nМаксимальная плотность для мягкого переплета. Почти картон. Журнал будет ощущаться в руках массивно и дорого.", "journal_back_step_help_6")

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
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 7)}"
        "🎨 <b>Шаг 7. Красочность обложки</b>\n"
        "Нужна ли цветная печать на внутренней стороне обложки?\n\n"
        "1️⃣ <b>4+0</b> — Цветная только снаружи. Внутри обложка остается белой.\n"
        "2️⃣ <b>4+4</b> — Цветная с двух сторон (снаружи и внутри).\n"
        "3️⃣ <b>1+1</b> — Черно-белая с двух сторон (для строгих отчетов).\n"
        "4️⃣ <b>4+1</b> — Снаружи цветная, внутри черно-белая."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="4+0 (Лицо)", callback_data="cov_col_4+0"),
         InlineKeyboardButton(text="4+4 (Все)", callback_data="cov_col_4+4")],
        [InlineKeyboardButton(text="1+1 (ЧБ)", callback_data="cov_col_1+1"),
         InlineKeyboardButton(text="4+1 (Цв+ЧБ)", callback_data="cov_col_4+1")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_covcol"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_6")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "help_journal_covcol")
async def help_7(callback: types.CallbackQuery):
    await show_help(callback, "<b>Расшифровка полиграфических формул:</b>\n\n"
        "Цифры означают количество используемых красок. «4» — это полноцветная печать (CMYK), «1» — только черная краска, «0» — без печати (чистый лист).\n\n"
        "Первая цифра — это лицевая сторона обложки, вторая — её обратная (внутренняя) сторона.\n\n"
        "👉 <b>Что выбрать?</b>\n"
        "Если вы не планируете размещать рекламу или информацию на внутренней стороне обложки (сразу открываешь и идет первая страница) — смело выбирайте <b>4+0</b>, это сэкономит бюджет.\n"
        "Если на развороте обложки есть дизайн — берите <b>4+4</b>.", "journal_back_step_help_7")

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
    text = (
        f"{get_breadcrumbs(d, 8)}"
        "✨ <b>Шаг 8. Премиальная отделка обложки</b>\n"
        "Хотите, чтобы журнал выглядел дорого и выделялся на полке?\n"
        "<i>(Можно выбрать несколько опций или пропустить)</i>\n\n"
        "🛡 <b>Ламинация</b> — Покрытие матовой или глянцевой пленкой.\n"
        "🔥 <b>Тиснение</b> — Рельефное выдавливание логотипа или фольга.\n"
        "💧 <b>УФ-лак</b> — Блестящее выделение отдельных элементов дизайна."
    )
    await smart_edit(message, text, kb_finish(d.get("cover_finishes_list", [])))

@router.callback_query(F.data == "help_journal_finish")
async def help_8(callback: types.CallbackQuery):
    await show_help(callback, "<b>Зачем нужна дополнительная отделка?</b>\n\n"
        "🛡 <b>Ламинация (обязательно для КБС и плотных обложек)</b>\n"
        "Защищает краску от царапин, влаги и заломов на сгибе. Глянцевая делает цвета ярче, матовая убирает блики и добавляет тактильного благородства.\n\n"
        "🔥 <b>Тиснение (Фольга или Блинт)</b>\n"
        "Позволяет сделать логотип золотым, серебряным или просто вдавленным в бумагу. Создает wow-эффект.\n\n"
        "💧 <b>Выборочный УФ-лак</b>\n"
        "Крутой прием: обложка покрывается матовой ламинацией, а фото продукта или логотип заливаются толстым слоем глянцевого лака. Элемент становится объемным и блестит на свету.", "journal_back_step_help_8")

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
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 9)}"
        "📄 <b>Шаг 9. Количество страниц внутри (Блок)</b>\n"
        "Сколько всего страниц будет в вашем журнале? Обложка в это число не входит.\n\n"
        "❗️ <b>Техническое ограничение:</b> число страниц должно делиться на 4 (например: 8, 12, 16, 20...).\n\n"
        "<i>Выберите из списка или введите точное число вручную в чат:</i>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="8", callback_data="pages_8"),
         InlineKeyboardButton(text="12", callback_data="pages_12"),
         InlineKeyboardButton(text="24", callback_data="pages_24"),
         InlineKeyboardButton(text="48", callback_data="pages_48")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_pages"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_8")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "help_journal_pages")
async def help_9(callback: types.CallbackQuery):
    await show_help(callback, "<b>Почему страницы должны быть кратны 4?</b>\n\n"
        "В полиграфии журналы не печатаются отдельными листиками. Они печатаются на больших разворотах, которые затем складываются пополам.\n\n"
        "Представьте один согнутый пополам лист: у него появляется 4 стороны (страницы).\n"
        "Именно поэтому невозможно сделать журнал на 5, 7 или 10 страниц — всегда останутся пустые белые полосы. Если у вас 10 страниц текста, вам придется добавить 2 пустые страницы для заметок или рекламы, чтобы получилось 12.", "journal_back_step_help_9")

@router.callback_query(F.data == "journal_back_step_help_9")
async def back_help_9(callback: types.CallbackQuery, state: FSMContext):
    await step_9_block_pages(callback.message, state)

@router.callback_query(F.data == "journal_back_step_8")
async def back_to_step_8(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await step_8_cover_finish(callback.message, state)

@router.callback_query(JournalCalc.step_block_pages, F.data.startswith("pages_"))
async def process_pages_btn(callback: types.CallbackQuery, state: FSMContext):
    pages = int(callback.data.split("_")[1])
    await state.update_data(block_pages=pages)
    await callback.answer()
    await step_10_block_color(callback.message, state)

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
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 10)}"
        "🎨 <b>Шаг 10. Цветность внутренних страниц</b>\n"
        "Что будет напечатано внутри?\n\n"
        "1️⃣ <b>1+1 (Черно-белое)</b> — Только текст и черно-белые схемы.\n"
        "2️⃣ <b>4+4 (Полноцвет)</b> — Цветные фотографии на каждой странице.\n"
        "3️⃣ <b>2+2 (Два цвета)</b> — Черный текст + один фирменный цвет для акцентов."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1+1 (ЧБ)", callback_data="blk_col_1+1"),
         InlineKeyboardButton(text="2+2 (Два цв.)", callback_data="blk_col_2+2")],
        [InlineKeyboardButton(text="4+4 (Полноцвет)", callback_data="blk_col_4+4")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_blkcol"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_9")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "help_journal_blkcol")
async def help_10(callback: types.CallbackQuery):
    await show_help(callback, "<b>Какую цветность выбрать?</b>\n\n"
        "⚫️ <b>1+1 (ЧБ)</b>\n"
        "Самый дешевый вариант. Отлично подходит для текстовых отчетов, рабочих тетрадей, инструкций по эксплуатации и справочников.\n\n"
        "🎨 <b>4+4 (Полноцвет)</b>\n"
        "Необходим для каталогов продукции, глянцевых журналов, комиксов и портфолио. Фотографии будут яркими и сочными.\n\n"
        "🔴 <b>2+2 (Два цвета)</b>\n"
        "Компромиссный вариант. Например, основной текст черный, а заголовки, таблицы и рамки — в вашем фирменном красном или синем цвете. Выглядит стильно и обходится дешевле полноцвета (при офсетной печати).", "journal_back_step_help_10")

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
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 11)}"
        "📄 <b>Шаг 11. Бумага для внутренних страниц</b>\n"
        "От материала зависит, как будут выглядеть картинки и удобно ли будет читать текст.\n\n"
        "1️⃣ <b>Офсетная</b> — Матовая, шершавая (как для принтера). Удобно писать ручкой.\n"
        "2️⃣ <b>Мелованная Глянец</b> — Блестящая, гладкая. Делает фото максимально яркими.\n"
        "3️⃣ <b>Мелованная Матовая</b> — Гладкая, но без бликов. Глаза не устают при чтении."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Офсетная", callback_data="blk_type_Offset")],
        [InlineKeyboardButton(text="Мелованная Глянец", callback_data="blk_type_Glossy"),
         InlineKeyboardButton(text="Мелованная Мат", callback_data="blk_type_Matte")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_blktype"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_10")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "help_journal_blktype")
async def help_11(callback: types.CallbackQuery):
    await show_help(callback, "<b>Какая бумага нужна вашему проекту?</b>\n\n"
        "📝 <b>Офсетная (Без покрытия)</b>\n"
        "Хорошо впитывает краску, из-за чего цвета становятся слегка приглушенными. Зато на ней идеально писать ручкой или карандашом. <i>Выбор для рабочих тетрадей, анкет, прайс-листов и инструкций.</i>\n\n"
        "✨ <b>Мелованная Глянцевая</b>\n"
        "Краска остается на поверхности. Фотографии автомобилей, еды или ювелирных изделий будут выглядеть максимально «вкусно». <i>Выбор для рекламных каталогов.</i>\n\n"
        "☁️ <b>Мелованная Матовая</b>\n"
        "Выглядит солидно и дорого. На свету нет раздражающих бликов, поэтому текст читать намного приятнее. <i>Выбор для fashion-журналов, корпоративных отчетов и архитектурных презентаций.</i>", "journal_back_step_help_11")

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
        f"{get_breadcrumbs(data, 12)}"
        "⚖️ <b>Шаг 12. Плотность бумаги страниц</b>\n"
        f"Выбрана: <i>{ptype}</i>\n"
        "Слишком тонкая бумага будет просвечивать оборотную сторону, а слишком толстая сделает журнал тяжелым и негибким.\n\n"
        "Выберите оптимальную толщину листа:"
    )

    buttons = []

    if "Офсетная" in ptype:
        buttons.append([
            InlineKeyboardButton(text="65 г/м²", callback_data="blk_w_65"),
            InlineKeyboardButton(text="80 г/м²", callback_data="blk_w_80")
        ])
        buttons.append([
            InlineKeyboardButton(text="100 г/м²", callback_data="blk_w_100"),
            InlineKeyboardButton(text="120 г/м²", callback_data="blk_w_120")
        ])
    else:
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

    buttons.append([
        InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_journal_blkweight"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="journal_back_step_11")
    ])

    await smart_edit(message, text, InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "help_journal_blkweight")
async def help_12(callback: types.CallbackQuery):
    await show_help(callback, "<b>Гид по плотности страниц:</b>\n\n"
        "🔹 <b>80 - 90 г/м²</b>\nТонкая бумага. Идеальна для многостраничных черно-белых отчетов и инструкций. Если напечатать плотные цветные картинки, они будут просвечивать насквозь.\n\n"
        "🔹 <b>115 - 130 г/м²</b>\nКлассический стандарт для цветных журналов и каталогов. Оптимальный баланс: не просвечивает, легкая, отлично листается.\n\n"
        "🔹 <b>150 - 170 г/м²</b>\nПлотная журнальная страница. Дает ощущение премиальности. Часто используется для фотоальбомов и меню.\n\n"
        "🔹 <b>200+ г/м²</b>\nОчень толстые листы. Выбирают для небольших детских книг или эксклюзивных каталогов с малым количеством страниц.", "journal_back_step_help_12")

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
        f"{get_breadcrumbs(data, 13)}"
        "🛠 <b>Шаг 13. Дополнительные услуги</b>\n"
        "Если у вас нет готового к печати файла по всем техническим требованиям, наши специалисты помогут довести проект до ума.\n"
        "<i>(Выберите нужное или сразу жмите «Рассчитать заказ»)</i>\n\n"
        "💻 <b>Верстка</b> — Соберем красивый макет из вашего текста и фото.\n"
        "📖 <b>ISBN</b> — Официальная регистрация издания (штрихкод).\n"
        "📝 <b>Корректура</b> — Проверка текста на ошибки и опечатки."
    )

    await smart_edit(message, text, kb_services(selected))

@router.callback_query(F.data == "help_journal_srv")
async def help_13(callback: types.CallbackQuery):
    await show_help(callback, "<b>Что включает в себя помощь типографии?</b>\n\n"
        "💻 <b>Дизайн и Верстка</b>\n"
        "Если у вас есть только текст в Word и папка с фотографиями, наш верстальщик грамотно разместит это на страницах, подберет шрифты и подготовит файл к печати с учетом всех отступов и полей.\n\n"
        "📖 <b>Присвоение ISBN</b>\n"
        "Международный стандартный книжный номер. Нужен, если вы планируете официально продавать ваш журнал или книгу через магазины и маркетплейсы.\n\n"
        "📝 <b>Корректура и Редактура</b>\n"
        "Профессиональный филолог вычитает ваш текст, исправит запятые, опечатки и стилистические ошибки, чтобы издание было безупречным.", "journal_back_step_help_13")

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

def build_summary_text(data: dict) -> str:
    finishes = data.get('cover_finishes_list', [])
    finish_str = ', '.join(finishes) if finishes else "Нет"
    services = data.get('services_list', [])
    if services:
        services_lines = "\n".join(f"• <b>{s}</b>" for s in services)
    else:
        services_lines = "• <b>Нет</b>"

    return (
        f"🧾 <b>ПРОВЕРКА ДАННЫХ: ЖУРНАЛЫ</b>\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"🔧 <b>ОБЩИЕ:</b>\n"
        f"• Тираж: <b>{data.get('quantity', '?')} шт.</b>\n"
        f"• Формат: <b>{data.get('format_name', '?')}</b>\n"
        f"• Ориентация: <b>{data.get('orientation', '?')}</b>\n\n"
        f"📕 <b>ОБЛОЖКА:</b>\n"
        f"• Переплет: <b>{data.get('cover_type', '?')}</b>\n"
        f"• Скрепление: <b>{data.get('binding', '?')}</b>\n"
        f"• Бумага: <b>{data.get('cover_paper', '?')}</b>\n"
        f"• Цветность: <b>{data.get('cover_color', '?')}</b>\n"
        f"• Отделка: <b>{finish_str}</b>\n\n"
        f"📄 <b>БЛОК:</b>\n"
        f"• Страниц: <b>{data.get('block_pages', '?')}</b>\n"
        f"• Печать: <b>{data.get('block_color', '?')}</b>\n"
        f"• Бумага: <b>{data.get('block_paper_type', '?')}</b>\n"
        f"• Плотность: <b>{data.get('block_paper_weight', '?')}</b>\n\n"
        f"🛠 УСЛУГИ:\n{services_lines}"
    )

@router.callback_query(F.data == "srv_done")
async def step_finish_summary(callback: types.CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    await state.update_data(services_done=True)
    data = await state.get_data()

    summary_text = build_summary_text(data)
    await state.update_data(final_summary=summary_text)

    user_id = callback.message.chat.id
    profile = await db.get_user(user_id)

    is_profile_complete = (
        profile and
        profile.full_name and
        profile.phone and
        profile.city and
        profile.address
    )

    if is_profile_complete:
        text = (
            "🏁 <b>Почти готово! Проверьте ваш заказ</b>\n\n"
            f"{summary_text}\n\n"
            "➖➖➖➖➖➖➖➖\n"
            "🚀 <b>Что произойдет после отправки?</b>\n\n"
            "Ваш заказ будет немедленно передан нашему менеджеру. "
            "Он внимательно изучит все параметры, подготовит точный расчёт стоимости "
            "и отправит вам ответ <b>прямо в этот чат</b>. 💬\n\n"
            "Обычно это занимает <b>от 15 до 30 минут</b> в рабочее время. "
            "После получения цены вы сможете подтвердить заказ или обсудить детали с менеджером.\n\n"
            "<i>Нажмите кнопку ниже, чтобы отправить заявку:</i> 👇"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 ОТПРАВИТЬ МЕНЕДЖЕРУ", callback_data="journal_submit_order")],
            [InlineKeyboardButton(text="🔄 Изменить параметры", callback_data="start_calc_journal")]
        ])
    else:
        text = (
            "🏁 <b>Отлично! Ваш заказ сформирован!</b>\n\n"
            f"{summary_text}\n\n"
            "➖➖➖➖➖➖➖➖\n"
            "👋 <b>Давайте познакомимся!</b>\n\n"
            "Для того чтобы менеджер мог оперативно связаться с вами и отправить расчёт стоимости, "
            "нам потребуются ваши контактные данные.\n\n"
            "📌 <i>Не переживайте — это нужно сделать всего один раз! "
            "Ваши данные надёжно сохранятся в личном кабинете и будут автоматически подставляться при следующих заказах.</i>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 ПРЕДСТАВИТЬСЯ И ОТПРАВИТЬ", callback_data="journal_reg_start")],
            [InlineKeyboardButton(text="🔄 Начать сначала", callback_data="start_calc_journal")]
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
# 🚀 ОТПРАВКА ЗАКАЗА (Финализация)
# =======================================================

@router.callback_query(F.data == "journal_submit_order")
async def submit_order_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    await callback.answer()
    await finalize_order(callback.message.chat, state, bot, callback.message, db)

async def finalize_order(user_obj, state: FSMContext, bot: Bot, message_obj, db: Database):
    from handlers.common import send_order_to_managers

    data = await state.get_data()
    summary = data.get('final_summary', 'Нет данных')

    order = Order(
        user_id=user_obj.id,
        category="Журналы",
        params=data,
        description=summary
    )
    order_id = await db.create_order(order)

    await send_order_to_managers(order_id, user_obj.id, summary, "Журналы", bot, db)

    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="main_profile")],
        [InlineKeyboardButton(text="🏗 В каталог товаров", callback_data="main_constructor")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])

    await message_obj.answer(
        f"✨ <b>Спасибо! Заказ #{order_id} успешно отправлен!</b> ✨\n\n"
        "Информация о вашем заказе журналов уже передана нашему менеджеру. 🚀\n\n"
        "Он внимательно изучит все параметры и подготовит точный расчёт стоимости. "
        "Ответ с ценой придёт <b>прямо в этот чат</b> — вам останется только подтвердить или обсудить детали. 💬\n\n"
        "⏱ <i>Обычно это занимает от 15 до 30 минут в рабочее время.</i>\n\n"
        "<b>Благодарим за доверие к типографии «Поликрафт»!</b> 🙌\n\n"
        "👇 <i>Чем займёмся, пока ждём ответ?</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )
