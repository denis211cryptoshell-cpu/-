"""
Глобальный обработчик ошибок.
"""

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import ErrorEvent

from logger import logger

router = Router()


@router.errors()
async def errors_handler(event: ErrorEvent):
    """
    Глобальный обработчик ошибок.
    
    Логгирует ошибку и предотвращает падение бота.
    """
    error = event.exception

    # Игнорируем ожидаемые ошибки Telegram API
    if isinstance(error, TelegramBadRequest):
        if "message is not modified" in str(error):
            # Пользователь быстро нажал кнопки — не логируем
            return True
        if "message can't be edited" in str(error):
            # Сообщение удалено или недоступно
            return True
        if "have no rights to send" in str(error):
            # Бот заблокирован пользователем
            return True

    if isinstance(error, TelegramRetryAfter):
        # Лимит рассылки — обработано в broadcaster.py
        return True

    # Критические ошибки — логируем
    logger.opt(exception=error).error(
        f"Ошибка в обработчике: {event.update}"
    )

    # Возвращаем True чтобы ошибка не пропагировалась
    return True
