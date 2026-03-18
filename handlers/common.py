import os
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Database

logger = logging.getLogger(__name__)


async def send_order_to_managers(order_id: int, user_id: int, summary_text: str, category: str, bot: Bot, db: Database):
    from datetime import datetime
    
    logger.info(f"📤 Начинаем отправку заказа #{order_id} менеджерам...")
    
    profile = await db.get_user(user_id)

    client_name = profile.full_name if profile and profile.full_name else "Не указано"
    client_org = profile.org_name if profile and profile.org_name else "—"
    client_phone = profile.phone if profile and profile.phone else "—"
    client_email = profile.email if profile and profile.email else "—"
    client_city = profile.city if profile and profile.city else "—"
    client_address = profile.address if profile and profile.address else "—"
    client_username = f"@{profile.username}" if profile and profile.username else "скрыт"

    # Красивое форматирование для менеджера
    admin_text = (
        f"🔔 <b>НОВАЯ ЗАЯВКА НА ПРОСЧЁТ</b>\n\n"
        f"<b>📦 ЗАКАЗ #{order_id}</b>\n"
        f"<code>═══════════════════════════════════</code>\n"
        f"<b>📂 Категория:</b> {category}\n"
        f"<b>⏱ Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        f"<code>═══════════════════════════════════</code>\n\n"
        f"<b>👤 ИНФОРМАЦИЯ О КЛИЕНТЕ:</b>\n"
        f"  <b>Имя:</b> {client_name}\n"
        f"  <b>Организация:</b> {client_org}\n"
        f"  <b>Телефон:</b> <code>{client_phone}</code>\n"
        f"  <b>Email:</b> {client_email}\n"
        f"  <b>Город:</b> {client_city}\n"
        f"  <b>Адрес:</b> {client_address}\n"
        f"  <b>Telegram:</b> {client_username}\n\n"
        f"📋 <b>ПАРАМЕТРЫ ЗАКАЗА:</b>\n"
        f"{summary_text}\n\n"
        f"<code>═══════════════════════════════════</code>\n"
        f"💰 <i>Рассчитайте стоимость и отправьте клиенту, нажав кнопку ниже:</i>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Указать стоимость", callback_data=f"mgr_price_{order_id}")]
    ])

    admin_ids = [x.strip() for x in os.getenv("ADMIN_ID", "").split(",") if x.strip()]
    manager_ids = await db.get_managers()
    all_ids = list(set(admin_ids + [str(mid) for mid in manager_ids]))

    sent_count = 0
    for adm_id in all_ids:
        try:
            await bot.send_message(chat_id=adm_id, text=admin_text, reply_markup=kb, parse_mode="HTML")
            sent_count += 1
            logger.info(f"✅ Заказ #{order_id} отправлен менеджеру {adm_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки заказа #{order_id} менеджеру {adm_id}: {e}")

    logger.info(f"📤 Заказ #{order_id} успешно отправлен ({sent_count}/{len(all_ids)})")
