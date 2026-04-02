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
from database import init_db, DB_TYPE, db, run_migrations
from handlers import start, menu, admin, errors
from utils import DatabaseMiddleware, ServiceMiddleware, AdminMiddleware
from utils.rate_limiter import RateLimitMiddleware
from utils.scheduler import scheduler_service
from utils.delete_message_middleware import DeleteUserMessageMiddleware
from utils.cache import init_cache
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

    # Инициализация кэша
    if settings.cache_backend == "redis" and settings.redis_url:
        init_cache(backend="redis", redis_url=settings.redis_url)
    else:
        init_cache(backend="local")

    # Подключение middleware
    # DeleteUserMessageMiddleware должен быть ПЕРВЫМ для dp.message — чтобы удалять все сообщения
    dp.message.middleware(DeleteUserMessageMiddleware())
    
    # Остальные middleware для dp.update
    dp.update.middleware(RateLimitMiddleware())
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

        # Применяем миграции
        await run_migrations(db)
        logger.info("Миграции БД применены")

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
        
        # Отключение Redis (если используется)
        if settings.cache_backend == "redis":
            from utils.cache import get_cache
            cache_backend = get_cache()
            if hasattr(cache_backend, 'disconnect') and cache_backend._connected:
                await cache_backend.disconnect()
        
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
