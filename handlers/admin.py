import os
import logging
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import Database

logger = logging.getLogger(__name__)

router = Router()


class ManagerResponse(StatesGroup):
    waiting_for_price = State()


async def is_manager_or_admin(user_id: int, db: Database) -> bool:
    admin_ids = [x.strip() for x in os.getenv("ADMIN_ID", "").split(",") if x.strip()]
    if str(user_id) in admin_ids:
        return True
    user = await db.get_user(user_id)
    return user is not None and user.role in ("manager", "admin")


@router.callback_query(F.data.startswith("mgr_price_"))
async def mgr_start_pricing(callback: types.CallbackQuery, state: FSMContext, db: Database):
    if not await is_manager_or_admin(callback.from_user.id, db):
        await callback.answer("У вас нет прав для этого действия.", show_alert=True)
        return

    await callback.answer()
    order_id = int(callback.data.replace("mgr_price_", ""))

    order = await db.get_order(order_id)
    if not order or order.status != "pending_calculation":
        await callback.answer("Этот заказ уже обработан.", show_alert=True)
        return

    await state.set_state(ManagerResponse.waiting_for_price)
    await state.update_data(pricing_order_id=order_id)

    await callback.message.answer(
        f"💰 <b>Заказ #{order_id}</b>\n\n"
        "Введите стоимость заказа в BYN (только число):\n"
        "<i>Например: 150.50</i>",
        parse_mode="HTML"
    )


@router.message(ManagerResponse.waiting_for_price)
async def mgr_set_price(message: types.Message, state: FSMContext, bot: Bot, db: Database):
    try:
        price = float(message.text.replace(",", ".").strip())
        if price <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Введите корректную сумму (например: 250 или 150.50)")
        return

    data = await state.get_data()
    order_id = data.get("pricing_order_id")

    if not order_id:
        await state.clear()
        await message.answer("Ошибка. Попробуйте снова через кнопку в заказе.")
        return

    order = await db.get_order(order_id)
    if not order or order.status != "pending_calculation":
        await state.clear()
        await message.answer("Этот заказ уже обработан другим менеджером.")
        return

    await db.set_order_price(order_id, price, message.from_user.id)
    logger.info(f"💰 Менеджер {message.from_user.id} установил цену {price} для заказа #{order_id}")

    if message.from_user.username:
        try:
            await db.update_user_profile(message.from_user.id, username=message.from_user.username)
        except:
            pass

    await state.clear()

    await message.answer(
        f"✅ <b>Готово!</b> Стоимость <b>{price:.2f} BYN</b> отправлена клиенту по заказу #{order_id}.\n\n"
        f"Клиент получит уведомление и сможет подтвердить или отклонить заказ. "
        f"Вы получите оповещение о его решении. 🔔",
        parse_mode="HTML"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Цена устраивает", callback_data=f"order_accept_{order_id}")],
        [InlineKeyboardButton(text="❌ Отказаться", callback_data=f"order_decline_{order_id}")],
    ])

    await bot.send_message(
        chat_id=order.user_id,
        text=(
            f"📬 <b>Отличные новости! Ваш заказ #{order_id} просчитан!</b>\n\n"
            f"Наш менеджер внимательно изучил все параметры вашего заказа "
            f"и подготовил расчёт стоимости.\n\n"
            f"{order.description}\n\n"
            f"➖➖➖➖➖➖➖➖\n"
            f"💰 <b>Итоговая стоимость: {price:.2f} BYN</b>\n\n"
            f"Если цена вас устраивает — нажмите <b>«Цена устраивает»</b>, "
            f"и мы свяжем вас с менеджером для обсуждения деталей и запуска в работу. 🚀\n\n"
            f"Если хотите обсудить условия или отказаться — нажмите <b>«Отказаться»</b>. "
            f"Вы всегда можете создать новый заказ с другими параметрами.\n\n"
            f"👇 <i>Выберите действие:</i>"
        ),
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("order_accept_"))
async def client_accept_order(callback: types.CallbackQuery, db: Database, bot: Bot):
    await callback.answer()
    order_id = int(callback.data.replace("order_accept_", ""))

    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    if order.user_id != callback.from_user.id:
        await callback.answer("Это не ваш заказ.", show_alert=True)
        return

    if order.status != "priced":
        await callback.answer("Этот заказ уже обработан.", show_alert=True)
        return

    await db.update_order_status(order_id, "in_work")

    manager = await db.get_user(order.manager_id) if order.manager_id else None

    buttons = []
    if manager and manager.username:
        buttons.append([InlineKeyboardButton(text="💬 Написать менеджеру", url=f"https://t.me/{manager.username}")])
    elif order.manager_id:
        buttons.append([InlineKeyboardButton(text="💬 Написать менеджеру", url=f"tg://user?id={order.manager_id}")])
    buttons.append([InlineKeyboardButton(text="👤 Личный кабинет", callback_data="main_profile")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        f"🎉 <b>Замечательно! Заказ #{order_id} подтверждён!</b>\n\n"
        f"💰 Стоимость: <b>{order.offered_price:.2f} BYN</b>\n\n"
        "Теперь вы можете связаться с менеджером напрямую, чтобы обсудить все детали: "
        "сроки изготовления, доставку, оплату и требования к макету. 📋\n\n"
        "Менеджер уже получил уведомление о вашем подтверждении и готов к общению. 🤝\n\n"
        "<b>Спасибо, что выбираете «Поликрафт»!</b> 🙌\n\n"
        "👇 <i>Нажмите кнопку, чтобы написать менеджеру:</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )

    if order.manager_id:
        client = await db.get_user(order.user_id)
        client_name = client.full_name if client else "Клиент"
        client_username = f" (@{client.username})" if client and client.username else ""
        try:
            await bot.send_message(
                chat_id=order.manager_id,
                text=(
                    f"✅ <b>Заказ #{order_id} подтверждён клиентом!</b>\n\n"
                    f"👤 Клиент: <b>{client_name}</b>{client_username}\n"
                    f"💰 Стоимость: <b>{order.offered_price:.2f} BYN</b>\n\n"
                    f"Клиент принял предложенную стоимость и может написать вам "
                    f"для обсуждения деталей заказа. Будьте на связи! 🤝"
                ),
                parse_mode="HTML"
            )
        except:
            pass


@router.callback_query(F.data.startswith("order_decline_"))
async def client_decline_order(callback: types.CallbackQuery, db: Database, bot: Bot):
    await callback.answer()
    order_id = int(callback.data.replace("order_decline_", ""))

    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    if order.user_id != callback.from_user.id:
        await callback.answer("Это не ваш заказ.", show_alert=True)
        return

    if order.status != "priced":
        await callback.answer("Этот заказ уже обработан.", show_alert=True)
        return

    await db.update_order_status(order_id, "cancelled")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="main_profile")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])

    await callback.message.edit_text(
        f"📝 <b>Заказ #{order_id} отклонён.</b>\n\n"
        "Мы понимаем, что не всегда условия совпадают с ожиданиями — это абсолютно нормально. 🤝\n\n"
        "Вы в любой момент можете:\n"
        "• Создать новый заказ с другими параметрами\n"
        "• Обратиться к менеджеру для индивидуального расчёта\n"
        "• Заглянуть в раздел <b>«Акции»</b> — возможно, там найдётся выгодное предложение\n\n"
        "<b>Мы всегда рады помочь!</b> 🙌",
        reply_markup=kb,
        parse_mode="HTML"
    )

    if order.manager_id:
        client = await db.get_user(order.user_id)
        client_name = client.full_name if client else "Клиент"
        try:
            await bot.send_message(
                chat_id=order.manager_id,
                text=(
                    f"📝 <b>Заказ #{order_id} отклонён клиентом.</b>\n\n"
                    f"👤 Клиент: <b>{client_name}</b>\n\n"
                    f"Клиент решил отказаться от данного заказа. "
                    f"Возможно, он вернётся с другими параметрами."
                ),
                parse_mode="HTML"
            )
        except:
            pass
