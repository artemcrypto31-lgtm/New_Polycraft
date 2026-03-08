# === START handlers/calc_vizitki.py ===
from aiogram import Router, F, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
import mock_db 

router = Router()


# === МАШИНА СОСТОЯНИЙ ===
class CalcVizitki(StatesGroup):
    step_format = State()
    step_circulation = State()
    step_sets = State()
    step_paper = State()
    step_color = State()
    step_lamination = State()
    step_lamination_sides = State()
    step_rounding = State()
    
# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def get_breadcrumbs(data: dict, current_step: int) -> str:
    lines = []
    if current_step > 1: lines.append(f"📏 Формат: <b>{data.get('format', '???')}</b>")
    if current_step > 2: lines.append(f"🔢 Тираж: <b>{data.get('count', '???')} шт.</b>")
    if current_step > 3: lines.append(f"👥 Видов: <b>{data.get('sets', '1')}</b>")
    if current_step > 4: lines.append(f"📄 Бумага: <b>{data.get('paper', '???')}</b>")
    if current_step > 5: lines.append(f"🎨 Печать: <b>{data.get('color', '???')}</b>")
    if current_step > 6: lines.append(f"🛡 Ламинация: <b>{data.get('lamination', 'Нет')}</b>")
    
    if not lines: return ""
    return "⚙️ <b>Ваш выбор:</b>\n" + "\n".join(lines) + "\n➖➖➖➖➖➖➖➖\n"

async def smart_edit(message: types.Message, text: str, kb: InlineKeyboardMarkup, photo_id: str = None):
    """Обновляет сообщение: поддерживает смену фото на текст и обратно в тихом режиме."""
    try:
        # Если нужно показать фото
        if photo_id and photo_id.strip():
            if message.photo:
                # Если фото уже есть, плавно меняем медиа и текст
                media = InputMediaPhoto(media=photo_id, caption=text, parse_mode="HTML")
                await message.edit_media(media=media, reply_markup=kb)
            else:
                # Если был текст, удаляем его и шлем новое фото (без звука)
                await message.delete()
                await message.answer_photo(
                    photo=photo_id, 
                    caption=text, 
                    reply_markup=kb, 
                    parse_mode="HTML",
                    disable_notification=True
                )
        # Если фото НЕ нужно (чистый текст)
        else:
            if message.photo:
                
                await message.delete()
                await message.answer(
                    text=text, 
                    reply_markup=kb, 
                    parse_mode="HTML",
                    disable_notification=True
                )
            else:
                # Обычное редактирование текста
                await message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        # Резервный вариант на случай ошибок API
        await message.answer(
            text=text, 
            reply_markup=kb, 
            parse_mode="HTML", 
            disable_notification=True
        )
        
