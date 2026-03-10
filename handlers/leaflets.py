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

# === МАШИНА СОСТОЯНИЙ ===
class CalcLeaflets(StatesGroup):
    step_format = State()
    step_color = State()
    step_processing = State()
    step_paper_type = State()
    step_paper_weight = State()
    step_circulation = State()
    
    # Регистрация (согласно логике из calc_leaflets.py)
    reg_name = State()
    reg_phone = State()
    reg_email = State()
    reg_city = State()
    reg_address = State()

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def get_breadcrumbs(data: dict, current_step: int) -> str:
    lines = []
    if current_step > 1: lines.append(f"📏 Формат: <b>{data.get('format', '???')}</b>")
    if current_step > 2: lines.append(f"🎨 Печать: <b>{data.get('color', '???')}</b>")
    if current_step > 3: lines.append(f"🛠 Обработка: <b>{data.get('processing', '???')}</b>")
    if current_step > 4: lines.append(f"📄 Тип бумаги: <b>{data.get('p_type', '???')}</b>")
    if current_step > 5: lines.append(f"⚖️ Плотность: <b>{data.get('paper', '???')}</b>")
    if current_step > 6: lines.append(f"🔢 Тираж: <b>{data.get('count', '???')} шт.</b>")
    
    if not lines: return ""
    return "⚙️ <b>Ваш выбор:</b>\n" + "\n".join(lines) + "\n➖➖➖➖➖➖➖➖\n"

async def smart_edit(message: types.Message, text: str, kb: InlineKeyboardMarkup):
    try:
        await message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        try: await message.delete()
        except: pass
        await message.answer(text=text, reply_markup=kb, parse_mode="HTML")

# ==========================================
# 1. ФОРМАТ
# ==========================================
@router.callback_query(F.data == "prod_Листовки")
async def step_1_format(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(CalcLeaflets.step_format)
    
    text = (
        "📍 <b>Шаг 1. Выбор формата</b>\n\n"
        "Отлично, печатаем Листовки! Это универсальный инструмент: от агитации до подробных прайс-листов.\n\n"
        "Сейчас выберите размер. От него зависит, сколько информации поместится и насколько удобно её будет читать.\n\n"
        "<b>Выберите подходящий формат:</b>\n"
        "• A6 (105 × 148 мм)\n"
        "• A5 (148 × 210 мм)\n"
        "• A4 (210 × 297 мм)\n"
        "• A3 (297 × 420 мм)\n"
        "• Флаер (Евро) (100 × 210 мм)\n\n"
        "💡 <i>Не уверены? Нажмите кнопку «Справка», я разложил всё по полочкам.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="А6 (105х148)", callback_data="l_fmt_A6"),
         InlineKeyboardButton(text="А5 (148х210)", callback_data="l_fmt_A5")],
        [InlineKeyboardButton(text="А4 (210х297)", callback_data="l_fmt_A4"),
         InlineKeyboardButton(text="А3 (297х420)", callback_data="l_fmt_A3")],
        [InlineKeyboardButton(text="🚀 Флаер (Евро)", callback_data="l_fmt_Flyer")],
        [InlineKeyboardButton(text="📖 Справка", callback_data="info_l_format")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cat_promo")]
    ])
    await smart_edit(callback.message, text, kb)

@router.callback_query(StateFilter(CalcLeaflets.step_format), F.data == "info_l_format")
async def info_l_format_handler(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "ℹ️ <b>Размер имеет значение</b>\n\n"
        "Вот краткий гид, какой формат под какую задачу «заточен»:\n\n"
        "🔹 <b>A6 (Карманный)</b>\n"
        "Самый бюджетный вариант. Идеален для кратких офферов, купонов или небольших объявлений. Легко помещается в кошелек или карман.\n\n"
        "🔹 <b>A5 (Золотая середина)</b>\n"
        "Популярный формат для раздачи в руки. Места достаточно и для яркой картинки, и для списка услуг с ценами.\n\n"
        "🔹 <b>A4 (Стандарт)</b>\n"
        "Классика для серьезных предложений. Именно этот формат чаще всего размещают в рекламных карманах инфо-стендов и в транспорте.\n\n"
        "🔹 <b>A3 (Макси)</b>\n"
        "Внимание! Это уже почти плакат. Используйте его, если информации действительно много или если листовка будет висеть на стене как объявление.\n\n"
        "🔹 <b>Флаер (Евроформат)</b>\n"
        "Узкий и стильный. Идеален для приглашений, меню или стильных промо-акций. Выглядит дороже обычной листовки за счет своей формы."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="prod_Листовки")]])
    await smart_edit(callback.message, text, kb)

# ==========================================
# 2. КРАСОЧНОСТЬ
# ==========================================
@router.callback_query(CalcLeaflets.step_format, F.data.startswith("l_fmt_"))
async def step_2_color_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    fmt_map = {"l_fmt_A6": "А6", "l_fmt_A5": "А5", "l_fmt_A4": "А4", "l_fmt_A3": "А3", "l_fmt_Flyer": "Флаер"}
    await state.update_data(format=fmt_map.get(callback.data))
    await render_step_2(callback.message, state)

async def render_step_2(message: types.Message, state: FSMContext):
    await state.set_state(CalcLeaflets.step_color)
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 2)}"
        "📍 <b>Шаг 2. Цветность печати</b>\n\n"
        "Теперь решим, с каких сторон будем печатать. Помните: полноцветная печать в сочетании с корректной версткой в разы увеличивает отдачу от рекламы.\n\n"
        "<b>Выберите вариант:</b>\n"
        "• <b>4+0 (Односторонняя)</b> — Яркая печать только с лицевой стороны. Оборот остается белым.\n"
        "• <b>4+4 (Двусторонняя)</b> — Полноцветная печать с обеих сторон.\n\n"
        "💡 <i>Что выбрать? Если сомневаетесь, загляните в раздел «Справка» — там я объяснил, на чем можно сэкономить, а где этого делать не стоит.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Односторонняя (4+0)", callback_data="l_col_4+0")],
        [InlineKeyboardButton(text="2️⃣ Двусторонняя (4+4)", callback_data="l_col_4+4")],
        [
            InlineKeyboardButton(text="📖 Справка", callback_data="info_l_color"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="prod_Листовки")
        ]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(StateFilter(CalcLeaflets.step_color), F.data == "info_l_color")
async def info_l_color_handler(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "ℹ️ <b>Справка: Красочность</b>\n\n"
        "Разница не только в цене, но и в том, как клиент будет взаимодействовать с вашей листовкой.\n\n"
        "🎨 <b>4+0 (Цветная с одной стороны)</b>\n"
        "<b>Для чего:</b> Идеально, если листовка будет клеиться на стену, доску объявлений или вставляться в прозрачные карманы в транспорте.\n"
        "✅ <b>Плюс:</b> Это дешевле. Нет смысла платить за вторую сторону, если её никто не увидит.\n\n"
        "🎨 <b>4+4 (Цветная с двух сторон)</b>\n"
        "<b>Для чего:</b> Для раздачи в руки на улице или на выставках.\n"
        "✅ <b>Плюс:</b> Увеличивает «глубину контакта» с потребителем. Если человек перевернет листовку и увидит там пустой лист, вы упустили 50% рекламной площади.\n\n"
        "💡 <b>Совет:</b> Используйте вторую сторону для подробностей: схем проезда, подробного прайса или технических характеристик товара."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="back_to_color")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(StateFilter(CalcLeaflets), F.data == "back_to_color")
async def back_to_color_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_2(callback.message, state)

