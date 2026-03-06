import asyncio
import logging
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

load_dotenv()

async def main():
    # 1. Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )

    # 2. Проверка конфигурации
    token = os.getenv("BOT_TOKEN")
    if not token:
        logging.critical("BOT_TOKEN не найден в переменных окружения или .env файле!")
        return

    # 3. Инициализация базы данных
    db = Database()
    await db.init_db()

    # 4. Инициализация бота
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # 5. Инициализация диспетчера
    dp = Dispatcher()
    
    # Пробрасываем БД в middleware/хендлеры через context
    dp["db"] = db

    # Регистрируем роутеры
    # Сначала специфичные требования и акции, затем общий start
    dp.include_router(promotions_router)
    dp.include_router(requirements_router)
    dp.include_router(start_router)

    # 6. Запуск бота
    logging.info("Бот запущен и готов к работе.")
    try:
        # Удаляем вебхуки и старые обновления перед началом
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logging.exception(f"Ошибка при работе бота: {e}")
    finally:
        # Корректное завершение ресурсов
        await db.close()
        await bot.session.close()
        logging.info("Работа бота остановлена.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