# ==========================================
# 1. ФОРМАТ (СТАРТ)
# ==========================================
@router.callback_query(F.data.in_({"calc_vizitki_start", "menu_calc"}))
async def step_1_format(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.data != "calc_vizitki_start":
        await state.clear()
        await state.update_data(lamination="Нет", rounding="Прямые")

    await state.set_state(CalcVizitki.step_format)
    text = (
        "📐 <b>Шаг 1. Формат</b>\n\n"
        "<b>Стандарт (90х50)</b> или <b>Евро (85х55)</b>?\n"
        "Это база, под которую подстраивается дизайн.\n\n"
        "👇 <i>Сомневаетесь в разнице? Кнопка «Справка/Пример» покажет наглядное сравнение.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Стандарт (90х50)", callback_data="set_fmt_90x50"),
         InlineKeyboardButton(text="🇪🇺 Евро (85х55)", callback_data="set_fmt_85x55")],
        [InlineKeyboardButton(text="💡 Справка", callback_data="info_format")],
        [InlineKeyboardButton(text="🔙 Назад в каталог", callback_data="menu_catalog")]
    ])
    # Вызываем без photo_id, чтобы гарантированно убрать картинку при возврате из справки
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "info_format")
async def info_format(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "📐 <b>90x50 или 85x55? Размер имеет значение</b>\n"
        "<i>(особенно для кошелька)</i>\n\n"
        "Выбор формата визитки — это не просто дело вкуса, а вопрос удобства вашего клиента. В СНГ идет борьба двух стандартов. Какой выбрать?\n\n"
        "<b>1️⃣ Стандарт РФ/СНГ (90х50 мм)</b>\n"
        "Это наша классика.\n"
        "✅ <b>Плюсы:</b>\n"
        "— <b>Вмещает всё:</b> Ширина 90 мм спасает, если у вас длинная должность — текст не придется мельчить.\n"
        "— <b>Привычность:</b> Идеально входит в стандартные настольные визитницы.\n"
        "— <b>Цена:</b> Часто чуть дешевле в производстве.\n"
        "❌ <b>Главный минус:</b> Она не влезает в отделения для карт современных кошельков. Визитку либо мнут, либо подрезают, либо выбрасывают.\n"
        "👤 <b>Кому подходит:</b> Госсектор, промышленность, медицина, локальный бизнес.\n\n"
        "<b>2️⃣ Евроформат (85х55 мм)</b>\n"
        "Мировой стандарт (размер кредитки).\n"
        "✅ <b>Плюсы:</b>\n"
        "— <b>Эргономика:</b> Идеально ложится в любой кошелек или слот для карт.\n"
        "— <b>Имидж:</b> Выглядит по-европейски, компактно («золотое сечение»).\n"
        "— <b>Воздух:</b> Больше места для креатива сверху и снизу.\n"
        "❌ <b>Минусы:</b> Меньше места по ширине — длинные слова придется переносить.\n"
        "👤 <b>Кому подходит:</b> IT-сфера, дизайн, стартапы, экспорт.\n\n"
        "🎯 <b>Итог:</b>\n"
        "Если клиенты с визитницами на столах 👉 <b>90х50</b>.\n"
        "Если клиенты с картхолдерами и смартфонами 👉 <b>85х55</b>."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="calc_vizitki_start")]])
    await smart_edit(callback.message, text, kb, PHOTO_FORMAT)

# ==========================================
# 2. ТИРАЖ
# ==========================================
@router.callback_query(CalcVizitki.step_format, F.data.startswith("set_fmt_"))
async def step_2_circulation(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    choice = "90x50 мм" if "90x50" in callback.data else "85x55 мм"
    await state.update_data(format=choice)
    await render_step_2(callback, state)

async def render_step_2(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CalcVizitki.step_circulation)
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 2)}"
        f"📦 <b>Шаг 2. Тираж (Количество штук)</b>\n\n"
        f"Какой тираж печатаем?\n"
        f"Выберите количество визиток для <b>одного макета</b> (на одного человека).\n\n"
        f"ℹ️ <i>Подробнее о выгоде тиражей — в разделе «Справка/Пример».</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="100 шт.", callback_data="set_cnt_100"),
         InlineKeyboardButton(text="200 шт.", callback_data="set_cnt_200"),
         InlineKeyboardButton(text="300 шт.", callback_data="set_cnt_300")],
        [InlineKeyboardButton(text="500 шт.", callback_data="set_cnt_500"),
         InlineKeyboardButton(text="1000 шт.", callback_data="set_cnt_1000")],
        [InlineKeyboardButton(text="💡 Справка", callback_data="info_circulation")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="calc_vizitki_start")]
    ])
    await smart_edit(callback.message, text, kb)

@router.callback_query(F.data == "info_circulation")
async def info_circulation(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    text = (
        "📉 <b>Математика выгоды: Почему больше = дешевле?</b>\n\n"
        "В полиграфии работает железное правило:\n"
        "<b>Чем выше тираж — тем ниже цена за одну визитку.</b>\n\n"
        "⚙️ <b>Как это работает?</b>\n"
        "Основные расходы типографии — это настройка оборудования и запуск машины (приладка). Эти затраты <b>одинаковы</b> и для 100, и для 1000 визиток.\n\n"
        "💸 <b>Почувствуйте разницу:</b>\n"
        "• Заказать <b>10 раз по 100 шт</b> — вы 10 раз оплатите «запуск» машины. Это дорого.\n"
        "• Заказать <b>1 раз 1000 шт</b> — вы платите за запуск всего один раз. Это выгодно.\n\n"
        "💡 <b>Совет профи:</b>\n"
        "Визитки не портятся и не имеют срока годности. Заказать 1000 штук за раз всегда разумнее, чем бегать в типографию каждые два месяца."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="back_to_step_2_internal")]])
    await smart_edit(callback.message, text, kb, PHOTO_CIRCULATION)

