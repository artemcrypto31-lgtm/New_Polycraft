import os
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import Database

router = Router()

STATUS_MAP = {
    "pending_calculation": "⏳ На просчете",
    "priced": "💰 Ожидает подтверждения",
    "in_work": "⚙️ В работе",
    "design": "🎨 Дизайн",
    "ready": "✅ Готов",
    "completed": "📁 Завершен",
    "cancelled": "❌ Отменен",
}

STATUS_KEYS = list(STATUS_MAP.keys())

ROLE_MAP = {
    "client": "👤 Клиент",
    "manager": "👔 Менеджер",
    "admin": "🛡 Администратор",
}


class AdminStates(StatesGroup):
    waiting_order_status = State()
    waiting_user_role = State()


async def is_manager_or_admin(user_id: int, db: Database) -> bool:
    admin_ids = [x.strip() for x in os.getenv("ADMIN_ID", "").split(",") if x.strip()]
    if str(user_id) in admin_ids:
        return True
    user = await db.get_user(user_id)
    return user is not None and user.role in ("manager", "admin")


async def check_access(callback: types.CallbackQuery, db: Database) -> bool:
    if not await is_manager_or_admin(callback.from_user.id, db):
        await callback.answer("У вас нет доступа к панели управления.", show_alert=True)
        return False
    return True


@router.callback_query(F.data == "admin_panel")
async def admin_panel_main(callback: types.CallbackQuery, state: FSMContext, db: Database):
    if not await check_access(callback, db):
        return
    await state.clear()
    await callback.answer()

    order_stats = await db.get_order_stats()
    user_stats = await db.get_user_stats()

    pending = order_stats.get("pending_calculation", 0)
    priced = order_stats.get("priced", 0)
    in_work = order_stats.get("in_work", 0)

    text = (
        "⚙️ <b>Панель управления</b>\n"
        "➖➖➖➖➖➖➖➖\n\n"
        "📊 <b>Сводка:</b>\n"
        f"• Заказов всего: <b>{order_stats.get('total', 0)}</b>\n"
        f"• ⏳ На просчете: <b>{pending}</b>\n"
        f"• 💰 Ожидают подтверждения: <b>{priced}</b>\n"
        f"• ⚙️ В работе: <b>{in_work}</b>\n\n"
        f"👥 <b>Пользователи:</b>\n"
        f"• Всего: <b>{user_stats.get('total', 0)}</b>\n"
        f"• Клиентов: <b>{user_stats.get('clients', 0)}</b>\n"
        f"• Менеджеров: <b>{user_stats.get('managers', 0)}</b>\n"
        f"• Администраторов: <b>{user_stats.get('admins', 0)}</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Заказы", callback_data="adm_orders_menu")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="adm_users_list")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
    ])

    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "adm_orders_menu")
async def admin_orders_menu(callback: types.CallbackQuery, db: Database):
    if not await check_access(callback, db):
        return
    await callback.answer()

    order_stats = await db.get_order_stats()

    text = (
        "📦 <b>Управление заказами</b>\n"
        "➖➖➖➖➖➖➖➖\n\n"
        "Выберите категорию для просмотра:\n\n"
    )

    buttons = []
    for status_key, status_label in STATUS_MAP.items():
        count = order_stats.get(status_key, 0)
        buttons.append([InlineKeyboardButton(
            text=f"{status_label} ({count})",
            callback_data=f"adm_orders_{status_key}"
        )])

    all_count = order_stats.get('total', 0)
    buttons.append([InlineKeyboardButton(text=f"📋 Все заказы ({all_count})", callback_data="adm_orders_all")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("adm_orders_"))
async def admin_orders_list(callback: types.CallbackQuery, db: Database):
    if not await check_access(callback, db):
        return
    await callback.answer()

    status_filter = callback.data.replace("adm_orders_", "")

    if status_filter == "all":
        orders = await db.get_all_orders(limit=30)
        title = "📋 Все заказы"
    else:
        orders = await db.get_all_orders(status=status_filter, limit=30)
        title = f"{STATUS_MAP.get(status_filter, status_filter)}"

    if not orders:
        text = f"{title}\n\nЗаказов не найдено."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_orders_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=kb)
        return

    text = f"📦 <b>{title}</b>\n➖➖➖➖➖➖➖➖\n\n"

    for order in orders[:15]:
        status_emoji = STATUS_MAP.get(order.status, order.status)
        created = order.created_at.strftime("%d.%m.%Y") if order.created_at else "—"
        price_str = f" | {order.offered_price:.2f} BYN" if order.offered_price else ""
        text += (
            f"<b>#{order.id}</b> | {order.category} | {status_emoji}{price_str}\n"
            f"   📅 {created}\n"
        )

    buttons = []
    row = []
    for order in orders[:15]:
        row.append(InlineKeyboardButton(text=f"#{order.id}", callback_data=f"adm_ord_{order.id}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm_orders_menu")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.regexp(r"^adm_ord_\d+$"))
