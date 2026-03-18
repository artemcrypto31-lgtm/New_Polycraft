from aiogram import Router, F, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import Database
from models import Order
from handlers.common import send_order_to_managers
from handlers.orders import kb_cat_promo, TEXT_PROMO

router = Router()
TOTAL_STEPS = 5

class CalcBooklets(StatesGroup):
    step_format = State()
    step_custom_size = State()
    step_color = State()
    step_processing = State()
    step_paper = State()
    step_circulation = State()
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
    lines = []
    if current_step > 1: lines.append(f"📐 Формат: <b>{data.get('format', '???')}</b>")
    if current_step > 2: lines.append(f"🎨 Цветность: <b>{data.get('color', '???')}</b>")
    if current_step > 3: lines.append(f"⚙️ Обработка: <b>{data.get('processing', '???')}</b>")
    if current_step > 4: lines.append(f"📄 Бумага: <b>{data.get('paper', '???')}</b>")
    history = ("📝 <b>Ваш заказ:</b>\n" + "\n".join(lines) + "\n➖➖➖➖➖➖➖➖\n") if lines else ""
    return progress + history

async def smart_edit(message: types.Message, text: str, kb: InlineKeyboardMarkup):
    try:
        await message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await message.answer(text=text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.in_({"prod_Буклеты", "calc_booklets_start"}))
async def step_1_format(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(CalcBooklets.step_format)
    text = (
        f"{get_breadcrumbs({}, 1)}"
        "📐 <b>Шаг 1. Формат буклета в развёрнутом виде</b>\n"
        "Укажите размер листа до сложения.\n\n"
        "💡 <i>Например, буклет А5 — это лист А4, сложенный пополам.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="А3 (420×297)", callback_data="bkl_fmt_A3"),
         InlineKeyboardButton(text="А4 (297×210)", callback_data="bkl_fmt_A4")],
        [InlineKeyboardButton(text="А5 (210×148)", callback_data="bkl_fmt_A5"),
         InlineKeyboardButton(text="А6 (148×105)", callback_data="bkl_fmt_A6")],
        [InlineKeyboardButton(text="210×98", callback_data="bkl_fmt_210x98"),
         InlineKeyboardButton(text="210×200", callback_data="bkl_fmt_210x200")],
        [InlineKeyboardButton(text="📏 Свой размер", callback_data="bkl_fmt_custom")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="stop_calc_booklets")]
    ])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "stop_calc_booklets")
async def stop_calc(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(TEXT_PROMO, reply_markup=kb_cat_promo(), parse_mode="HTML")

@router.callback_query(CalcBooklets.step_format, F.data == "bkl_fmt_custom")
async def custom_size_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CalcBooklets.step_custom_size)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="calc_booklets_start")]
    ])
    await callback.message.edit_text(
        "📏 <b>Введите Ширину x Высоту в мм через пробел:</b>\n<i>Пример: 420 297</i>",
        reply_markup=kb, parse_mode="HTML"
    )

@router.message(CalcBooklets.step_custom_size)
async def process_custom_size(message: types.Message, state: FSMContext):
    try:
        await message.delete()
    except: pass
    try:
        parts = message.text.split()
        if len(parts) != 2: raise ValueError
        w, h = map(int, parts)
        await state.update_data(format=f"{w}×{h} мм")
        await state.set_state(CalcBooklets.step_color)
        data = await state.get_data()
        await render_step_2(message, state, data)
    except:
        await message.answer("⚠️ Введите два числа через пробел (например: 420 297)")

@router.callback_query(CalcBooklets.step_format, F.data.startswith("bkl_fmt_"))
async def process_format(callback: types.CallbackQuery, state: FSMContext):
    fmt = callback.data.replace("bkl_fmt_", "")
    await state.update_data(format=fmt)
    await callback.answer()
    data = await state.get_data()
    await render_step_2(callback.message, state, data)

async def render_step_2(message: types.Message, state: FSMContext, data: dict):
    await state.set_state(CalcBooklets.step_color)
    text = (
        f"{get_breadcrumbs(data, 2)}"
        "🎨 <b>Шаг 2. Цветность печати</b>\n\n"
        "• <b>4+4</b> — полноцвет с двух сторон\n"
        "• <b>3+3</b> — три краски с двух сторон\n"
        "• <b>2+2</b> — два цвета с двух сторон\n"
        "• <b>1+1</b> — чёрно-белый с двух сторон\n"
        "• <b>К+К</b> — только чёрный цвет"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="4+4", callback_data="bkl_col_4+4"),
         InlineKeyboardButton(text="3+3", callback_data="bkl_col_3+3"),
         InlineKeyboardButton(text="2+2", callback_data="bkl_col_2+2")],
        [InlineKeyboardButton(text="1+1", callback_data="bkl_col_1+1"),
         InlineKeyboardButton(text="К+К", callback_data="bkl_col_К+К")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="calc_booklets_start")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(CalcBooklets.step_color, F.data.startswith("bkl_col_"))