@router.callback_query(F.data == "back_to_step_2_internal")
async def back_to_step_2(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_2(callback, state)


# ==========================================
# 3. КОМПЛЕКТЫ (ВИДЫ)
# ==========================================
@router.callback_query(CalcVizitki.step_circulation, F.data.startswith("set_cnt_"))
async def step_3_sets(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(count=callback.data.split("_")[2])
    await render_step_3_msg(callback.message, state)

async def render_step_3_msg(message: types.Message, state: FSMContext):
    await state.set_state(CalcVizitki.step_sets)
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 3)}"
        f"👥 <b>Шаг 3. Комплекты</b>\n\n"
        f"Сколько видов макетов?\n"
        f"Если визитки нужны нескольким сотрудникам (или у вас разные дизайны), укажите количество комплектов.\n\n"
        f"<b>Как выбрать:</b>\n"
        f"1️⃣ Нажмите кнопку с цифрой ниже.\n"
        f"2️⃣ Или <b>напишите число вручную</b> в чат (например: 6) и отправьте."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 1 вид", callback_data="set_sets_1"),
         InlineKeyboardButton(text="👥 2 вида", callback_data="set_sets_2"),
         InlineKeyboardButton(text="👥 3 вида", callback_data="set_sets_3")],
        [InlineKeyboardButton(text="👥 4 вида", callback_data="set_sets_4"),
         InlineKeyboardButton(text="👥 5 видов", callback_data="set_sets_5")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_step_2")]
    ])
    
    if message.from_user.is_bot:
        await smart_edit(message, text, kb)
        msg_id = message.message_id
    else:
        msg = await message.answer(text, reply_markup=kb, parse_mode="HTML", disable_notification=True)
        msg_id = msg.message_id
    
    await state.update_data(calc_msg_id=msg_id)

@router.message(CalcVizitki.step_sets)
async def step_3_sets_manual(message: types.Message, state: FSMContext, bot: Bot):
    try: await message.delete()
    except: pass

    if not message.text.isdigit():
        await message.answer("⚠️ <b>Пожалуйста, введите только число.</b>", parse_mode="HTML", disable_notification=True)
        return
        
    await state.update_data(sets=message.text)
    data = await state.get_data()
    await render_step_4_msg(message, state, bot=bot, edit_id=data.get('calc_msg_id'))
        
    sets_count = int(message.text)
    if sets_count < 1:
        await message.answer("⚠️ Количество видов должно быть больше 0.")
        return
        
    await state.update_data(sets=str(sets_count))
    data = await state.get_data()
    last_msg_id = data.get('calc_msg_id')
    await render_step_4_msg(message, state, bot=bot, edit_id=last_msg_id)