async def admin_order_detail(callback: types.CallbackQuery, db: Database):
    if not await check_access(callback, db):
        return
    await callback.answer()

    order_id = int(callback.data.replace("adm_ord_", ""))
    order = await db.get_order(order_id)

    if not order:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    client = await db.get_user(order.user_id)
    client_name = client.full_name if client else f"ID: {order.user_id}"
    client_phone = client.phone if client and client.phone else "—"
    client_org = client.org_name if client and client.org_name else "—"
    client_username = f"@{client.username}" if client and client.username else "скрыт"

    manager_name = "—"
    if order.manager_id:
        manager = await db.get_user(order.manager_id)
        if manager:
            manager_name = manager.full_name or f"ID: {order.manager_id}"

    status_label = STATUS_MAP.get(order.status, order.status)
    created = order.created_at.strftime("%d.%m.%Y %H:%M") if order.created_at else "—"
    updated = order.updated_at.strftime("%d.%m.%Y %H:%M") if order.updated_at else "—"

    text = (
        f"📋 <b>Заказ #{order.id}</b>\n"
        f"➖➖➖➖➖➖➖➖\n\n"
        f"📦 <b>Категория:</b> {order.category}\n"
        f"📌 <b>Статус:</b> {status_label}\n"
        f"💰 <b>Стоимость:</b> {order.offered_price:.2f} BYN\n"
        f"📅 <b>Создан:</b> {created}\n"
        f"🔄 <b>Обновлен:</b> {updated}\n\n"
        f"👤 <b>Клиент:</b> {client_name}\n"
        f"📞 <b>Телефон:</b> {client_phone}\n"
        f"🏢 <b>Организация:</b> {client_org}\n"
        f"💬 <b>Telegram:</b> {client_username}\n"
        f"👔 <b>Менеджер:</b> {manager_name}\n"
    )

    if order.description:
        desc_preview = order.description[:500]
        text += f"\n📝 <b>Описание:</b>\n{desc_preview}"

    buttons = [
        [InlineKeyboardButton(text="🔄 Изменить статус", callback_data=f"adm_chst_{order.id}")],
    ]

    if order.status == "pending_calculation":
        buttons.append([InlineKeyboardButton(text="💰 Указать стоимость", callback_data=f"mgr_price_{order.id}")])

    if client and client.username:
        buttons.append([InlineKeyboardButton(text=f"💬 Написать клиенту", url=f"https://t.me/{client.username}")])

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"adm_orders_{order.status}")])
    buttons.append([InlineKeyboardButton(text="⚙️ Панель управления", callback_data="admin_panel")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.regexp(r"^adm_chst_\d+$"))
async def admin_change_status_menu(callback: types.CallbackQuery, db: Database):
    if not await check_access(callback, db):
        return
    await callback.answer()

    order_id = int(callback.data.replace("adm_chst_", ""))
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    current_label = STATUS_MAP.get(order.status, order.status)
    text = (
        f"🔄 <b>Смена статуса заказа #{order_id}</b>\n\n"
        f"Текущий статус: <b>{current_label}</b>\n\n"
        "Выберите новый статус:"
    )

    buttons = []
    for status_key, status_label in STATUS_MAP.items():
        if status_key == order.status:
            continue
        buttons.append([InlineKeyboardButton(
            text=status_label,
            callback_data=f"adm_setst_{order_id}_{status_key}"
        )])

    buttons.append([InlineKeyboardButton(text="🔙 Назад к заказу", callback_data=f"adm_ord_{order_id}")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.regexp(r"^adm_setst_\d+_.+$"))
async def admin_set_status(callback: types.CallbackQuery, db: Database, bot: Bot):
    if not await check_access(callback, db):
        return
    await callback.answer()

    parts = callback.data.split("_", 3)
    order_id = int(parts[2])
    new_status = parts[3]

    if new_status not in STATUS_MAP:
        await callback.answer("Неизвестный статус.", show_alert=True)
        return

    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    old_label = STATUS_MAP.get(order.status, order.status)
    new_label = STATUS_MAP.get(new_status, new_status)

    await db.update_order_status(order_id, new_status)

    try:
        await bot.send_message(
            chat_id=order.user_id,
            text=(
                f"🔔 <b>Обновление по заказу #{order_id}</b>\n\n"
                f"Статус вашего заказа изменён:\n"
                f"{old_label} → <b>{new_label}</b>\n\n"
                "Если у вас есть вопросы — обратитесь к менеджеру через личный кабинет."
            ),
            parse_mode="HTML"
        )
    except:
        pass

    await callback.message.edit_text(
        f"✅ Статус заказа <b>#{order_id}</b> изменён:\n"
        f"{old_label} → <b>{new_label}</b>\n\n"
        "Клиент получил уведомление.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 К заказу", callback_data=f"adm_ord_{order_id}")],
            [InlineKeyboardButton(text="⚙️ Панель управления", callback_data="admin_panel")]
        ])
    )