async def process_color(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(color=callback.data.replace("bkl_col_", ""))
    await callback.answer()
    data = await state.get_data()
    await render_step_3(callback.message, state, data)

async def render_step_3(message: types.Message, state: FSMContext, data: dict):
    await state.set_state(CalcBooklets.step_processing)
    text = (
        f"{get_breadcrumbs(data, 3)}"
        "⚙️ <b>Шаг 3. Послепечатная обработка</b>\n\n"
        "• <b>Без обработки</b> — просто нарезка\n"
        "• <b>Фальцовка 1-2 фальца</b> — сложить 1 или 2 раза\n"
        "• <b>Фальцовка 3-4 фальца</b> — сложить 3 или 4 раза (гармошка)\n\n"
        "💡 <i>Большинство буклетов делаются с 1 фальцом (сложены пополам).</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Без обработки", callback_data="bkl_prc_Без обработки")],
        [InlineKeyboardButton(text="📂 Фальцовка 1-2 фальца", callback_data="bkl_prc_Фальцовка 1-2 фальца")],
        [InlineKeyboardButton(text="📚 Фальцовка 3-4 фальца", callback_data="bkl_prc_Фальцовка 3-4 фальца")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="bkl_back_step_2")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "bkl_back_step_2")
async def back_to_step_2(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await render_step_2(callback.message, state, data)

@router.callback_query(CalcBooklets.step_processing, F.data.startswith("bkl_prc_"))
async def process_processing(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(processing=callback.data.replace("bkl_prc_", ""))
    await callback.answer()
    data = await state.get_data()
    await render_step_4(callback.message, state, data)

async def render_step_4(message: types.Message, state: FSMContext, data: dict):
    await state.set_state(CalcBooklets.step_paper)
    text = (
        f"{get_breadcrumbs(data, 4)}"
        "📄 <b>Шаг 4. Выбор бумаги</b>\n\n"
        "⭐ Рекомендуем мелованную 150 г/м² — оптимальное соотношение качества и цены.\n\n"
        "<b>Мелованная (глянцевая):</b>\n"
        "• 80, 90, 115, <b>150★</b>, 170 г/м²\n\n"
        "<b>Офсетная (матовая):</b>\n"
        "• 70, 80, 120 г/м²"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Мел. 80 г", callback_data="bkl_pap_Мелованная 80 г/м²"),
         InlineKeyboardButton(text="✨ Мел. 90 г", callback_data="bkl_pap_Мелованная 90 г/м²"),
         InlineKeyboardButton(text="✨ Мел. 115 г", callback_data="bkl_pap_Мелованная 115 г/м²")],
        [InlineKeyboardButton(text="⭐ Мел. 150 г (рек.)", callback_data="bkl_pap_Мелованная 150 г/м²")],
        [InlineKeyboardButton(text="✨ Мел. 170 г", callback_data="bkl_pap_Мелованная 170 г/м²")],
        [InlineKeyboardButton(text="📝 Офс. 70 г", callback_data="bkl_pap_Офсетная 70 г/м²"),
         InlineKeyboardButton(text="📝 Офс. 80 г", callback_data="bkl_pap_Офсетная 80 г/м²"),
         InlineKeyboardButton(text="📝 Офс. 120 г", callback_data="bkl_pap_Офсетная 120 г/м²")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="bkl_back_step_3")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "bkl_back_step_3")
async def back_to_step_3(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await render_step_3(callback.message, state, data)

@router.callback_query(CalcBooklets.step_paper, F.data.startswith("bkl_pap_"))
async def process_paper(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(paper=callback.data.replace("bkl_pap_", ""))
    await callback.answer()
    data = await state.get_data()
    await render_step_5(callback.message, state, data)

async def render_step_5(message: types.Message, state: FSMContext, data: dict):
    await state.set_state(CalcBooklets.step_circulation)
    text = (
        f"{get_breadcrumbs(data, 5)}"
        "🔢 <b>Шаг 5. Тираж</b>\n"
        "Сколько экземпляров буклетов вам нужно?\n\n"
        "<i>Выберите из списка или введите число вручную в чат.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="100", callback_data="bkl_cnt_100"),
         InlineKeyboardButton(text="250", callback_data="bkl_cnt_250"),
         InlineKeyboardButton(text="500", callback_data="bkl_cnt_500")],
        [InlineKeyboardButton(text="1 000", callback_data="bkl_cnt_1000"),
         InlineKeyboardButton(text="2 000", callback_data="bkl_cnt_2000"),
         InlineKeyboardButton(text="5 000", callback_data="bkl_cnt_5000")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="bkl_back_step_4")]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "bkl_back_step_4")
async def back_to_step_4(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await render_step_4(callback.message, state, data)

@router.callback_query(CalcBooklets.step_circulation, F.data.startswith("bkl_cnt_"))
async def process_cnt_btn(callback: types.CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    await state.update_data(count=callback.data.replace("bkl_cnt_", ""))
    await callback.answer()
    await show_summary(callback.message, state, db)

@router.message(CalcBooklets.step_circulation)
async def process_cnt_text(message: types.Message, state: FSMContext, db: Database, bot: Bot):
    try: await message.delete()
    except: pass
    if not message.text.isdigit() or int(message.text) < 1:
        await message.answer("⚠️ Введите только число (например: 500)")
        return
    await state.update_data(count=message.text)
    await show_summary(message, state, db)

async def show_summary(message: types.Message, state: FSMContext, db: Database):
    data = await state.get_data()
    summary = (
        f"🧾 <b>ПРОВЕРКА ДАННЫХ: БУКЛЕТЫ</b>\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"📐 Формат: <b>{data.get('format', '?')}</b>\n"
        f"🎨 Цветность: <b>{data.get('color', '?')}</b>\n"
        f"⚙️ Обработка: <b>{data.get('processing', '?')}</b>\n"
        f"📄 Бумага: <b>{data.get('paper', '?')}</b>\n"
        f"🔢 Тираж: <b>{data.get('count', '?')} шт.</b>"
    )
    await state.update_data(final_summary=summary)

    profile = await db.get_user(message.chat.id)
    is_complete = profile and profile.full_name and profile.phone and profile.city and profile.address

    if is_complete:
        text = (
            "🏁 <b>Проверьте ваш заказ:</b>\n\n"
            f"{summary}\n\n➖➖➖➖➖➖➖➖\n"
            "Нажмите кнопку — менеджер получит заявку и рассчитает стоимость за 15-30 минут. 💬"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 ОТПРАВИТЬ МЕНЕДЖЕРУ", callback_data="bkl_submit")],
            [InlineKeyboardButton(text="🔄 Начать сначала", callback_data="calc_booklets_start")]
        ])
    else:
        text = (
            "🏁 <b>Заказ сформирован!</b>\n\n"
            f"{summary}\n\n➖➖➖➖➖➖➖➖\n"
            "👋 Для отправки менеджеру нужны ваши контакты. Это займёт минуту и сохранится навсегда."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 ПРЕДСТАВИТЬСЯ И ОТПРАВИТЬ", callback_data="bkl_reg_start")],
            [InlineKeyboardButton(text="🔄 Начать сначала", callback_data="calc_booklets_start")]
        ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "bkl_reg_start")
async def reg_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CalcBooklets.reg_name)
    await callback.message.answer("✍️ Введите ваше <b>Имя</b>:", parse_mode="HTML")

@router.message(CalcBooklets.reg_name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(reg_name=message.text)
    await state.set_state(CalcBooklets.reg_phone)
    await message.answer("📞 Введите ваш <b>Телефон</b>:", parse_mode="HTML")

@router.message(CalcBooklets.reg_phone)
async def reg_phone(message: types.Message, state: FSMContext):
    await state.update_data(reg_phone=message.text)
    await state.set_state(CalcBooklets.reg_city)
    await message.answer("🏙 Введите ваш <b>Город</b>:", parse_mode="HTML")

@router.message(CalcBooklets.reg_city)
async def reg_city(message: types.Message, state: FSMContext):
    await state.update_data(reg_city=message.text)
    await state.set_state(CalcBooklets.reg_address)
    await message.answer("🚚 Введите <b>Адрес доставки</b>:", parse_mode="HTML")

@router.message(CalcBooklets.reg_address)
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

@router.callback_query(F.data == "bkl_submit")
async def submit_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    await callback.answer()
    await finalize_order(callback.message.chat, state, bot, callback.message, db)

async def finalize_order(user_obj, state: FSMContext, bot: Bot, message_obj, db: Database):
    data = await state.get_data()
    summary = data.get('final_summary', '')
    order = Order(
        user_id=user_obj.id,
        category="Буклеты",
        params={
            "format": data.get('format'),
            "color": data.get('color'),
            "processing": data.get('processing'),
            "paper": data.get('paper'),
            "count": data.get('count')
        },
        description=summary
    )
    order_id = await db.create_order(order)
    await send_order_to_managers(order_id, user_obj.id, summary, "Буклеты", bot, db)
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="main_profile")],
        [InlineKeyboardButton(text="🏗 В каталог", callback_data="main_constructor")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])
    await message_obj.answer(
        f"✨ <b>Заказ #{order_id} отправлен!</b>\n\n"
        "Менеджер получил заявку на буклеты и подготовит расчёт стоимости. "
        "Ответ придёт прямо в этот чат в течение 15-30 минут. 💬\n\n"
        "<b>Спасибо, что выбираете «Поликрафт»!</b> 🙌",
        reply_markup=kb, parse_mode="HTML"
    )