# ==========================================
# 3. ПОСЛЕПЕЧАТНАЯ ОБРАБОТКА
# ==========================================
@router.callback_query(CalcLeaflets.step_color, F.data.startswith("l_col_"))
async def step_3_processing(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    color = "4+0 (1 ст)" if "4+0" in callback.data else "4+4 (2 ст)"
    await state.update_data(color=color)
    await render_step_3(callback.message, state)

async def render_step_3(message: types.Message, state: FSMContext):
    await state.set_state(CalcLeaflets.step_processing)
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 3)}"
        "📍 <b>Шаг 3. Обработка</b>\n\n"
        "Почти готово! Финишная обработка определяет, насколько удобно будет пользоваться вашим изделием и как долго оно сохранит презентабельный вид.\n\n"
        "<b>Выберите тип обработки:</b>\n"
        "• ❌ <b>Без обработки</b> — Простая нарезка в размер.\n"
        "• 📂 <b>Фальцовка (1-2 сгиба)</b> — Для открыток или евробуклетов.\n"
        "• 📚 <b>Фальцовка (3-4 сгиба)</b> — Для инструкций и мини-каталогов.\n"
        "• 🎟 <b>Перфорация (1 линия)</b> — Линия для легкого отрыва купона или билета.\n"
        "• 🫧 <b>Скругление углов</b> — Чтобы листовка не «мохрилась» и выглядела аккуратнее.\n"
        "• 🔢 <b>Нумерация</b> — Для учета тиража, лотерей или уникальных промокодов.\n\n"
        "💡 <i>Зачем это нужно? Нажмите кнопку «Справка», чтобы узнать, как эти «мелочи» повышают эффективность вашей рекламы.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Без обработки", callback_data="l_prc_Без обработки")],
        [InlineKeyboardButton(text="📂 Фальцовка 1-2 сгиба", callback_data="l_prc_Фальцовка 1-2"),
         InlineKeyboardButton(text="📚 Фальцовка 3-4 сгиба", callback_data="l_prc_Фальцовка 3-4")],
        [InlineKeyboardButton(text="🎟 Перфорация", callback_data="l_prc_Перфорация")],
        [InlineKeyboardButton(text="🫧 Скругление углов", callback_data="l_prc_Скругление"),
         InlineKeyboardButton(text="🔢 Нумерация", callback_data="l_prc_Нумерация")],
        [InlineKeyboardButton(text="📖 Справка", callback_data="info_l_proc")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_color")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(StateFilter(CalcLeaflets.step_processing), F.data == "info_l_proc")
async def info_l_proc_handler(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "📖 <b>Гид по финишной обработке</b>\n\n"
        "Финишная обработка превращает обычный лист бумаги в функциональный инструмент. Вот что вам нужно знать перед выбором:\n\n"
        "📂 <b>Фальцовка (Складывание)</b>\n"
        "Это не просто сгиб, это архитектура вашей информации. Каждый сгиб — мозг считывает как переход к новой теме.\n\n"
        "🎟 <b>Перфорация (Линия отрыва)</b>\n"
        "Самый мощный инструмент интерактива. Физическое действие — отрыв купона — создает психологическую привязку к вашей скидке. Служит защитой от подделок.\n\n"
        "🫧 <b>Скругление углов</b>\n"
        "Скругление делает продукт «дружелюбным» и премиальным. Практика: углы не расслаиваются и не пачкаются в карманах. Листовка выглядит новой в 2-3 раза дольше.\n\n"
        "🔢 <b>Нумерация</b>\n"
        "Присвойте уникальные номера листовкам для контроля тиража, проведения лотерей и защиты скидочных карт от копирования.\n\n"
        "⚠️ <b>Совет:</b> Если выбрали плотную бумагу (от 150 г/м²) для фальцовки, мы обязательно добавим биговку, чтобы избежать трещин краски."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="back_to_proc")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(StateFilter(CalcLeaflets), F.data == "back_to_proc")
async def back_to_proc_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_3(callback.message, state)

# ==========================================
# 4. ТИП БУМАГИ (МАТЕРИАЛ)
# ==========================================
@router.callback_query(CalcLeaflets.step_processing, F.data.startswith("l_prc_"))
async def step_4_paper_type(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    proc = callback.data.replace("l_prc_", "")
    await state.update_data(processing=proc)
    await render_step_4(callback.message, state)

async def render_step_4(message: types.Message, state: FSMContext):
    await state.set_state(CalcLeaflets.step_paper_type)
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 4)}"
        "📍 <b>Шаг 4. Выбор материала</b>\n\n"
        "Теперь выберем «лицо» вашего заказа — материал. От этого зависит, насколько сочными будут цвета и как долго листовка проживет в руках у клиента.\n\n"
        "<b>Выберите тип бумаги:</b>\n"
        "• ✨ <b>Мелованная (глянец)</b> — Максимальная яркость и «сочные» фото.\n"
        "• ☁️ <b>Матовая</b> — Солидный вид без бликов, удобно читать текст.\n"
        "• 📄 <b>Офсетная</b> — Привычная «бумажная» фактура, бюджетно и функционально.\n"
        "• 🧱 <b>Картон</b> — Для тех, кому нужна жесткость и долговечность.\n"
        "• 🎯 <b>Самоклейка</b> — Печать на клейкой основе (бумага или винил).\n"
        "• 👑 <b>Дизайнерская</b> — Элитные материалы с уникальной текстурой и цветом.\n\n"
        "💡 <i>Не знаете, что лучше? Нажмите кнопку «Справка», я разложил все материалы по полочкам.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Мелованная", callback_data="pt_Мелованная"),
         InlineKeyboardButton(text="☁️ Матовая", callback_data="pt_Матовая")],
        [InlineKeyboardButton(text="📝 Офсетная", callback_data="pt_Офсетная"),
         InlineKeyboardButton(text="📦 Картон", callback_data="pt_Картон")],
        [InlineKeyboardButton(text="🎞 Самоклейка", callback_data="pt_Самоклейка"),
         InlineKeyboardButton(text="🎨 Дизайнерская", callback_data="pt_Дизайнерская")],
        [InlineKeyboardButton(text="📖 Справка", callback_data="info_l_ptype")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_proc")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(StateFilter(CalcLeaflets.step_paper_type), F.data == "info_l_ptype")
async def info_l_ptype_handler(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "📖 <b>Гид по материалам: Как не ошибиться?</b>\n\n"
        "✨ <b>Мелованная (Глянцевая)</b>\nКраска не впитывается, а остается на поверхности. Идеально для «вкусных» картинок еды или косметики.\n\n"
        "☁️ <b>Матовая</b>\nРассеивает свет, исключая блики. Для презентаций и брошюр с большим количеством текста.\n\n"
        "📄 <b>Офсетная</b>\nБез покрытия, пористая. Самый бюджетный вариант для массовых рассылок и информационных объявлений.\n\n"
        "🧱 <b>Картон</b>\nМногослойный материал повышенной плотности (от 230 до 520 г/м²). Выглядит как ценный объект.\n\n"
        "🎯 <b>Самоклейка</b>\nБумажная или пленочная (виниловая). Наклейки на товары, витрины или авто.\n\n"
        "👑 <b>Дизайнерская</b>\nЭлитные материалы: лен, кожа, металлик. Когда нужно подчеркнуть статус бренда."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="back_to_paper_type_root")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(StateFilter(CalcLeaflets), F.data == "back_to_paper_type_root")
async def back_to_paper_type_root_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_4(callback.message, state)

# ==========================================
# 5. ПЛОТНОСТЬ БУМАГИ
# ==========================================
@router.callback_query(CalcLeaflets.step_paper_type, F.data.startswith("pt_"))
async def step_5_paper_weight(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    p_type = callback.data.replace("pt_", "")
    await state.update_data(p_type=p_type)
    await render_step_5(callback.message, state)

async def render_step_5(message: types.Message, state: FSMContext):
    await state.set_state(CalcLeaflets.step_paper_weight)
    data = await state.get_data()
    p_type = data.get('p_type')
    
    weights = []
    if p_type in ["Мелованная", "Матовая"]:
        weights = ["80", "90","105", "115", "130", "150", "170", "200", "250", "300", "350"]
    elif p_type == "Офсетная":
        weights = ["65", "80", "100", "120"]
    elif p_type == "Картон":
        weights = ["200", "250", "Добруш 250", "300"]
    else:
        await state.update_data(paper="Стандарт")
        return await render_step_6(message, state)

    text = f"{get_breadcrumbs(data, 5)}⚖️ <b>Шаг 5. Плотность ({p_type})</b>"
    buttons = []
    row = []
    for w in weights:
        row.append(InlineKeyboardButton(text=f"{w} г", callback_data=f"pw_{w}"))
        if len(row) == 3:
            buttons.append(row); row = []
    if row: buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="🔙 К типам бумаги", callback_data="back_to_paper_type_root")])
    await smart_edit(message, text, InlineKeyboardMarkup(inline_keyboard=buttons))

# ==========================================
# 6. ТИРАЖ (КОЛИЧЕСТВО)
# ==========================================
@router.callback_query(CalcLeaflets.step_paper_weight, F.data.startswith("pw_"))
async def step_6_circulation_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    weight = callback.data.replace("pw_", "")
    await state.update_data(paper=f"{weight} г/м²")
    await render_step_6(callback.message, state)

async def render_step_6(message: types.Message, state: FSMContext):
    await state.set_state(CalcLeaflets.step_circulation)
    data = await state.get_data()
    
    text = (
        f"{get_breadcrumbs(data, 6)}"
        "📍 <b>Шаг 6. Тираж (Количество)</b>\n\n"
        "Сколько экземпляров печатаем?\n"
        "Вы можете указать любое количество от 100 штук — просто введите число сообщением. Или воспользуйтесь кнопками.\n\n"
        "💡 <i>Важный нюанс: При тираже от 1000 штук стоимость одного экземпляра падает почти в два раза за счет перехода на офсетную печать.</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1000 шт.", callback_data="l_cnt_1000"),
         InlineKeyboardButton(text="2000 шт.", callback_data="l_cnt_2000")],
        [InlineKeyboardButton(text="3000 шт.", callback_data="l_cnt_3000"),
         InlineKeyboardButton(text="5000 шт.", callback_data="l_cnt_5000")],
        [InlineKeyboardButton(text="📖 Справка", callback_data="info_l_circ")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_weight_internal")]
    ])
    
    # Чтобы избежать дублирования сообщений при вводе текста
    msg = await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.update_data(last_msg_id=msg.message_id)
    if message.message_id != msg.message_id: 
        try: await message.delete()
        except: pass

