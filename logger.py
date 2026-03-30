"""
Настройка логирования через loguru.
Улучшенная версия с фильтрами, эмодзи и раздельными файлами.
"""

import sys
import json
from pathlib import Path

from loguru import logger

from config import settings


# ========== ФИЛЬТРЫ ==========

def filter_sensitive(record: dict) -> bool:
    """
    Фильтр для скрытия чувствительных данных.
    Удаляет токены и ADMIN_ID из логов.
    """
    try:
        message = record["message"]
        
        # Скрываем токен бота (показываем только первые 10 символов)
        if hasattr(settings, 'bot_token') and settings.bot_token:
            token = settings.bot_token
            if len(token) > 10 and token in message:
                message = message.replace(token, f"{token[:10]}...")
        
        # Скрываем ADMIN_ID
        if hasattr(settings, 'admin_ids') and settings.admin_ids:
            for admin_id in settings.admin_ids:
                admin_id_str = str(admin_id)
                if admin_id_str in message:
                    message = message.replace(admin_id_str, "***")
        
        record["message"] = message
    except Exception:
        # Если фильтр упал — всё равно пропускаем лог
        pass
    
    return True


# ========== ФОРМАТЕРЫ ==========

def color_formatter(record: dict) -> str:
    """
    Цветной формат для консоли с эмодзи.
    """
    # Эмодзи для уровней
    emoji_map = {
        "TRACE": "🔍",
        "DEBUG": "🐛",
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "🔥",
    }
    emoji = emoji_map.get(record["level"].name, "•")
    
    record["extra"]["emoji"] = emoji
    
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "{extra[emoji]} <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>\n"
    )


def json_formatter(record: dict) -> str:
    """
    JSON формат для продакшена.
    Удобно для парсинга в ELK/Splunk/Grafana.
    """
    log_entry = {
        "timestamp": str(record["time"]),
        "level": record["level"].name,
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
        "message": record["message"],
        "exception": str(record["exception"]) if record["exception"] else None,
    }
    return json.dumps(log_entry, ensure_ascii=False) + "\n"


# ========== ИНИЦИАЛИЗАЦИЯ ==========

def setup_logger() -> None:
    """
    Инициализация логгера с упрощёнными настройками.

    Создаёт 2 обработчика:
    1. Консоль (цветной вывод с эмодзи)
    2. errors.log — только ошибки (храним 30 дней)
    """
    logger.remove()  # Удаляем дефолтный обработчик

    # 1. Консоль (цветной вывод с эмодзи)
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format=color_formatter,
        colorize=True,
        filter=filter_sensitive,
    )

    # 2. Файл: Только ошибки (для быстрого доступа)
    errors_log_path = Path("logs/errors.log")

    logger.add(
        errors_log_path,
        level="ERROR",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}\n"
            "{exception}"
        ),
        rotation="10 MB",
        compression="zip",
        retention="30 days",  # Ошибки храним дольше
        filter=filter_sensitive,
        enqueue=True,
    )

    logger.debug("Логгер инициализирован")


# ========== УДОБНЫЕ ФУНКЦИИ ==========

def log_startup(bot_id: int) -> None:
    """Логирование запуска бота."""
    logger.info(f"🤖 Бот запущен (ID: {bot_id})")


def log_shutdown() -> None:
    """Логирование остановки."""
    logger.info("🛑 Бот остановлен")


def log_network_error(error: str, retry_count: int) -> None:
    """Логирование сетевых ошибок."""
    logger.warning(f"🌐 Сетевая ошибка (попытка {retry_count}): {error}")


def log_database_error(operation: str, error: str) -> None:
    """Логирование ошибок БД."""
    logger.error(f"💾 Ошибка БД ({operation}): {error}")


def log_admin_action(action: str, admin_id: int) -> None:
    """Логирование действий админа."""
    logger.info(f"👤 Админ {admin_id}: {action}")


# Экспорт
__all__ = [
    "logger",
    "setup_logger",
    "log_startup",
    "log_shutdown",
    "log_network_error",
    "log_database_error",
    "log_admin_action",
]
