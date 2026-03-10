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

# Машина состояний (все шаги опроса)
class CalcFlyers(StatesGroup):
    step_print_type = State()   # 1. Тип печати
    step_format = State()       # 2. Формат
    step_paper_type = State()    # 3. Тип бумаги (НОВОЕ)
    step_paper_weight = State()  # 4. Плотность бумаги (НОВОЕ)
    step_color = State()        # 5. Цвет
    step_processing = State()   # 6. Обработка
    step_circulation = State()  # 7. Тираж
    
    # Данные для регистрации
    reg_name = State()
    reg_phone = State()
    reg_city = State()
    reg_address = State()

def get_breadcrumbs(data: dict, current_step: int) -> str:
    """Генерирует 'хлебные крошки' — историю выбора пользователя"""
    lines = []
    if current_step > 1: lines.append(f"🖨 Печать: <b>{data.get('print_type', '???')}</b>")
    if current_step > 2: lines.append(f"📏 Формат: <b>{data.get('format', '???')}</b>")
    if current_step > 3: lines.append(f"📄 Бумага: <b>{data.get('p_type', '???')}</b>")
    if current_step > 4: lines.append(f"⚖️ Плотность: <b>{data.get('paper', '???')}</b>")
    if current_step > 5: lines.append(f"🎨 Цвет: <b>{data.get('color', '???')}</b>")
    if current_step > 6: lines.append(f"⚙️ Доп: <b>{data.get('processing', '???')}</b>")
    if current_step > 7: lines.append(f"🔢 Тираж: <b>{data.get('count', '???')} шт.</b>")
    
    return ("📝 <b>Ваш заказ:</b>\n" + "\n".join(lines) + "\n➖➖➖➖➖➖➖➖\n") if lines else ""

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
# 1️⃣ БЛОК 1: ВЫБОР ТЕХНОЛОГИИ ПЕЧАТИ (СТАРТ)
# =======================================================

@router.callback_query(F.data.in_({"prod_Флаеры", "calc_flyers_start"}))
async def step_1_print_type(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(CalcFlyers.step_print_type)
    
    # --- ТЕКСТ ВОПРОСА ---
    text = (
        "🔹 <b>Шаг 1. Выберите технологию печати</b>\n"
        "От технологии зависит цена за тираж и срок изготовления.\n\n"
        "1️⃣ <b>Офсетная печать</b>\n"
        "- Лучше для тиражей от 1000 шт.\n"
        "- Чем больше объем — тем дешевле 1 флаер.\n\n"
        "2️⃣ <b>Цифровая печать</b>\n"
        "- Лучше для тиражей до 1000 шт.\n"
        "- Быстрый запуск, удобно для срочных заказов."
    )
    
    # --- КНОПКИ ---
    kb = InlineKeyboardMarkup(inline_keyboard=[
        # Ряд 1: Два типа печати (для компактности)
        [
            InlineKeyboardButton(text="1️⃣ Офсетная", callback_data="flyer_type_offset"),
            InlineKeyboardButton(text="2️⃣ Цифровая", callback_data="flyer_type_digital")
        ],
        # Ряд 2: Справка
        [InlineKeyboardButton(text="💡 Справка", callback_data="info_print_type")],
        # Ряд 3: Назад (ведет в категорию Листовки/Реклама)
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cat_promo")]
    ])
    
    await smart_edit(callback.message, text, kb)


# --- СПРАВКА ПО ТИПАМ ПЕЧАТИ ---
@router.callback_query(F.data == "info_print_type")
async def info_print_type_handler(callback: types.CallbackQuery):
    await callback.answer()
    
    text = (
        "<b>Справка</b>\n"
        "В чем разница?\n\n"
        
        "🖨 <b>Цифровая печать</b>\n"
        "- Запускается сразу, без подготовки форм\n"
        "- Подходит для 100–500 шт\n"
        "- Идеальна, если нужно срочно\n"
        "- Можно печатать тестовый тираж\n"
        "💡 <i>Если вы делаете первую рекламную кампанию или не уверены в результате — чаще всего выбирают именно её.</i>\n"
        "⚠️ <b>Минус:</b> при больших объемах становится дороже.\n\n"
        
        "🏭 <b>Офсетная печать</b>\n"
        "- Требует подготовки печатных форм\n"
        "- Запуск занимает больше времени\n"
        "- Зато при больших тиражах сильно снижает цену за 1 шт\n"
        "💡 <i>Если вам нужно 1000, 5000 или 10 000 флаеров — это самый выгодный вариант.</i>\n"
        "⚠️ <b>Минус:</b> не подходит для срочных и маленьких тиражей."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="calc_flyers_start")]
    ])
    
    await smart_edit(callback.message, text, kb)


