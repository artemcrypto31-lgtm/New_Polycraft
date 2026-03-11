import os
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Database


async def send_order_to_managers(order_id: int, user_id: int, summary_text: str, category: str, bot: Bot, db: Database):
    profile = await db.get_user(user_id)

    client_name = profile.full_name if profile and profile.full_name else "Не указано"
    client_org = profile.org_name if profile and profile.org_name else "—"
    client_phone = profile.phone if profile and profile.phone else "—"
    client_email = profile.email if profile and profile.email else "—"
    client_city = profile.city if profile and profile.city else "—"
    client_address = profile.address if profile and profile.address else "—"
    client_username = f"@{profile.username}" if profile and profile.username else "скрыт"

    admin_text = (
        f"🔔 <b>НОВАЯ ЗАЯВКА НА ПРОСЧЁТ #{order_id}</b>\n"
        f"📦 <b>Категория:</b> {category}\n"
        f"➖➖➖➖➖➖➖➖\n\n"
        f"👤 <b>Информация о клиенте:</b>\n"
        f"• Имя: <b>{client_name}</b>\n"
        f"• Организация: <b>{client_org}</b>\n"
        f"• Телефон: <b>{client_phone}</b>\n"
        f"• Email: <b>{client_email}</b>\n"
        f"• Город: <b>{client_city}</b>\n"
        f"• Адрес доставки: <b>{client_address}</b>\n"
        f"• Telegram: <b>{client_username}</b>\n\n"
        f"📋 <b>Параметры заказа:</b>\n"
        f"{summary_text}\n\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"💰 <i>Рассчитайте стоимость и отправьте клиенту, нажав кнопку ниже:</i>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Указать стоимость", callback_data=f"mgr_price_{order_id}")]
    ])

    admin_ids = [x.strip() for x in os.getenv("ADMIN_ID", "").split(",") if x.strip()]
    manager_ids = await db.get_managers()
    all_ids = list(set(admin_ids + [str(mid) for mid in manager_ids]))

    for adm_id in all_ids:
        try:
            await bot.send_message(chat_id=adm_id, text=admin_text, reply_markup=kb, parse_mode="HTML")
        except:
            pass