@router.callback_query(CalcVizitki.step_sets, F.data.startswith("set_sets_"))
async def step_3_sets_btn(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    sets = callback.data.split("_")[2]
    await state.update_data(sets=sets)
    await render_step_4_msg(callback.message, state)

@router.callback_query(F.data == "back_to_step_2")
async def back_to_step_2_btn(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CalcVizitki.step_circulation)
    await render_step_2(callback, state)

@router.callback_query(F.data == "back_to_step_3_internal")
async def back_to_step_3(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_3_msg(callback.message, state)


# ==========================================
# 4. БУМАГА
# ==========================================
async def render_step_4_msg(message: types.Message, state: FSMContext, bot: Bot = None, edit_id: int = None):
    await state.set_state(CalcVizitki.step_paper)
    data = await state.get_data()
    text = (
        f"{get_breadcrumbs(data, 4)}"
        f"📄 <b>Шаг 4. Бумага</b>\n\n"
        f"Самое приятное — тактильные ощущения.\n"
        f"Обычная мелованная или изысканный лён? От выбора бумаги зависит восприятие вашего бренда.\n\n"
        f"💡 <i>В «Справке» мы подробно расписали плюсы и минусы каждого материала.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Глянцевая", callback_data="set_pap_MelGloss"),
         InlineKeyboardButton(text="☁️ Матовая", callback_data="set_pap_MelMat")],
        [InlineKeyboardButton(text="🎨 Дизайнерская", callback_data="set_pap_Design"),
         InlineKeyboardButton(text="🧵 Лён", callback_data="set_pap_Len")],
        [InlineKeyboardButton(text="💡 Справка", callback_data="info_paper")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_step_3_internal")]
    ])
    
    if edit_id and bot:
        try:
            await bot.edit_message_text(chat_id=message.chat.id, message_id=edit_id, text=text, reply_markup=kb, parse_mode="HTML")
            return 
        except: pass 

    await smart_edit(message, text, kb)

@router.callback_query(CalcVizitki.step_paper, F.data.startswith("set_pap_"))
async def step_4_paper(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    mapping = {"MelGloss": "Глянец 350г", "MelMat": "Мат 350г", "Design": "Дизайн", "Len": "Лен"}
    code = callback.data.split("_")[2]
    await state.update_data(paper=mapping.get(code, code))
    await render_step_5(callback, state)

@router.callback_query(F.data == "info_paper")
async def info_paper(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "📄 <b>На какой бумаге печатать: Мат, Глянец, Дизайн или Лён?</b>\n\n"
        "Визитка — это первый тактильный контакт с брендом. Выбор бумаги напрямую влияет на доверие и на то, выбросят визитку или сохранят.\n\n"
        "☁️ <b>Матовая (350 г/м²) — Рабочая лошадка</b>\n"
        "Универсальный, безопасный вариант. Не бликует, выглядит сдержанно и аккуратно.\n"
        "👤 <i>Кому:</i> B2B, услуги, производство, консалтинг.\n"
        "❌ <i>Нюанс:</i> Не маскирует ошибки слабого дизайна.\n\n"
        "✨ <b>Глянцевая (350 г/м²) — Визуальный удар</b>\n"
        "Про цвет и контраст. Усиливает фото и логотипы.\n"
        "👤 <i>Кому:</i> Реклама, ивенты, яркий визуал.\n"
        "❌ <i>Нюанс:</i> Собирает отпечатки пальцев. В строгом бизнесе может выглядеть как «показуха».\n\n"
        "🎨 <b>Дизайнерская — Когда визитка становится объектом</b>\n"
        "Это про характер, текстуру и эмоции. Такую визитку хочется трогать.\n"
        "👤 <i>Кому:</i> Личный бренд, премиум, креативные студии.\n"
        "❌ <i>Нюанс:</i> Требует профессионального минималистичного макета.\n\n"
        "🧵 <b>Лён — Спокойный статус</b>\n"
        "Текстурная классика. Ассоциируется со стабильностью и опытом.\n"
        "👤 <i>Кому:</i> Юристы, врачи, архитекторы, руководители.\n"
        "❌ <i>Нюанс:</i> Не любит сложные цветные заливки.\n\n"
        "⚠️ <b>Главная ошибка</b> — выбирать бумагу «потому что красивее». Бумага должна решать задачу бизнеса!\n\n"
        "🎯 <b>Итог без иллюзий:</b>\n"
        "• <b>Мат</b> — для стабильности.\n"
        "• <b>Глянец</b> — для визуального эффекта.\n"
        "• <b>Дизайнерская</b> — для выделения.\n"
        "• <b>Лён</b> — для статуса и доверия."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="back_to_step_4_internal")]])
    await smart_edit(callback.message, text, kb, PHOTO_PAPER)
    