# =======================================================
# 2️⃣ БЛОК 2: ВЫБОР ФОРМАТА
# =======================================================

@router.callback_query(CalcFlyers.step_print_type, F.data.startswith("flyer_type_"))
async def step_2_format(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    # Сохраняем выбор технологии печати
    p_type_code = callback.data.split("_")[2]
    p_type_name = "Офсетная" if p_type_code == "offset" else "Цифровая"
    await state.update_data(print_type=p_type_name, print_code=p_type_code)
    
    await render_step_2(callback, state)

async def render_step_2(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CalcFlyers.step_format)
    data = await state.get_data()
    
    # --- ВАРИАНТ 1: ЦИФРОВАЯ ПЕЧАТЬ (Уведомление) ---
    if data['print_code'] == 'digital':
        text = (
            f"{get_breadcrumbs(data, 2)}"
            "📐 <b>Для цифровой печати доступен формат: Евро (100×210 мм)</b>\n\n"
            "Этот формат оптимален для малых тиражей и быстрого производства."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            # Кнопка "Продолжить" сразу выбирает формат Евро и ведет к Шагу 3
            [InlineKeyboardButton(text="👉 Продолжить", callback_data="flyer_fmt_100x210")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="calc_flyers_start")]
        ])
    
    # --- ВАРИАНТ 2: ОФСЕТНАЯ ПЕЧАТЬ (Выбор из 3-х) ---
    else:
        text = (
            f"{get_breadcrumbs(data, 2)}"
            "🔹 <b>Шаг 2. Выберите формат флаера (Офсетная печать)</b>\n"
            "Формат влияет на внешний вид, восприятие и количество информации, которое можно разместить.\n\n"
            
            "1️⃣ <b>Евро (DL) — 100×210 мм</b>\n"
            "Классический удлинённый формат.\n"
            "<i>Подходит для акций, меню, презентаций услуг.</i>\n\n"
            
            "2️⃣ <b>Mini DL — 148×70 мм</b>\n"
            "Компактный формат.\n"
            "<i>Удобен для кратких предложений и массовой раздачи.</i>\n\n"
            
            "3️⃣ <b>Квадрат — 100×100 мм</b>\n"
            "Современный формат с акцентом на дизайн.\n"
            "<i>Подходит для имиджевой рекламы.</i>"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            # Евро - самый популярный, отдельно
            [InlineKeyboardButton(text="1️⃣ Евро (100х210)", callback_data="flyer_fmt_100x210")],
            # Остальные два - компактно в ряд
            [
                InlineKeyboardButton(text="2️⃣ Mini DL", callback_data="flyer_fmt_148x70"),
                InlineKeyboardButton(text="3️⃣ Квадрат", callback_data="flyer_fmt_100x100")
            ],
            # Справка
            [InlineKeyboardButton(text="💡 Справка", callback_data="flyer_info_format")],
            # Назад
            [InlineKeyboardButton(text="🔙 Назад", callback_data="calc_flyers_start")]
        ])
    
    await smart_edit(callback.message, text, kb)


# --- СПРАВКА ПО ФОРМАТАМ ---
@router.callback_query(F.data == "flyer_info_format")
async def info_format_handler(callback: types.CallbackQuery):
    await callback.answer()
    
    text = (
        "<b>Как выбрать формат?</b>\n"
        "Выбор зависит от задачи: сколько информации нужно разместить и какое впечатление вы хотите произвести.\n\n"
        
        "📄 <b>Евро (DL) — 100×210 мм</b>\n"
        "Самый популярный формат.\n"
        "✔ Вмещает много информации\n"
        "✔ Удобен для меню, прайсов, подробных предложений\n"
        "✔ Легко помещается в конверт DL\n"
        "💡 <i>Чаще всего выбирают для: салонов красоты, ресторанов, строительных услуг, образовательных курсов.</i>\n"
        "👉 Если сомневаетесь — это самый универсальный вариант.\n\n"
        
        "📏 <b>Mini DL — 148×70 мм</b>\n"
        "Узкий и компактный формат.\n"
        "✔ Минимальный расход бумаги\n"
        "✔ Выгоден для массовых раздач\n"
        "✔ Фокус на коротком сообщении\n"
        "💡 <i>Подходит для: скидок и акций, раздачи возле ТЦ, купонов.</i>\n"
        "👉 Не подходит, если нужно разместить много текста.\n\n"
        
        "◼ <b>Квадрат 100×100 мм</b>\n"
        "Современный и визуально заметный формат.\n"
        "✔ Выделяется среди стандартных флаеров\n"
        "✔ Отлично подходит для дизайна с крупной графикой\n"
        "✔ Создает ощущение «дорогого» продукта\n"
        "💡 <i>Чаще выбирают: бренды одежды, кафе, креативные проекты.</i>\n"
        "👉 Если важен визуальный эффект — это сильный вариант."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="flyer_back_step_2")]
    ])
    
    await smart_edit(callback.message, text, kb)

# Вспомогательный хендлер для возврата
@router.callback_query(F.data == "flyer_back_step_2")
async def back_to_step_2_internal(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_2(callback, state)

# =======================================================
# 3️⃣ БЛОК 3: ТИП БУМАГИ (МАТЕРИАЛ)
# =======================================================

@router.callback_query(CalcFlyers.step_format, F.data.startswith("flyer_fmt_"))
async def step_3_paper_type_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    fmt = callback.data.split("_")[2]
    await state.update_data(format=fmt)
    await render_step_3_paper_type(callback.message, state)

async def render_step_3_paper_type(message: types.Message, state: FSMContext):
    await state.set_state(CalcFlyers.step_paper_type)
    data = await state.get_data()
    
    text = (
        f"{get_breadcrumbs(data, 3)}"
        "🔹 <b>Шаг 3. Тип бумаги</b>\n\n"
        "Материал определяет тактильные ощущения и то, как будут выглядеть цвета на вашем флаере.\n\n"
        "<b>Выберите вариант:</b>\n"
        "• ✨ <b>Мелованная (глянец)</b> — Максимальная яркость и «сочные» фото.\n"
        "• ☁️ <b>Матовая</b> — Солидный вид без бликов, удобно читать текст.\n"
        "• 📄 <b>Офсетная</b> — Привычная «бумажная» фактура, бюджетно и функционально.\n"
        "• 📦 <b>Картон</b> — Для тех, кому нужна жесткость и долговечность.\n"
        "• 🎯 <b>Самоклейка</b> — Печать на клейкой основе (бумага или винил).\n"
        "• 👑 <b>Дизайнерская</b> — Элитные материалы с уникальной текстурой и цветом.\n\n"
        "💡 <i>Не знаете, что лучше? Нажмите кнопку «Справка», я разложил все материалы по полочкам.</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Мелованная", callback_data="fly_pt_Мелованная"),
         InlineKeyboardButton(text="☁️ Матовая", callback_data="fly_pt_Матовая")],
        [InlineKeyboardButton(text="📝 Офсетная", callback_data="fly_pt_Офсетная"),
         InlineKeyboardButton(text="📦 Картон", callback_data="fly_pt_Картон")],
        [InlineKeyboardButton(text="🎞 Самоклейка", callback_data="fly_pt_Самоклейка"),
         InlineKeyboardButton(text="🎨 Дизайнерская", callback_data="fly_pt_Дизайнерская")],
        [InlineKeyboardButton(text="📖 Справка", callback_data="flyer_info_paper_type")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="flyer_back_step_2")]
    ])
    await smart_edit(message, text, kb)

# --- СПРАВКА ПО ТИПАМ БУМАГИ ---
@router.callback_query(F.data == "flyer_info_paper_type")
async def info_paper_type_handler(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "📖 <b>Гид по материалам: Как не ошибиться?</b>\n\n"
        "✨ <b>Мелованная (Глянцевая)</b>\nКраска не впитывается, а остается на поверхности. Идеально для «вкусных» картинок еды или косметики.\n\n"
        "☁️ <b>Матовая</b>\nРассеивает свет, исключая блики. Для презентаций и брошюр с большим количеством текста.\n\n"
        "📄 <b>Офсетная</b>\nБез покрытия, пористая. Самый бюджетный вариант для массовых рассылок и информационных объявлений.\n\n"
        "📦 <b>Картон</b>\nМногослойный материал повышенной плотности (от 230 до 520 г/м²). Выглядит как ценный объект.\n\n"
        "🎯 <b>Самоклейка</b>\nБумажная или пленочная (виниловая). Наклейки на товары, витрины или авто.\n\n"
        "👑 <b>Дизайнерская</b>\nЭлитные материалы: лен, кожа, металлик. Когда нужно подчеркнуть статус бренда."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="flyer_back_step_3_pt")]])
    await smart_edit(callback.message, text, kb)


# =======================================================
# 4️⃣ БЛОК 4: ПЛОТНОСТЬ БУМАГИ
# =======================================================

@router.callback_query(CalcFlyers.step_paper_type, F.data.startswith("fly_pt_"))
async def step_4_paper_weight_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    p_type = callback.data.replace("fly_pt_", "")
    await state.update_data(p_type=p_type)
    
    if p_type in ["Самоклейка", "Дизайнерская"]:
        await state.update_data(paper="Стандарт")
        await render_step_5_color(callback.message, state)
    else:
        await render_step_4_paper_weight(callback.message, state)

async def render_step_4_paper_weight(message: types.Message, state: FSMContext):
    await state.set_state(CalcFlyers.step_paper_weight)
    data = await state.get_data()
    p_type = data.get('p_type')
    
    weights = []
    if p_type in ["Мелованная", "Матовая"]:
        weights = ["80", "90", "105", "115", "130", "150", "170", "200", "250", "300", "350"]
    elif p_type == "Офсетная":
        weights = ["65", "80", "100", "120"]
    elif p_type == "Картон":
        weights = ["200", "250", "Добруш 250", "300"]
    
    text = (
        f"{get_breadcrumbs(data, 4)}"
        f"🔹 <b>Шаг 4. Плотность бумаги ({p_type})</b>\n\n"
        "От плотности зависит «вес», долговечность и тактильные ощущения. Тонкие бумаги хороши для массовых раздач, плотные создают ощущение премиальности."
    )
    
    buttons = []
    row = []
    for w in weights:
        row.append(InlineKeyboardButton(text=f"{w} г", callback_data=f"fly_pw_{w}"))
        if len(row) == 3:
            buttons.append(row); row = []
    if row: buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="🔙 К типам бумаги", callback_data="flyer_back_step_3_pt")])
    await smart_edit(message, text, InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "flyer_back_step_3_pt")
async def back_to_pt_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_3_paper_type(callback.message, state)

# =======================================================
# 5️⃣ БЛОК 5: КРАСОЧНОСТЬ (ЦВЕТ)
# =======================================================

@router.callback_query(CalcFlyers.step_paper_weight, F.data.startswith("fly_pw_"))
async def step_5_color_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    weight = callback.data.replace("fly_pw_", "")
    await state.update_data(paper=f"{weight} г/м²")
    await render_step_5_color(callback.message, state)

async def render_step_5_color(message: types.Message, state: FSMContext):
    await state.set_state(CalcFlyers.step_color)
    data = await state.get_data()
    
    # Текст основного вопроса
    text = (
        f"{get_breadcrumbs(data, 5)}"
        "🔹 <b>Шаг 5. Красочность печати</b>\n"
        "Выберите, будет ли печать с одной или с двух сторон.\n\n"
        
        "1️⃣ <b>4+4 — печать с двух сторон</b>\n"
        "Полноцветная печать на лицевой и оборотной стороне.\n"
        "<i>Подходит, если нужно разместить больше информации.</i>\n\n"
        
        "2️⃣ <b>4+0 — печать с одной стороны</b>\n"
        "Полноцветная печать только с лицевой стороны.\n"
        "<i>Подходит для лаконичных и простых сообщений.</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        # Ряд 1: Основные варианты (Компактно)
        [
            InlineKeyboardButton(text="1️⃣ 4+4 (2 стороны)", callback_data="flyer_col_4+4"),
            InlineKeyboardButton(text="2️⃣ 4+0 (1 сторона)", callback_data="flyer_col_4+0")
        ],
        
        # Ряд 2: Навигация (Справка и Назад вместе)
        [
            InlineKeyboardButton(text="💡 Справка", callback_data="flyer_info_color"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="flyer_back_step_4_pw")
        ]
    ])
    await smart_edit(message, text, kb)

@router.callback_query(F.data == "flyer_back_step_4_pw")
async def back_to_pw_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_4_paper_weight(callback.message, state)


# --- СПРАВКА ПО ЦВЕТНОСТИ ---
@router.callback_query(F.data == "flyer_info_color")
async def info_color_handler(callback: types.CallbackQuery):
    await callback.answer()
    
    text = (
        "📌 <b>Справка</b>\n"
        "<b>Что означают 4+4 и 4+0?</b>\n\n"
        "Цифра «4» — это полноцветная печать (CMYK).\n"
        "Первая цифра обозначает лицевую сторону, вторая — оборотную.\n"
        "• <b>4+4</b> — цветная печать с двух сторон.\n"
        "• <b>4+0</b> — цветная печать только с одной стороны, оборот остаётся чистым.\n\n"
        
        "🖨 <b>4+0 — печать с одной стороны</b>\n"
        "<b>Подходит, если:</b>\n"
        "• на флаере одно основное предложение\n"
        "• текст занимает немного места\n"
        "• нужен минималистичный дизайн\n"
        "• обратная сторона не требуется\n"
        "💡 <i>Чаще выбирают для: кратких акций, анонсов, массовой раздачи.</i>\n\n"
        
        "🖨 <b>4+4 — печать с двух сторон</b>\n"
        "<b>Подходит, если:</b>\n"
        "• информации больше, чем помещается на одной стороне\n"
        "• нужно разместить контакты, карту, соцсети\n"
        "• есть несколько услуг или предложений\n"
        "💡 <i>Чаще выбирают для: меню, презентации услуг, подробных рекламных предложений.</i>\n\n"
        
        "<b>Как быстро понять, что выбрать?</b>\n"
        "👉 Если всё сообщение легко помещается на одну сторону — выбирайте 4+0.\n"
        "👉 Если информации много или хочется использовать флаер максимально — выбирайте 4+4."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        # Возврат именно в Шаг 5
        [InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="flyer_back_step_5_internal")]
    ])
    
    await smart_edit(callback.message, text, kb)

# Вспомогательный хендлер для возврата в Шаг 5 из справки
@router.callback_query(F.data == "flyer_back_step_5_internal")
async def back_to_step_5_internal(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_5_color(callback.message, state)

# =======================================================
# 6️⃣ БЛОК 6: ДОПОЛНИТЕЛЬНАЯ ОБРАБОТКА
# =======================================================

@router.callback_query(CalcFlyers.step_color, F.data.startswith("flyer_col_"))
async def step_6_processing(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    col = callback.data.split("_")[2]
    await state.update_data(color=col)
    await render_step_6(callback, state)

async def render_step_6(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CalcFlyers.step_processing)
    data = await state.get_data()
    
    # Получаем список выбранных опций (для мультивыбора)
    selected = data.get('processing_list', [])
    if not isinstance(selected, list): selected = []
    
    def get_mark(val):
        return " ✅" if val in selected else ""
    
    text = (
        f"{get_breadcrumbs(data, 6)}"
        "🔹 <b>Шаг 6. Дополнительная обработка</b>\n"
        "Выберите, нужна ли дополнительная обработка флаера после печати.\n"
        "<i>(Можно выбрать несколько вариантов)</i>\n\n"
        "1️⃣ <b>Без обработки</b>\n"
        "Стандартный флаер без дополнительных элементов.\n\n"
        "2️⃣ <b>Перфорация</b>\n"
        "Линия отрыва на флаере.\n\n"
        "3️⃣ <b>Фальц (1–2 сгиба)</b>\n"
        "Сгиб флаера в один или два раза."
    )
    
    kb_rows = [
        # Вариант "Без обработки" - ведет дальше сразу
        [InlineKeyboardButton(text="1️⃣ Без обработки", callback_data="flyer_proc_Нет")],
        [
            InlineKeyboardButton(text=f"2️⃣ Перфорация{get_mark('Перфорация')}", callback_data="flyer_proc_Перфорация"),
            InlineKeyboardButton(text=f"3️⃣ Фальц (1-2){get_mark('Фальц')}", callback_data="flyer_proc_Фальц")
        ]
    ]
    
    # Кнопка "Продолжить" появляется, если выбрана хотя бы одна доп. опция
    if selected:
        kb_rows.append([InlineKeyboardButton(text="👉 Продолжить", callback_data="flyer_proc_done")])
        
    # Навигация
    kb_rows.append([
        InlineKeyboardButton(text="💡 Справка", callback_data="flyer_info_proc"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="flyer_back_step_5")
    ])
    
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    await smart_edit(callback.message, text, kb)


# --- СПРАВКА ПО ОБРАБОТКЕ ---
@router.callback_query(F.data == "flyer_info_proc")
async def info_proc_handler(callback: types.CallbackQuery):
    await callback.answer()
    
    text = (
        "📌 <b>Справка</b>\n"
        "<b>Что такое дополнительная обработка?</b>\n"
        "Это элементы, которые добавляются после печати и меняют функциональность флаера.\n\n"
        "📄 <b>Без обработки</b>\n"
        "Флаер остаётся в стандартном виде — цельный лист без сгибов и отрывных частей.\n"
        "<b>Подходит, если:</b>\n"
        "• информация размещена компактно\n"
        "• флаер будет раздаваться массово\n"
        "• не требуется дополнительных функций\n"
        "👉 <i>Самый универсальный вариант.</i>\n\n"
        "✂ <b>Перфорация (линия отрыва)</b>\n"
        "На флаере делается специальная пунктирная линия, по которой можно аккуратно оторвать часть.\n"
        "<b>Подходит, если:</b>\n"
        "• нужен купон на скидку\n"
        "• требуется отрывной талон\n"
        "• нужно оставить контакт или промокод\n"
        "• флаер участвует в акции\n"
        "💡 <i>Часто используется для: салонов красоты, фитнес-клубов, магазинов, мероприятий с регистрацией.</i>\n"
        "⚠️ <b>Важно:</b> отрывная часть должна быть предусмотрена в макете.\n\n"
        "📂 <b>Фальц (1–2 сгиба)</b>\n"
        "Флаер складывается в один или два раза.\n"
        "<b>Подходит, если:</b>\n"
        "• информации много\n"
        "• нужно структурировать текст по блокам\n"
        "• требуется формат мини-буклета\n"
        "<i>1 сгиб — флаер складывается пополам.</i>\n"
        "<i>2 сгиба — формат «гармошка» или «евробуклет».</i>\n"
        "💡 <i>Часто выбирают для: меню, прайсов, презентации услуг, подробных коммерческих предложений.</i>\n"
        "⚠️ <b>Важно:</b> при выборе фальца макет должен быть подготовлен с учетом сгибов."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="flyer_back_step_6_internal")]
    ])
    
    await smart_edit(callback.message, text, kb)

# Вспомогательный хендлер для возврата в Шаг 6 из справки
@router.callback_query(F.data == "flyer_back_step_6_internal")
async def back_to_step_6_internal(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_6(callback, state)

# Вспомогательный хендлер для возврата в Шаг 5 (из кнопки Назад)
@router.callback_query(F.data == "flyer_back_step_5")
async def back_to_step_5_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_5_color(callback.message, state)

# =======================================================
# 7️⃣ БЛОК 7: ТИРАЖ
# =======================================================

@router.callback_query(CalcFlyers.step_processing, F.data.startswith("flyer_proc_"))
async def step_6_toggle_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    proc_val = callback.data.replace("flyer_proc_", "")
    
    # 1. Если выбрали "Без обработки" — сбрасываем список и идем к тиражу
    if proc_val == "Нет":
        await state.update_data(processing="Нет", processing_list=[])
        await render_step_7(callback.message, state)
        return
        
    # 2. Если нажали "Продолжить" (после выбора нескольких опций)
    if proc_val == "done":
        data = await state.get_data()
        selected = data.get('processing_list', [])
        if not selected:
             await state.update_data(processing="Нет")
        else:
             await state.update_data(processing=", ".join(selected))
        await render_step_7(callback.message, state)
        return

    # 3. Переключение опций (Перфорация / Фальц)
    data = await state.get_data()
    selected = data.get('processing_list', [])
    if not isinstance(selected, list): selected = []
    
    if proc_val in selected:
        selected.remove(proc_val)
    else:
        selected.append(proc_val)
        
    # Обновляем строковое представление для "хлебных крошек"
    proc_str = ", ".join(selected) if selected else "Не выбрано"
    
    await state.update_data(processing_list=selected, processing=proc_str)
    await render_step_6(callback, state)

async def render_step_7(message: types.Message, state: FSMContext):
    await state.set_state(CalcFlyers.step_circulation)
    data = await state.get_data()
    
    text = (
        f"{get_breadcrumbs(data, 7)}"
        "🔹 <b>Шаг 7. Тираж</b>\n"
        "Выберите количество из списка или напишите число вручную в чат.\n"
        "<i>(Например: 350)</i>"
    )
    
    # Формируем кнопки в зависимости от типа печати (Цифра или Офсет)
    buttons = []
    
    if data.get('print_code') == 'digital':
        # Для цифры - малые тиражи
        buttons.append([
            InlineKeyboardButton(text="50", callback_data="flyer_cnt_50"),
            InlineKeyboardButton(text="100", callback_data="flyer_cnt_100"),
            InlineKeyboardButton(text="200", callback_data="flyer_cnt_200")
        ])
        buttons.append([
            InlineKeyboardButton(text="300", callback_data="flyer_cnt_300"),
            InlineKeyboardButton(text="500", callback_data="flyer_cnt_500")
        ])
    else:
        # Для офсета - большие тиражи
        buttons.append([
            InlineKeyboardButton(text="1 000", callback_data="flyer_cnt_1000"),
            InlineKeyboardButton(text="2 000", callback_data="flyer_cnt_2000")
        ])
        buttons.append([
            InlineKeyboardButton(text="5 000", callback_data="flyer_cnt_5000"),
            InlineKeyboardButton(text="10 000", callback_data="flyer_cnt_10000")
        ])

    # Навигация
    buttons.append([
        InlineKeyboardButton(text="💡 Справка", callback_data="flyer_info_circ"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="flyer_back_step_6")
    ])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Отправляем (учитывая, что message может быть как CallbackQuery, так и Message)
    if isinstance(message, types.CallbackQuery):
        await smart_edit(message.message, text, kb)
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


# --- СПРАВКА ПО ТИРАЖУ ---
@router.callback_query(F.data == "flyer_info_circ")
async def info_circulation_handler(callback: types.CallbackQuery):
    await callback.answer()
    
    text = (
        "📌 <b>Как определить нужный тираж?</b>\n"
        "Перед выбором количества ответьте себе на несколько вопросов:\n\n"
        "📍 <b>Где будет распространяться флаер?</b>\n"
        "• Раздача у метро или ТЦ → потребуется больший тираж\n"
        "• Рассылка постоянным клиентам → тираж можно рассчитать точнее\n\n"
        "📅 <b>На какой период рассчитана реклама?</b>\n"
        "• Краткосрочная акция → достаточно ограниченного тиража\n"
        "• Долгосрочное предложение → лучше закладывать запас\n\n"
        "🎯 <b>Это тест или полноценная кампания?</b>\n"
        "• Тестирование спроса → разумно начать с небольшого количества\n"
        "• Масштабное продвижение → нужен полноценный тираж\n\n"
        "<b>Важно учитывать:</b>\n"
        "🔹 <b>При цифровой печати</b> минимальный тираж — 50 экземпляров.\n"
        "<i>Технология рассчитана на небольшие и средние объемы, поэтому заказы принимаются от установленного минимума.</i>\n\n"
        "🔹 <b>При офсетной печати</b> чаще выбирают крупные тиражи для массового распространения.\n"
        "<i>Этот способ особенно удобен, если планируется широкая рекламная кампания или регулярная раздача флаеров.</i>\n\n"
        "🎁 <b>Дополнительно:</b>\n"
        "Для офсетной печати у нас действуют аукционные скидки на тиражи.\n"
        "<i>Подробные условия и актуальные предложения можно посмотреть в разделе «Акции и скидки» в главном меню.</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="flyer_back_step_7_internal")]
    ])
    
    await smart_edit(callback.message, text, kb)


# --- ОБРАБОТЧИКИ НАВИГАЦИИ ---

# 1. Если выбрали тираж КНОПКОЙ
@router.callback_query(CalcFlyers.step_circulation, F.data.startswith("flyer_cnt_"))
async def step_7_circulation_click(callback: types.CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    await callback.answer()
    count = callback.data.split("_")[2]
    await state.update_data(count=count)
    await step_final_summary(callback.message, state, db, bot)

# 2. Если ввели тираж ВРУЧНУЮ (текстом)
@router.message(CalcFlyers.step_circulation)
async def process_circulation_input(message: types.Message, state: FSMContext, db: Database, bot: Bot):
    # Пытаемся удалить сообщение пользователя для чистоты чата
    try: await message.delete()
    except: pass

    if not message.text.isdigit():
        # Временное сообщение об ошибке
        await message.answer("⚠️ <b>Ошибка!</b> Введите только число (например: 1000).")
        return

    count = int(message.text)
    if count < 1:
        await message.answer("⚠️ Тираж должен быть больше 0.")
        return

    await state.update_data(count=str(count))
    await step_final_summary(message, state, db, bot)

# Возврат из справки
@router.callback_query(F.data == "flyer_back_step_7_internal")
async def back_to_step_7_internal(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_7(callback, state)

# Возврат в Шаг 6 (Кнопка Назад)
@router.callback_query(F.data == "flyer_back_step_6")
async def back_to_step_6(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_6(callback, state)

# =======================================================
# 8️⃣ БЛОК 8: ИТОГ И ОТПРАВКА ЗАКАЗА
# =======================================================

async def step_final_summary(message: types.Message, state: FSMContext, db: Database, bot: Bot):
    data = await state.get_data()
    
    summary_text = (
        f"🧾 <b>ПРОВЕРКА ДАННЫХ: ФЛАЕРЫ</b>\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"🖨 Печать: <b>{data.get('print_type', 'Не указан')}</b>\n"
        f"📏 Формат: <b>{data.get('format', 'Не указан')}</b>\n"
        f"📄 Бумага: <b>{data.get('p_type', 'Не указана')}</b>\n"
        f"⚖️ Плотность: <b>{data.get('paper', 'Не указана')}</b>\n"
        f"🎨 Цвет: <b>{data.get('color', 'Не указан')}</b>\n"
        f"⚙️ Обработка: <b>{data.get('processing', 'Не указана')}</b>\n"
        f"🔢 Тираж: <b>{data.get('count', '0')} шт.</b>"
    )
    
    await state.update_data(final_summary=summary_text)
    
    # --- ЕДИНАЯ ПРОВЕРКА ПРОФИЛЯ ---
    user_id = message.chat.id
    profile = await db.get_user(user_id)
    
    # Проверяем наличие всех ключевых полей
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
            "🚀 <b>Что произойдет дальше?</b>\n"
            "После нажатия кнопки «Отправить», ваши параметры попадут к менеджеру. "
            "Он рассчитает стоимость и свяжется с вами для подтверждения."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 ОТПРАВИТЬ МЕНЕДЖЕРУ", callback_data="flyer_submit")],
            [InlineKeyboardButton(text="🔄 Изменить параметры", callback_data="calc_flyers_start")]
        ])
    else:
        text = (
            "🏁 <b>Ваш заказ сформирован!</b>\n\n"
            f"{summary_text}\n\n"
            "➖➖➖➖➖➖➖➖\n"
            "👋 <b>Давайте знакомиться!</b>\n"
            "Чтобы менеджер мог связаться с вами, нужно заполнить контактные данные.\n"
            "<i>Это нужно сделать всего один раз, данные сохранятся для будущих заказов.</i>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 ПРЕДСТАВИТЬСЯ И ОТПРАВИТЬ", callback_data="flyer_reg_start")],
            [InlineKeyboardButton(text="🔄 Начать сначала", callback_data="calc_flyers_start")]
        ])
    
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# =======================================================
# 9️⃣ БЛОК 9: РЕГИСТРАЦИЯ И ЗАПИСЬ В БАЗУ
# =======================================================

