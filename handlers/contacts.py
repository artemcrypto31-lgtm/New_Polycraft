from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

# ==================================================
# 1. РАЗДЕЛ КОНТАКТЫ 
# ==================================================
@router.callback_query(F.data == "main_contacts")
async def show_contacts(callback: types.CallbackQuery):
    await callback.answer()

    contact_text = (
        "🏭 <b>Наш офис и производство</b>\n"
        "г. Минск, ул. Кнорина, 50 корп. 4, к. 401A\n"
        "<i>Территория завода «Термопласт»</i>\n\n"
        "📍 Ниже отправили точку на карте — можно открыть в навигаторе\n\n"
        "⏰ <b>Время работы</b>\n"
        "Пн–Пт: 09:00—18:00\n"
        "Перерыв: 13:00—14:00\n"
        "Сб–Вс: выходной\n"
        "Сообщения можно писать в любое время — отвечаем в рабочие часы\n\n"
        "📞 <b>Связаться с нами</b>\n"
        "+375 (29) 142-05-95 (Наталья)\n"
        "+375 (29) 937-68-07 (Антонина)\n"
        "<i>Менеджеры — по всем вопросам оформления заказа и расчёта стоимости</i>\n"
        "📧 nata_martynava82@mail.ru\n\n"
        "🤝 <b>Обратная связь</b>\n"
        "Если вы заметили ошибку в работе чат-бота или что-то работает не так — пожалуйста, сообщите нам. "
        "Мы постоянно дорабатываем систему и будем благодарны за любую обратную связь.\n\n"
        "Заранее приносим извинения за возможные неудобства и спасибо, что помогаете сделать сервис лучше 🙌\n"
        "<a href='https://t.me/StudentBy'>💬 Написать в Telegram (Артем)</a>"
    )

    call_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
        ]
    )

    # Отправляем новое сообщение, так как после него будет локация
    await callback.message.answer(
        text=contact_text, 
        reply_markup=call_keyboard,
        disable_web_page_preview=True
    )

    # Геолокация
    await callback.message.answer_location(
        latitude=53.943849, 
        longitude=27.624977
    )