@router.callback_query(StateFilter(CalcLeaflets.step_circulation), F.data == "info_l_circ")
async def info_l_circ_handler(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "📖 <b>Гид по тиражам: Как количество управляет ценой</b>\n\n"
        "📦 <b>Малые тиражи (от 100 до 500 шт.)</b>\n"
        "Печатаются на цифровых машинах. Это быстро и удобно, но стоимость одной листовки будет максимальной.\n\n"
        "🚀 <b>Средние и большие тиражи (от 1000 шт.)</b>\n"
        "Здесь в игру вступает офсетная печать. Стоимость «приладки» оборудования распределяется на все листы, поэтому печатать 1000 штук часто выгоднее, чем 700.\n\n"
        "💡 <b>Почему стоит брать больше?</b>\n"
        "При большом тираже «стоимость контакта» с одним реальным клиентом остается минимальной."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="back_to_circ_internal")]])
    await smart_edit(callback.message, text, kb)

@router.callback_query(StateFilter(CalcLeaflets), F.data == "back_to_circ_internal")
async def back_to_circ_internal(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_6(callback.message, state)

@router.callback_query(StateFilter(CalcLeaflets), F.data == "back_to_weight_internal")
async def back_to_weight_from_circ(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    p_type = data.get('p_type')
    
    if p_type in ["Самоклейка", "Дизайнерская"]:
        await render_step_4(callback.message, state)
    else:
        await render_step_5(callback.message, state)

# ==========================================
# ФИНАЛЬНОЕ МЕНЮ И РЕГИСТРАЦИЯ
# ==========================================

@router.message(CalcLeaflets.step_circulation)
async def manual_circulation(message: types.Message, state: FSMContext, bot: Bot, db: Database):
    if not message.text.isdigit() or int(message.text) < 100:
        await message.answer("⚠️ Пожалуйста, введите число не меньше 100.")
        return
    await state.update_data(count=message.text)
    data = await state.get_data()
    try: await message.delete()
    except: pass
    await show_final_summary(message, state, bot, db, edit_id=data.get('last_msg_id'))

@router.callback_query(CalcLeaflets.step_circulation, F.data.startswith("l_cnt_"))
async def btn_circulation(callback: types.CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    await callback.answer()
    await state.update_data(count=callback.data.replace("l_cnt_", ""))
    await show_final_summary(callback.message, state, bot, db)

async def show_final_summary(message: types.Message, state: FSMContext, bot: Bot, db: Database, edit_id: int = None):
    data = await state.get_data()
    
    params_text = (
        f"📏 Формат: <b>{data['format']}</b>\n"
        f"🎨 Печать: <b>{data['color']}</b>\n"
        f"🛠 Обработка: <b>{data['processing']}</b>\n"
        f"📄 Материал: <b>{data['p_type']}</b>\n"
        f"⚖️ Плотность: <b>{data.get('paper', 'Стандарт')}</b>\n"
        f"🔢 Тираж: <b>{data['count']} шт.</b>"
    )
    
    await state.update_data(final_summary=params_text)
    user_id = message.chat.id
    profile = await db.get_user(user_id)
    
    # --- ЕДИНАЯ ПРОВЕРКА ПРОФИЛЯ ---
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
            "Вы находитесь на финальном этапе сверки. Пожалуйста, убедитесь, что все параметры указаны верно:\n\n"
            f"{params_text}\n\n"
            "➖➖➖➖➖➖➖➖\n"
            "🚀 <b>Что произойдет дальше?</b>\n"
            "После нажатия кнопки «Отправить», ваши параметры попадут к менеджеру. "
            "Он рассчитает точную стоимость со всеми скидками и свяжется с вами для подтверждения заказа."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 ОТПРАВИТЬ МЕНЕДЖЕРУ", callback_data="l_submit")],
            [InlineKeyboardButton(text="🔄 Изменить параметры", callback_data="prod_Листовки")]
        ])
    else:
        text = (
            "🏁 <b>Ваш заказ сформирован!</b>\n\n"
            "Вы успешно собрали конфигурацию будущих листовок:\n\n"
            f"{params_text}\n\n"
            "➖➖➖➖➖➖➖➖\n"
            "👋 <b>Давайте знакомиться!</b>\n"
            "Чтобы менеджер мог рассчитать стоимость и связаться с вами, нужно заполнить контактные данные.\n"
            "<i>Это нужно сделать всего один раз, данные сохранятся для будущих заказов.</i>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 ПРЕДСТАВИТЬСЯ И ОТПРАВИТЬ", callback_data="l_reg_start")],
            [InlineKeyboardButton(text="🔄 Начать сначала", callback_data="prod_Листовки")]
        ])

    if edit_id:
        try: await bot.edit_message_text(chat_id=user_id, message_id=edit_id, text=text, reply_markup=kb, parse_mode="HTML")
        except: await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await smart_edit(message, text, kb)

# --- РЕГИСТРАЦИЯ (Унифицированная) ---

@router.callback_query(F.data == "l_reg_start")
async def reg_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CalcLeaflets.reg_name)
    await callback.message.answer("✍️ Введите ваше <b>Имя</b>:", parse_mode="HTML")

@router.message(CalcLeaflets.reg_name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(reg_name=message.text)
    await state.set_state(CalcLeaflets.reg_phone)
    await message.answer("📞 Введите ваш <b>Телефон</b>:", parse_mode="HTML")

@router.message(CalcLeaflets.reg_phone)
async def reg_phone(message: types.Message, state: FSMContext):
    await state.update_data(reg_phone=message.text)
    await state.set_state(CalcLeaflets.reg_city)
    await message.answer("🏙 Введите ваш <b>Город</b>:", parse_mode="HTML")

@router.message(CalcLeaflets.reg_city)
async def reg_city(message: types.Message, state: FSMContext):
    await state.update_data(reg_city=message.text)
    await state.set_state(CalcLeaflets.reg_address)
    await message.answer("🚚 Введите <b>Адрес доставки</b>:", parse_mode="HTML")

@router.message(CalcLeaflets.reg_address)
async def reg_address(message: types.Message, state: FSMContext, bot: Bot, db: Database):
    data = await state.get_data()
    await db.update_user_profile(
        message.chat.id, 
        full_name=data['reg_name'], 
        phone=data['reg_phone'],
        city=data['reg_city'], 
        address=message.text
    )
    await message.answer("✅ Контакты сохранены! Отправляем заказ...")
    await finalize_order(message.chat, state, bot, message, db)

@router.callback_query(F.data == "l_submit")
async def final_submit_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    await callback.answer()
    await finalize_order(callback.message.chat, state, bot, callback.message, db)

async def finalize_order(user_obj, state: FSMContext, bot: Bot, message_obj, db: Database):
    data = await state.get_data()
    
    params = {
        "format": data.get('format'),
        "color": data.get('color'),
        "processing": data.get('processing'),
        "paper_type": data.get('p_type'),
        "paper_weight": data.get('paper'),
        "count": data.get('count')
    }
    
    order = Order(
        user_id=user_obj.id,
        category="Листовки",
        params=params,
        description=data.get('final_summary')
    )
    
    order_id = await db.create_order(order)
    
    # Уведомления
    admin_ids = [x.strip() for x in os.getenv("ADMIN_ID", "").split(",") if x.strip()]
    manager_ids = await db.get_managers()
    all_notif_ids = list(set(admin_ids + [str(mid) for mid in manager_ids]))
    
    db_user = await db.get_user(user_obj.id)
    client_name = db_user.full_name if db_user and db_user.full_name else (user_obj.first_name if hasattr(user_obj, 'first_name') else "Клиент")
    client_phone = db_user.phone if db_user and db_user.phone else "-"
    username_str = f"(@{user_obj.username})" if hasattr(user_obj, 'username') and user_obj.username else ""

    admin_text = (
        f"⚡️ <b>НОВЫЙ ЗАКАЗ #{order_id} (Листовки)</b>\n"
        f"👤 {client_name} {username_str}\n"
        f"📞 {client_phone}\n\n"
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
        "Менеджер уже получил уведомление и приступил к расчету. Обычно это занимает от 15 до 30 минут в рабочее время.\n\n"
        "<b>Куда отправимся дальше?</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )
