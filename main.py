"""
Точка входа бота.
Инициализация, запуск polling.
"""

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from logger import setup_logger, logger
from database.db import db, init_db
from handlers import start, menu, admin, errors
from utils import DatabaseMiddleware, ServiceMiddleware, AdminMiddleware


async def main():
    """
    Основная функция запуска бота.
    """
    # Инициализация логгера
    setup_logger()
    logger.info("Запуск бота...")

    # Инициализация бота
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Инициализация диспетчера
    dp = Dispatcher()

    # Подключение middleware
    dp.update.middleware(DatabaseMiddleware(db))
    dp.update.middleware(ServiceMiddleware(db, bot))
    dp.update.middleware(AdminMiddleware())

    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(menu.router)
    dp.include_router(errors.router)

    try:
        # Инициализация БД
        await init_db()
        logger.info("База данных инициализирована")

        # Удаление вебхука (на всякий случай)
        await bot.delete_webhook(drop_pending_updates=True)

        # Запуск polling
        logger.info("Бот запущен в режиме polling")
        await dp.start_polling(bot)

    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")

    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # Корректное завершение
        await db.disconnect()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