@router.callback_query(F.data == "back_to_step_4_internal")
async def back_to_step_4(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_4_msg(callback.message, state)


# ==========================================
# 5. ЦВЕТНОСТЬ
# ==========================================
async def render_step_5(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CalcVizitki.step_color)
    data = await state.get_data()
    
    text = (
        f"{get_breadcrumbs(data, 5)}"
        f"🎨 <b>Шаг 5. Запечатка (Цветность)</b>\n\n"
        f"Следующий штрих.\n"
        f"Используем обе стороны визитки или оставим оборот чистым?\n\n"
        f"👉 <i>Загляните в «Справку», чтобы узнать, какой вариант практичнее.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Односторонняя", callback_data="set_col_4+0"),
         InlineKeyboardButton(text="2️⃣ Двухсторонняя", callback_data="set_col_4+4")],
        [InlineKeyboardButton(text="💡 Справка", callback_data="info_color")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_step_4_internal")]
    ])
    await smart_edit(callback.message, text, kb)

@router.callback_query(CalcVizitki.step_color, F.data.startswith("set_col_"))
async def step_5_color(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    color = "4+0" if "4+0" in callback.data else "4+4"
    await state.update_data(color=color)
    await render_step_6_type(callback, state)

@router.callback_query(F.data == "info_color")
async def info_color(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "🎨 <b>4+0 или 4+4: Одна сторона или обе?</b>\n\n"
        "Выбор влияет на то, останется визитка у клиента или полетит в корзину.\n\n"
        "1️⃣ <b>4+0 (Одна сторона) — Минимализм и фокус</b>\n"
        "Лаконичный вариант. Человек бросил взгляд и сразу понял, кто вы.\n"
        "✅ <i>Идеально для:</i> Массовой раздачи, выставок, холодных контактов.\n"
        "⚠️ <i>Риск:</i> Если информации много, дизайн начнет «задыхаться». Мелкий шрифт и теснота убивают вид.\n\n"
        "2️⃣ <b>4+4 (Две стороны) — Логика и статус</b>\n"
        "Вторая сторона нужна не для красоты, а для структуры. Лицо — бренд, оборот — детали (QR, услуги).\n"
        "✅ <i>Плюс:</i> Воспринимается подсознательно как более «дорогая» и продуманная вещь.\n"
        "🧠 <i>Психология:</i> Вы платите не за лишнюю краску, а за эффективность.\n\n"
        "🚫 <b>Главная ошибка</b>\n"
        "Выбрать одну сторону «ради экономии» и попытаться впихнуть туда всё подряд. В итоге теряется и читабельность, и эстетика.\n\n"
        "🎯 <b>Честный вывод:</b>\n"
        "• <b>4+0</b> — Про простоту и массовость.\n"
        "• <b>4+4</b> — Про удобство и впечатление.\n"
        "<i>Если визитка — часть имиджа, вторая сторона почти всегда себя оправдывает.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="back_to_step_5_internal")]])
    await smart_edit(callback.message, text, kb, PHOTO_COLOR)

@router.callback_query(F.data == "back_to_step_5_internal")
async def back_to_step_5(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_5(callback, state)


# ==========================================
# 6. ЛАМИНАЦИЯ
# ==========================================
async def render_step_6_type(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CalcVizitki.step_lamination)
    data = await state.get_data()
    
    text = (
        f"{get_breadcrumbs(data, 6)}"
        f"🛡 <b>Шаг 6: Ламинация (Тип)</b>\n\n"
        f"Какую пленку будем использовать?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Нет", callback_data="set_lam_Нет"),
         InlineKeyboardButton(text="✨ Глянец", callback_data="set_lam_type_Глянец")],
        [InlineKeyboardButton(text="☁️ Мат", callback_data="set_lam_type_Мат"),
         InlineKeyboardButton(text="🍑 Софт-Тач", callback_data="set_lam_type_Софт")],
        [InlineKeyboardButton(text="💡 Справка", callback_data="info_lam")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_step_5_internal")]
    ])
    await smart_edit(callback.message, text, kb)

@router.callback_query(CalcVizitki.step_lamination)
async def process_lam_type(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    code = callback.data
    
    if code == "set_lam_Нет":
        await state.update_data(lamination="Нет")
        # ПРОПУСКАЕМ ТИСНЕНИЕ: СРАЗУ НА УГЛЫ (ШАГ 8 -> 7)
        await render_step_8(callback, state)
    elif code.startswith("set_lam_type_"):
        lam_type = code.split("_")[3]
        await state.update_data(temp_lam_type=lam_type)
        await render_step_6_sides(callback, state, lam_type)
    elif code == "info_lam":
        await info_lam(callback)
    elif code == "back_to_step_5_internal":
        await back_to_step_5(callback, state)
    elif code == "back_to_lam_type":
        await render_step_6_type(callback, state)

async def render_step_6_sides(callback: types.CallbackQuery, state: FSMContext, lam_type: str):
    await state.set_state(CalcVizitki.step_lamination_sides)
    data = await state.get_data()
    
    text = (
        f"{get_breadcrumbs(data, 6)}"
        f"🛡 <b>Шаг 6: Ламинация ({lam_type})</b>\n\n"
        f"<b>1️⃣ С одной стороны</b>\n"
        f"Защищает лицевую часть и сохраняет аккуратный внешний вид. Оптимальный вариант, если важен баланс между практичностью и стоимостью.\n\n"
        f"<b>2️⃣ С двух сторон</b>\n"
        f"Максимальная защита и завершённый внешний вид. Визитка дольше сохраняет форму, приятна в руках и выглядит более презентабельно.\n\n"
        f"👇 <i>С какой стороны ламинируем?</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ С одной (1 ст)", callback_data="set_lam_side_1ст"),
         InlineKeyboardButton(text="2️⃣ С обеих (2 ст)", callback_data="set_lam_side_2ст")],
        [InlineKeyboardButton(text="🔙 Назад (Выбрать тип)", callback_data="back_to_lam_type")]
    ])
    await smart_edit(callback.message, text, kb)

