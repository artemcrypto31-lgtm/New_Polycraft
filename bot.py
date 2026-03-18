import asyncio
import logging
import logging.handlers
import os
import sys
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from database import Database
# Импортируем роутеры из файлов хендлеров
from handlers.start import router as start_router
from handlers.requirements import router as requirements_router
from handlers.promotions import router as promotions_router
from handlers.contacts import router as contacts_router
from handlers.profile import router as profile_router
from handlers.flyers import router as flyers_router
from handlers.leaflets import router as leaflets_router
from handlers.journals import router as journals_router
from handlers.posters import router as posters_router
from handlers.admin import router as admin_router
from handlers.admin_panel import router as admin_panel_router
from handlers.orders import router as orders_router
from handlers.booklets import router as booklets_router
from handlers.brochures import router as brochures_router

# Настройка логирования
log_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Логирование в файл с ротацией (5MB, храним 5 последних файлов)
file_handler = logging.handlers.RotatingFileHandler(
    'bot.log',
    maxBytes=5*1024*1024,  # 5MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(log_formatter)

# Логирование в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

# Добавляем к корневому логгеру
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

load_dotenv()

async def main():
    logger.info("🚀 Бот запускается...")
    
    # 2. Проверка конфигурации
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.critical("BOT_TOKEN не найден в переменных окружения или .env файле!")
        return

    # 3. Инициализация базы данных
    logger.info("Инициализация базы данных...")
    db = Database()
    await db.init_db()

    # 4. Инициализация бота
    logger.info("Инициализация бота...")
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # 5. Инициализация диспетчера
    logger.info("Инициализация диспетчера...")
    dp = Dispatcher()
    
    # Пробрасываем БД в middleware/хендлеры через context
    dp["db"] = db

    # Регистрируем роутеры
    logger.info("Регистрация роутеров...")
    # Сначала специфичные требования и акции, затем общий start
    dp.include_router(promotions_router)
    dp.include_router(requirements_router)
    dp.include_router(contacts_router)
    dp.include_router(profile_router)
    dp.include_router(flyers_router)
    dp.include_router(leaflets_router)
    dp.include_router(journals_router)
    dp.include_router(posters_router)
    dp.include_router(admin_router)
    dp.include_router(admin_panel_router)
    dp.include_router(booklets_router)
    dp.include_router(brochures_router)
    dp.include_router(orders_router)
    dp.include_router(start_router)
    
    # 6. Запуск бота
    logger.info("Бот запущен и готов к работе.")
    try:
        # Удаляем вебхуки и старые обновления перед началом
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Ошибка при работе бота: {e}")
    finally:
        # Корректное завершение ресурсов
        await db.close()
        await bot.session.close()
        logger.info("Работа бота остановлена.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
