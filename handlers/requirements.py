from aiogram import Router, F, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Импортируем из существующих файлов проекта
from handlers.start import WELCOME_TEXT 
from keyboards import get_main_menu

router = Router()

# --- ТЕКСТЫ С ЗАБОТОЙ О КЛИЕНТЕ ---

TEXTS = {
    "main": (
        "📋 <b>Технические стандарты</b>\n\n"
        "Чтобы ваш тираж получился идеальным, мы подготовили краткий справочник по подготовке макетов.\n\n"
        "📧 <b>Как передать файлы?</b>\n"
        "• <b>До 20 Мб:</b> отправляйте прямо на почту.\n"
        "• <b>Свыше 20 Мб:</b> загрузите на облако (Google/Yandex) и пришлите ссылку.\n"
        "• <i>Имя файла:</i> Название_Лицо_Тираж.pdf\n\n"
        "👇 <i>Выберите категорию, чтобы узнать подробности:</i>"
    ),
    "req_pdf": (
        "📄 <b>Почему мы любим PDF?</b>\n\n"
        "Это самый надежный формат для печати. В нем ничего «не слетит» и не сдвинется.\n\n"
        "<b>Наш чек-лист для PDF:</b>\n"
        "1. <b>Версия:</b> PDF 1.4 и выше (настройка Press Quality).\n"
        "2. <b>Размер:</b> 1:1, обязательно наличие TrimBox (обрезной формат).\n"
        "3. <b>Вылеты (Bleed):</b> 3 мм со всех сторон.\n"
        "4. <b>Цвет:</b> Только CMYK (без RGB и ICC профилей).\n"
        "5. <b>Шрифты:</b> Все шрифты должны быть внедрены (Embedded)."
    ),
    "req_psd": (
        "🎨 <b>Если готовите в Photoshop (Растр)</b>\n\n"
        "Растровые изображения требуют высокого качества, чтобы не было «пикселей».\n\n"
        "• <b>Цветовая модель:</b> Строго CMYK.\n"
        "• <b>Разрешение:</b> 300 dpi (для обычных картинок) или 600 dpi (для мелкого текста).\n"
        "• <b>Слои:</b> Пожалуйста, сведите все слои в один (команда Flatten Image).\n"
        "• <b>Черный текст:</b> Должен быть 100% Black (K=100), а не составным."
    ),
    "req_vector": (
        "✒️ <b>Если готовите в Corel / Illustrator (Вектор)</b>\n\n"
        "Вектор — лучший выбор для логотипов и текста.\n\n"
        "• <b>Шрифты:</b> Обязательно переведите все тексты в кривые (Curves/Outlines).\n"
        "• <b>Эффекты:</b> Тени, прозрачности и линзы лучше растрировать (300 dpi, CMYK).\n"
        "• <b>Overprint:</b> Проверьте настройки наложения, чтобы белые элементы не исчезли при печати."
    ),
    "req_indesign": (
        "📖 <b>Многостраничная верстка (InDesign)</b>\n\n"
        "• <b>Изображения:</b> Все связи (Links) должны быть внедрены или приложены в папке.\n"
        "• <b>Шрифты:</b> Приложите файлы шрифтов или переведите заголовки в кривые.\n"
        "• <b>Системные шрифты:</b> Старайтесь не использовать Arial или Times New Roman (версии могут конфликтовать)."
    ),
    "req_size": (
        "📏 <b>Зачем нужны «Вылеты»?</b>\n\n"
        "Нож резальной машины имеет погрешность в 1 мм. Если не сделать запас фона, по краям могут остаться белые полосы.\n\n"
        "✂️ <b>Правило:</b>\n"
        "Добавляйте к размеру изделия <b>по 2-3 мм</b> с каждой стороны.\n"
        "<i>Пример: Визитка 90х50 мм → Макет должен быть 94х54 мм.</i>\n\n"
        "🛡 <b>Безопасная зона:</b>\n"
        "Не ставьте важный текст ближе <b>4 мм</b> к краю реза, чтобы его случайно не зарезало."
    ),
    "req_xerox": (
        "✨ <b>Эксклюзивная отделка (Xerox Iridesse)</b>\n"
        "<i>Золото, Серебро, Белила, Лак</i>\n\n"
        "Мы можем напечатать металлизированными цветами! Чтобы машина поняла задачу, назовите Spot-цвета (Pantone) строго так:\n\n"
        "🥇 <b>Gold</b> (Золото)\n"
        "🥈 <b>Silver</b> (Серебро)\n"
        "⚪ <b>White</b> (Белила)\n"
        "💧 <b>Clear</b> (Прозрачный лак)\n\n"
        "<i>Совет: Металлик выглядит эффектнее на темных бумагах.</i>"
    )
}

# --- КЛАВИАТУРЫ ---

def kb_req_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 PDF (Стандарт)", callback_data="req_pdf")],
        [InlineKeyboardButton(text="🎨 Photoshop", callback_data="req_psd"),
         InlineKeyboardButton(text="✒️ Вектор (AI/CDR)", callback_data="req_vector")],
        [InlineKeyboardButton(text="📖 InDesign", callback_data="req_indesign"),
         InlineKeyboardButton(text="📏 Размеры / Вылеты", callback_data="req_size")],
        [InlineKeyboardButton(text="✨ Золото / Лак (Xerox)", callback_data="req_xerox")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
    ])

def kb_back_to_req():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К списку требований", callback_data="main_docs")],
        [InlineKeyboardButton(text="🏠 В Главное меню", callback_data="back_to_main")]
    ])

# --- ХЕНДЛЕРЫ ---

@router.callback_query(F.data == "main_docs")
async def show_req_menu(callback: types.CallbackQuery):
    """Главный вход в меню документации"""
    await callback.answer()
    try:
        await callback.message.edit_text(
            text=TEXTS["main"],
            reply_markup=kb_req_menu(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass # Игнорируем, если сообщение то же самое

@router.callback_query(F.data.startswith("req_"))
async def show_req_detail(callback: types.CallbackQuery):
    """Обработка всех детальных страниц требований"""
    await callback.answer()
    text_content = TEXTS.get(callback.data, "Информация временно недоступна.")
    
    try:
        await callback.message.edit_text(
            text=text_content,
            reply_markup=kb_back_to_req(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass


