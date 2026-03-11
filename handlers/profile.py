from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from database import Database
from models import User

router = Router()

ACTIVE_STATUSES = ["pending_calculation", "priced", "in_work", "design", "ready"]

class ProfileEdit(StatesGroup):
    waiting_for_name = State()
    waiting_for_org = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_city = State()
    waiting_for_address = State()

@router.callback_query(F.data == "main_profile")
async def show_profile(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Отображение личного кабинета"""
    await state.clear()
    user_id = callback.from_user.id
    profile = await db.get_user(user_id)
    
    # Проверка заполненности профиля (телефон - обязательный минимум)
    if not profile or not profile.phone or profile.phone == "-":
        text = (
            "👋 <b>Добро пожаловать в ваш Личный кабинет!</b>\n\n"
            "Чтобы мы могли сделать наше сотрудничество максимально удобным, "
            "пожалуйста, заполните небольшую анкету.\n\n"
            "✨ <b>Это займет буквально минуту и потребуется всего один раз.</b>\n"
            "Ваши данные сохранятся, и вам больше не придется вводить их при каждом заказе. "
            "Конечно, если что-то изменится, вы сможете обновить информацию в любой момент.\n\n"
            "<i>Начнем знакомство?</i>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Заполнить анкету", callback_data="profile_edit_full")],
            [InlineKeyboardButton(text="🏠 Вернуться в меню", callback_data="back_to_main")]
        ])
        await callback.message.edit_text(text, reply_markup=kb)
        return

    # Получаем заказы для статистики
    orders = await db.get_user_orders(user_id)
    active_count = sum(1 for o in orders if o.status in ACTIVE_STATUSES)
    archive_count = len(orders) - active_count

    text = (
        f"💼 <b>Ваш профиль: {profile.full_name}</b>\n\n"
        f"🏢 Организация: <b>{profile.org_name or 'Не указана'}</b>\n"
        f"📞 Контактный телефон: <b>{profile.phone}</b>\n"
        f"📧 Электронная почта: <b>{profile.email or '—'}</b>\n"
        f"📍 Адрес доставки: <b>{profile.city or '—'}, {profile.address or '—'}</b>\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"📊 <b>Ваша статистика заказов:</b>\n"
        f"⏳ В работе: <b>{active_count}</b>  |  📁 В архиве: <b>{archive_count}</b>\n\n"
        f"👇 Выберите нужное действие:"
    )
    
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"⏳ Активные ({active_count})", callback_data="profile_active"),
            InlineKeyboardButton(text=f"📁 Архив ({archive_count})", callback_data="profile_archive")
        ],
        [InlineKeyboardButton(text="⚙️ Редактировать данные", callback_data="profile_edit_full")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text=text, reply_markup=builder)

# --- ЛОГИКА ЗАПОЛНЕНИЯ ПРОФИЛЯ ---

@router.callback_query(F.data == "profile_edit_full")
async def start_profile_edit(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ProfileEdit.waiting_for_name)
    await callback.message.edit_text(
        "😊 <b>Шаг 1 из 6: Знакомство</b>\n\n"
        "Как к вам можно обращаться?\n"
        "Пожалуйста, введите ваше <b>Имя и Фамилию</b>:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="main_profile")]])
    )

@router.message(ProfileEdit.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext, db: Database):
    await db.update_user_profile(message.from_user.id, full_name=message.text)
    await state.set_state(ProfileEdit.waiting_for_org)
    await message.answer(
        "🏢 <b>Шаг 2 из 6: Компания</b>\n\n"
        "Очень приятно! Подскажите, какую <b>Организацию</b> вы представляете?\n"
        "<i>Если вы заказываете для себя, просто напишите «Частное лицо».</i>"
    )

@router.message(ProfileEdit.waiting_for_org)
async def process_org(message: types.Message, state: FSMContext, db: Database):
    await db.update_user_profile(message.from_user.id, org_name=message.text)
    await state.set_state(ProfileEdit.waiting_for_phone)
    
    # Кнопка для отправки контакта
    contact_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить мой номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        "📞 <b>Шаг 3 из 6: Связь</b>\n\n"
        "На какой <b>номер телефона</b> менеджер сможет позвонить для уточнения деталей заказа?\n\n"
        "<i>Вы можете нажать кнопку ниже, чтобы отправить номер автоматически:</i>",
        reply_markup=contact_kb
    )

@router.message(ProfileEdit.waiting_for_phone, F.contact | F.text)
async def process_phone(message: types.Message, state: FSMContext, db: Database):
    phone = message.contact.phone_number if message.contact else message.text
    await db.update_user_profile(message.from_user.id, phone=phone)
    await state.set_state(ProfileEdit.waiting_for_email)
    await message.answer(
        "📧 <b>Шаг 4 из 6: Почта</b>\n\n"
        "Спасибо! Теперь укажите ваш <b>Email</b>.\n"
        "Туда мы будем отправлять макеты и отчетные документы:",
        reply_markup=ReplyKeyboardRemove() # Убираем кнопку контакта
    )

@router.message(ProfileEdit.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext, db: Database):
    await db.update_user_profile(message.from_user.id, email=message.text)
    await state.set_state(ProfileEdit.waiting_for_city)
    await message.answer(
        "🏙 <b>Шаг 5 из 6: Город</b>\n\n"
        "Почти закончили! В каком <b>городе</b> вы находитесь?"
    )

@router.message(ProfileEdit.waiting_for_city)
async def process_city(message: types.Message, state: FSMContext, db: Database):
    await db.update_user_profile(message.from_user.id, city=message.text)
    await state.set_state(ProfileEdit.waiting_for_address)
    await message.answer(
        "📍 <b>Шаг 6 из 6: Адрес</b>\n\n"
        "И последний штрих — введите <b>точный адрес</b> для доставки (улица, дом, офис).\n"
        "<i>Мы запомним его, чтобы вам не пришлось вводить его снова!</i>"
    )

@router.message(ProfileEdit.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext, db: Database):
    await db.update_user_profile(message.from_user.id, address=message.text)
    await state.clear()
    
    await message.answer(
        "🎉 <b>Ура! Профиль полностью настроен.</b>\n\n"
        "Благодарим за ваше время! Теперь оформление заказов станет намного быстрее, "
        "а история всех ваших заявок будет бережно храниться здесь.\n\n"
        "<i>Помните, что вы в любой момент можете изменить эти данные в настройках профиля.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 Перейти в Личный кабинет", callback_data="main_profile")]])
    )

# --- ЛОГИКА ЗАКАЗОВ ---
# (Остальной код без изменений...)

# --- ЛОГИКА ЗАКАЗОВ ---

STATUS_MAP = {
    "pending_calculation": "⏳ На просчете",
    "priced": "💰 Ожидает подтверждения",
    "in_work": "⚙️ В работе",
    "design": "🎨 Дизайн",
    "ready": "✅ Готов к выдаче",
    "completed": "📁 Завершен",
    "cancelled": "❌ Отменен"
}

@router.callback_query(F.data.in_(["profile_active", "profile_archive"]))
async def show_orders(callback: types.CallbackQuery, db: Database):
    user_id = callback.from_user.id
    is_active = callback.data == "profile_active"
    
    orders = await db.get_user_orders(user_id)
    
    if is_active:
        filtered_orders = [o for o in orders if o.status in ACTIVE_STATUSES]
        title = "⏳ <b>Ваши активные заказы:</b>"
    else:
        filtered_orders = [o for o in orders if o.status not in ACTIVE_STATUSES]
        title = "📁 <b>Архив ваших заказов:</b>"

    if not filtered_orders:
        text = f"{title}\n\n<i>У вас пока нет заказов в этом разделе.</i>"
    else:
        text = f"{title}\n\n"
        for i, order in enumerate(filtered_orders, 1):
            status_text = STATUS_MAP.get(order.status, order.status)
            date_str = order.created_at.strftime("%d.%m.%Y")
            price_text = f" - <b>{order.offered_price} BYN</b>" if order.offered_price > 0 else ""
            
            text += (
                f"{i}. <b>Заказ №{order.id}</b> ({date_str})\n"
                f"🏷 Категория: {order.category}\n"
                f"📊 Статус: {status_text}{price_text}\n"
                f"------------------\n"
            )
            if i >= 10: # Ограничим вывод 10 последними заказами
                text += "<i>Показаны последние 10 заказов...</i>"
                break

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в профиль", callback_data="main_profile")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb)
