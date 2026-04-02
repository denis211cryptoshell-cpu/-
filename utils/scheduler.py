"""
Планировщик задач для бота.
Использует APScheduler для выполнения задач по расписанию.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from logger import logger
from services.backup import backup_service


class SchedulerService:
    """
    Сервис планирования задач.
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        """
        Запустить планировщик.
        """
        # Добавляем задачу авто-бекапа в 00:00 каждый день
        self.scheduler.add_job(
            self._daily_backup,
            CronTrigger(hour=0, minute=0),  # Каждый день в 00:00
            id="daily_backup",
            name="Ежедневный бекап БД",
            replace_existing=True,
        )

        # Добавляем задачу очистки кэша каждые 5 минут
        self.scheduler.add_job(
            self._cleanup_cache,
            CronTrigger(minute="*/5"),  # Каждые 5 минут
            id="cleanup_cache",
            name="Очистка кэша",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("✅ Планировщик задач запущен")

    def stop(self) -> None:
        """
        Остановить планировщик.
        """
        self.scheduler.shutdown()
        logger.info("🛑 Планировщик задач остановлен")

    async def _daily_backup(self) -> None:
        """
        Задача ежедневного бекапа.
        """
        logger.info("🔄 Запуск ежедневного бекапа...")
        backup_service.create_backup()

    async def _cleanup_cache(self) -> None:
        """
        Задача очистки просроченного кэша.
        """
        from utils.cache import get_cache

        cache_backend = get_cache()
        deleted = await cache_backend.cleanup_expired()
        if deleted > 0:
            logger.info(f"🧹 Очистка кэша: удалено {deleted} записей")

    def add_job(self, func, trigger, **kwargs) -> None:
        """
        Добавить задачу в планировщик.

        Args:
            func: Функция для выполнения
            trigger: Триггер (расписание)
            **kwargs: Дополнительные аргументы для APScheduler
        """
        self.scheduler.add_job(func, trigger, **kwargs)


# Глобальный экземпляр планировщика
scheduler_service = SchedulerService()
