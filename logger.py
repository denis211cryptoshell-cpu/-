"""
Настройка логирования через loguru.
Цветной вывод в консоль + сохранение ошибок в файл.
"""

import sys
from pathlib import Path

from loguru import logger

from config import settings


def setup_logger() -> None:
    """
    Инициализация логгера.
    
    - Вывод в консоль с цветом и форматированием
    - Сохранение ошибок в errors.log (ротация по размеру)
    """
    # Удаляем стандартный обработчик
    logger.remove()

    # Консольный вывод (цветной)
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # Файловый вывод (только ошибки)
    log_path = Path("logs/errors.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_path,
        level="ERROR",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
        rotation="10 MB",  # Ротация при 10 МБ
        compression="zip",  # Архивация старых логов
        retention="7 days",  # Хранение 7 дней
        enqueue=True,  # Асинхронная запись (безопасно для asyncio)
    )

    logger.info("Логгер инициализирован")


# Экспорт для удобства импорта
__all__ = ["logger", "setup_logger"]