@router.callback_query(F.data == "flyer_submit")
async def submit_order_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    await callback.answer()
    await finalize_order(callback.message.chat, state, bot, callback.message, db)

@router.callback_query(F.data == "flyer_reg_start")
async def reg_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CalcFlyers.reg_name)
    await callback.message.answer("✍️ Введите ваше <b>Имя</b>:", parse_mode="HTML")

@router.message(CalcFlyers.reg_name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(reg_name=message.text)
    await state.set_state(CalcFlyers.reg_phone)
    await message.answer("📞 Введите ваш <b>Телефон</b>:", parse_mode="HTML")

@router.message(CalcFlyers.reg_phone)
async def reg_phone(message: types.Message, state: FSMContext):
    await state.update_data(reg_phone=message.text)
    await state.set_state(CalcFlyers.reg_city)
    await message.answer("🏙 Введите ваш <b>Город</b>:", parse_mode="HTML")

@router.message(CalcFlyers.reg_city)
async def reg_city(message: types.Message, state: FSMContext):
    await state.update_data(reg_city=message.text)
    await state.set_state(CalcFlyers.reg_address)
    await message.answer("🚚 Введите <b>Адрес доставки</b>:", parse_mode="HTML")

@router.message(CalcFlyers.reg_address)
async def reg_address(message: types.Message, state: FSMContext, bot: Bot, db: Database):
    data = await state.get_data()
    
    # --- ЗАПИСЬ В БАЗУ ---
    await db.update_user_profile(
        message.chat.id, 
        full_name=data['reg_name'], 
        phone=data['reg_phone'], 
        city=data['reg_city'], 
        address=message.text
    )
        
    await message.answer("✅ Контакты сохранены! Отправляем заказ...")
    await finalize_order(message.chat, state, bot, message, db)

async def finalize_order(user_obj, state: FSMContext, bot: Bot, message_obj, db: Database):
    data = await state.get_data()
    
    params = {
        "print_type": data.get('print_type'),
        "format": data.get('format'),
        "paper_type": data.get('p_type'),
        "paper_weight": data.get('paper'),
        "color": data.get('color'),
        "processing": data.get('processing'),
        "count": data.get('count')
    }
    
    order = Order(
        user_id=user_obj.id,
        category="Флаеры",
        params=params,
        description=data.get('final_summary')
    )
    
    # Сохраняем заказ
    order_id = await db.create_order(order)
    
    # Уведомление админам/менеджерам
    admin_ids = [x.strip() for x in os.getenv("ADMIN_ID", "").split(",") if x.strip()]
    manager_ids = await db.get_managers()
    
    all_notif_ids = list(set(admin_ids + [str(mid) for mid in manager_ids]))
    
    # Получаем актуальное имя из базы
    db_user = await db.get_user(user_obj.id)
    client_name = db_user.full_name if db_user and db_user.full_name else (user_obj.first_name if hasattr(user_obj, 'first_name') else "Клиент")
    client_phone = db_user.phone if db_user and db_user.phone else "-"
    
    # Получаем username, если он есть
    username_str = f"(@{user_obj.username})" if hasattr(user_obj, 'username') and user_obj.username else ""

    admin_text = (
        f"⚡️ <b>НОВЫЙ ЗАКАЗ #{order_id} (Флаеры)</b>\n"
        f"👤 {client_name} {username_str}\n"
        f"📞 {client_phone}\n\n"
        f"{data.get('final_summary', '')}"
    )
    
    for adm in all_notif_ids:
        try: await bot.send_message(chat_id=adm, text=admin_text, parse_mode="HTML")
        except: pass

    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]])
    await message_obj.answer(f"✅ <b>Заказ #{order_id} отправлен!</b>\nМенеджер свяжется с вами.", reply_markup=kb, parse_mode="HTML")
