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
from logger import setup_logger, logger, log_startup, log_shutdown
from database import init_db, DB_TYPE, db
from handlers import start, menu, admin, errors
from utils import DatabaseMiddleware, ServiceMiddleware, AdminMiddleware
from utils.scheduler import scheduler_service
from services.backup import backup_service


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
        logger.info(f"База данных инициализирована ({DB_TYPE})")

        # Создаём стартовый бекап (только для SQLite)
        if DB_TYPE == "sqlite":
            backup_service.create_backup()
            logger.info("Создан стартовый бекап БД")

        # Запускаем планировщик задач (авто-бекап в 00:00)
        # Для PostgreSQL бекап не нужен — Supabase делает сам
        if DB_TYPE == "sqlite":
            scheduler_service.start()

        # Удаление вебхука (на всякий случай)
        await bot.delete_webhook(drop_pending_updates=True)

        # Логирование запуска
        bot_id = bot.id
        log_startup(bot_id)

        # Запуск polling
        logger.info("Бот запущен в режиме polling")
        await dp.start_polling(bot)

    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")

    except Exception as e:
        logger.critical(f"🔥 Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # Корректное завершение
        log_shutdown()
        if DB_TYPE == "sqlite":
            scheduler_service.stop()
        await db.disconnect()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