@router.callback_query(CalcVizitki.step_lamination_sides, F.data.startswith("set_lam_side_"))
async def process_lam_side(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    side = callback.data.split("_")[3]
    data = await state.get_data()
    
    full_lam_name = f"{data['temp_lam_type']} ({side})"
    await state.update_data(lamination=full_lam_name)
    # ПРОПУСКАЕМ ТИСНЕНИЕ: СРАЗУ НА УГЛЫ (ШАГ 8 -> 7)
    await render_step_8(callback, state)

@router.callback_query(F.data == "back_to_lam_type")
async def back_to_lam_type(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_6_type(callback, state)

@router.callback_query(F.data == "info_lam")
async def info_lam(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "🛡 <b>Ламинация: Глянец, Мат или Софт-тач?</b>\n\n"
        "Это не просто защита от износа, а способ управления впечатлением. Выбор «на глаз» часто ведет к разочарованию.\n\n"
        "✨ <b>Глянцевая — Визуальный удар</b>\n"
        "Делает цвета сочнее, а черный — глубже. Самый «эффектный» вариант.\n"
        "✅ <i>Для чего:</i> Реклама, фото, яркие иллюстрации.\n"
        "⚠️ <i>Минус:</i> Бликует и собирает отпечатки пальцев. Мелкий текст читать сложнее.\n\n"
        "☁ <b>Матовая — Контроль и сдержанность</b>\n"
        "Убирает блики, выглядит спокойно и «дорого». Текст читается идеально.\n"
        "✅ <i>Для чего:</i> Деловой стиль, корпоративный сектор, плотный текст.\n"
        "⚠️ <i>Минус:</i> Чуть приглушает яркость цветов.\n\n"
        "🍑 <b>Софт-тач — Тактильная эмоция</b>\n"
        "Бархатистая, мягкая поверхность (как лепесток розы). Вау-эффект через прикосновение.\n"
        "✅ <i>Для чего:</i> Премиум-сегмент, личный бренд, минимализм.\n"
        "⚠️ <i>Минус:</i> Требует бережного обращения, не массовый вариант.\n\n"
        "🎯 <b>Короткий честный вывод:</b>\n"
        "• <b>Глянец</b> — для визуального эффекта.\n"
        "• <b>Мат</b> — для универсальности и статуса.\n"
        "• <b>Софт-тач</b> — для запоминаемости на ощупь.\n"
        "<i>Ламинация должна усиливать визитку, а не спорить с её задачей.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="back_to_lam_type")]])
    await smart_edit(callback.message, text, kb, PHOTO_LAM)


# ==========================================
# 7. УГЛЫ И ФИНАЛ (БЫВШИЙ ШАГ 8)
# ==========================================
async def render_step_8(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CalcVizitki.step_rounding)
    data = await state.get_data()
    
    # Изменили номер шага с 8 на 7
    text = (
        f"{get_breadcrumbs(data, 7)}"
        f"📐 <b>Шаг 7: Углы</b>\n\n"
        f"Последний штрих."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📐 Прямые", callback_data="set_rnd_Прямые"),
         InlineKeyboardButton(text="🔄 Скругленные", callback_data="set_rnd_Скругленные")],
        [InlineKeyboardButton(text="💡 Справка", callback_data="info_rnd")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_lam_type")]
    ])
    await smart_edit(callback.message, text, kb)

@router.callback_query(CalcVizitki.step_rounding, F.data.startswith("set_rnd_"))
async def finish_vizitki(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    rnd = callback.data.split("_")[2]
    await state.update_data(rounding=rnd)
    
    data = await state.get_data()
    
    # Убрали строку про Тиснение из финала
    summary = (
        f"💳 <b>ЗАКАЗ: ВИЗИТКИ</b>\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"📏 Формат: <b>{data['format']}</b>\n"
        f"🔢 Тираж: <b>{data['count']} шт.</b>\n"
        f"👥 Видов: <b>{data['sets']}</b>\n"
        f"📄 Бумага: <b>{data['paper']}</b>\n"
        f"🎨 Цвет: <b>{data['color']}</b>\n"
        f"🛡 Лам: <b>{data['lamination']}</b>\n"
        f"📐 Углы: <b>{data['rounding']}</b>"
    )
    await state.update_data(final_summary=summary)

    # === ЛОГИКА ПРОВЕРКИ ПРОФИЛЯ ===
    # === ИСПРАВЛЕНИЕ: Используем mock_db вместо database и chat.id вместо user.id
    user_id = callback.message.chat.id
    profile = mock_db.get_user(user_id)
    
    # Считаем скидку для отображения (если есть)
    user_discount = 0
    if hasattr(mock_db, 'get_user_discount'):
        user_discount = mock_db.get_user_discount(user_id, 'Визитки')
    
    discount_note = f"\n🎁 Ваша скидка: <b>{user_discount}%</b>" if user_discount > 0 else ""

    # Проверяем, заполнил ли пользователь базу (имя и телефон — это минимум)
    if not profile or not profile.get('phone') or profile.get('phone') == '-':
        await state.update_data(order_category="визитки", final_summary=summary)
        btn_text = "📝 ЗАПОЛНИТЬ ДАННЫЕ И ОТПРАВИТЬ"
        callback_data = "user_cabinet" # Отправляем в кабинет, если данных нет
        alert_text = "⚠️ <b>Почти готово!</b>\nЧтобы отправить заказ, нужно заполнить профиль в личном кабинете."
    else:
        btn_text = "✅ ОТПРАВИТЬ МЕНЕДЖЕРУ"
        callback_data = "vizitki_submit"
        alert_text = f"🎉 <b>Проверьте данные заказа:</b>{discount_note}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, callback_data=callback_data)],
        [InlineKeyboardButton(text="🔙 Назад (Изменить углы)", callback_data="back_to_step_8_internal")]
    ])
    
    await smart_edit(callback.message, f"{alert_text}\n\n{summary}", kb)

@router.callback_query(F.data == "info_rnd")
async def info_rnd(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "📐 <b>Прямые или Скругленные: Что выбрать?</b>\n\n"
        "Форма углов — это не просто декор, а вопрос долговечности и восприятия бренда.\n\n"
        "🟦 <b>Прямые — Строгая классика</b>\n"
        "Деловой стандарт. Подчеркивают порядок и сдержанность.\n"
        "✅ <i>Для кого:</i> Юристы, финансы, B2B, производство.\n"
        "⚠️ <i>Минус:</i> Уголки быстрее изнашиваются и «лохматятся» в кармане.\n\n"
        "🔄 <b>Скругленные — Мягкость и долговечность</b>\n"
        "Визитка становится приятнее на ощупь и дольше сохраняет аккуратный вид.\n"
        "✅ <i>Для кого:</i> Личный бренд, сфера услуг, креатив, премиум.\n"
        "⚠️ <i>Минус:</i> Могут спорить с очень строгим «квадратным» дизайном.\n\n"
        "🧠 <b>Психология восприятия</b>\n"
        "• <b>Прямые углы</b> транслируют контроль и структуру.\n"
        "• <b>Скругленные</b> — открытость, комфорт и заботу.\n\n"
        "🎯 <b>Честный вывод:</b>\n"
        "Хотите строгости? Оставляйте <b>прямые</b>.\n"
        "Хотите, чтобы визитка дольше жила в руках клиента? Выбирайте <b>скругление</b>."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Вернуться к выбору", callback_data="back_to_step_8_internal")]])
    await smart_edit(callback.message, text, kb, PHOTO_ROUNDING)

@router.callback_query(F.data == "back_to_step_8_internal")
async def back_to_step_8(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await render_step_8(callback, state)

@router.callback_query(F.data == "vizitki_submit")
async def vizitki_submit_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer("Заказ отправлен!", show_alert=True)
    
    data = await state.get_data()
    # === ИСПРАВЛЕНИЕ: Используем chat.id для надежности
    user_id = callback.message.chat.id
    
    # === ИСПРАВЛЕНИЕ: Используем mock_db вместо database
    profile = mock_db.get_user(user_id)
    
    # Получаем скидку
    user_discount = 0
    if hasattr(mock_db, 'get_user_discount'):
        user_discount = mock_db.get_user_discount(user_id, 'Визитки')

    # 1. Сохраняем заказ в новую базу
    order_id = mock_db.add_order(
        user_id=user_id,
        description=data['final_summary'],
        category="Визитки"
    )
    
    # 2. Формируем сообщение для менеджера
    # Безопасное получение полей (get), чтобы не было ошибок
    org_name = profile.get('org_name', '-')
    client_name = profile.get('name', 'Клиент')
    client_phone = profile.get('phone', '-')
    client_city = profile.get('city', '-')

    admin_text = (
        f"🚀 <b>НОВЫЙ ЗАКАЗ #{order_id} (Визитки)</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏢 Организация: <b>{org_name}</b>\n"
        f"👤 Клиент: {client_name}\n"
        f"📱 Тел: {client_phone}\n"
        f"🏙 Город: {client_city}\n"
        f"🎁 Скидка клиента: <b>{user_discount}%</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>Техзадание:</b>\n{data['final_summary']}"
    )
    
    # 3. Отправляем админам
    admin_ids = os.getenv("ADMIN_ID", "").split(",")
    for admin_id in admin_ids:
        try:
            await bot.send_message(chat_id=admin_id.strip(), text=admin_text, parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка отправки админу {admin_id}: {e}")

    # 4. Финальный ответ пользователю
    await callback.message.edit_text(
        f"✅ <b>Заказ №{order_id} успешно оформлен!</b>\n\n"
        f"Менеджер получил уведомление и свяжется с вами для подтверждения стоимости (с учетом вашей скидки {user_discount}%).\n\n"
        f"Статус заказа можно отслеживать в Личном кабинете.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
        ]),
        parse_mode="HTML"
    )
    await state.clear()

# === END handlers/calc_vizitki.py ===