@router.callback_query(F.data == "adm_users_list")
async def admin_users_list(callback: types.CallbackQuery, db: Database):
    if not await check_access(callback, db):
        return
    await callback.answer()

    users = await db.get_all_users(limit=30)

    if not users:
        await callback.message.edit_text(
            "👥 <b>Пользователи</b>\n\nПользователей пока нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
            ])
        )
        return

    text = "👥 <b>Пользователи</b>\n➖➖➖➖➖➖➖➖\n\n"

    for u in users[:20]:
        role_emoji = ROLE_MAP.get(u.role, u.role)
        username_str = f" @{u.username}" if u.username else ""
        text += f"• <b>{u.full_name or '—'}</b>{username_str} — {role_emoji}\n"

    buttons = []
    row = []
    for u in users[:20]:
        label = u.full_name[:8] if u.full_name else str(u.id)[:8]
        row.append(InlineKeyboardButton(text=label, callback_data=f"adm_usr_{u.id}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.regexp(r"^adm_usr_\d+$"))
async def admin_user_detail(callback: types.CallbackQuery, db: Database):
    if not await check_access(callback, db):
        return
    await callback.answer()

    user_id = int(callback.data.replace("adm_usr_", ""))
    user = await db.get_user(user_id)

    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    orders = await db.get_user_orders(user_id)
    role_label = ROLE_MAP.get(user.role, user.role)
    created = user.created_at.strftime("%d.%m.%Y") if user.created_at else "—"

    text = (
        f"👤 <b>Профиль пользователя</b>\n"
        f"➖➖➖➖➖➖➖➖\n\n"
        f"🆔 <b>ID:</b> {user.id}\n"
        f"📛 <b>Имя:</b> {user.full_name or '—'}\n"
        f"💬 <b>Username:</b> {'@' + user.username if user.username else '—'}\n"
        f"📞 <b>Телефон:</b> {user.phone or '—'}\n"
        f"📧 <b>Email:</b> {user.email or '—'}\n"
        f"🏢 <b>Организация:</b> {user.org_name or '—'}\n"
        f"📍 <b>Город:</b> {user.city or '—'}\n"
        f"🚚 <b>Адрес:</b> {user.address or '—'}\n\n"
        f"🔑 <b>Роль:</b> {role_label}\n"
        f"📅 <b>Дата регистрации:</b> {created}\n"
        f"📦 <b>Заказов:</b> {len(orders)}"
    )

    buttons = [
        [InlineKeyboardButton(text="🔑 Изменить роль", callback_data=f"adm_chrole_{user.id}")],
    ]

    if orders:
        buttons.append([InlineKeyboardButton(text="📦 Заказы пользователя", callback_data=f"adm_usrord_{user.id}")])

    if user.username:
        buttons.append([InlineKeyboardButton(text="💬 Написать", url=f"https://t.me/{user.username}")])

    buttons.append([InlineKeyboardButton(text="🔙 К списку", callback_data="adm_users_list")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.regexp(r"^adm_usrord_\d+$"))
async def admin_user_orders(callback: types.CallbackQuery, db: Database):
    if not await check_access(callback, db):
        return
    await callback.answer()

    user_id = int(callback.data.replace("adm_usrord_", ""))
    orders = await db.get_user_orders(user_id)
    user = await db.get_user(user_id)
    user_name = user.full_name if user else f"ID: {user_id}"

    if not orders:
        await callback.message.edit_text(
            f"📦 <b>Заказы: {user_name}</b>\n\nЗаказов нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"adm_usr_{user_id}")]
            ])
        )
        return

    text = f"📦 <b>Заказы: {user_name}</b>\n➖➖➖➖➖➖➖➖\n\n"
    for order in orders[:15]:
        status_label = STATUS_MAP.get(order.status, order.status)
        created = order.created_at.strftime("%d.%m.%Y") if order.created_at else "—"
        price_str = f" | {order.offered_price:.2f} BYN" if order.offered_price else ""
        text += f"<b>#{order.id}</b> | {order.category} | {status_label}{price_str}\n"

    buttons = []
    row = []
    for order in orders[:15]:
        row.append(InlineKeyboardButton(text=f"#{order.id}", callback_data=f"adm_ord_{order.id}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"adm_usr_{user_id}")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.regexp(r"^adm_chrole_\d+$"))
async def admin_change_role_menu(callback: types.CallbackQuery, db: Database):
    if not await check_access(callback, db):
        return

    caller = await db.get_user(callback.from_user.id)
    caller_is_admin = (
        str(callback.from_user.id) in [x.strip() for x in os.getenv("ADMIN_ID", "").split(",") if x.strip()]
        or (caller and caller.role == "admin")
    )
    if not caller_is_admin:
        await callback.answer("Только администратор может менять роли.", show_alert=True)
        return

    await callback.answer()

    user_id = int(callback.data.replace("adm_chrole_", ""))
    user = await db.get_user(user_id)

    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    current_label = ROLE_MAP.get(user.role, user.role)
    text = (
        f"🔑 <b>Смена роли: {user.full_name or user_id}</b>\n\n"
        f"Текущая роль: <b>{current_label}</b>\n\n"
        "Выберите новую роль:"
    )

    buttons = []
    for role_key, role_label in ROLE_MAP.items():
        if role_key == user.role:
            continue
        buttons.append([InlineKeyboardButton(
            text=role_label,
            callback_data=f"adm_setrole_{user_id}_{role_key}"
        )])

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"adm_usr_{user_id}")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.regexp(r"^adm_setrole_\d+_.+$"))
async def admin_set_role(callback: types.CallbackQuery, db: Database):
    caller = await db.get_user(callback.from_user.id)
    caller_is_admin = (
        str(callback.from_user.id) in [x.strip() for x in os.getenv("ADMIN_ID", "").split(",") if x.strip()]
        or (caller and caller.role == "admin")
    )
    if not caller_is_admin:
        await callback.answer("Только администратор может менять роли.", show_alert=True)
        return

    await callback.answer()

    parts = callback.data.split("_", 3)
    user_id = int(parts[2])
    new_role = parts[3]

    if new_role not in ROLE_MAP:
        await callback.answer("Неизвестная роль.", show_alert=True)
        return

    user = await db.get_user(user_id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    old_label = ROLE_MAP.get(user.role, user.role)
    new_label = ROLE_MAP.get(new_role, new_role)

    await db.set_user_role(user_id, new_role)

    await callback.message.edit_text(
        f"✅ Роль пользователя <b>{user.full_name or user_id}</b> изменена:\n"
        f"{old_label} → <b>{new_label}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 К профилю", callback_data=f"adm_usr_{user_id}")],
            [InlineKeyboardButton(text="⚙️ Панель управления", callback_data="admin_panel")]
        ])
    )
