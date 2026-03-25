"""
Глобальный обработчик ошибок.
"""

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter, TelegramNetworkError
from aiogram.types import ErrorEvent

from logger import logger

router = Router()


@router.errors()
async def errors_handler(event: ErrorEvent) -> bool:
    """
    Глобальный обработчик ошибок.

    Логгирует ошибку и предотвращает падение бота.
    
    Returns:
        True — ошибка обработана, False — propagate дальше
    """
    error = event.exception
    update_type = event.update.__class__.__name__

    # ========== ИГНОРИРУЕМЫЕ ОШИБКИ (не логируем) ==========
    
    if isinstance(error, TelegramBadRequest):
        error_msg = str(error)
        
        # Пользователь быстро нажал кнопки
        if "message is not modified" in error_msg:
            logger.debug(f"Игнорируем: сообщение не изменено ({update_type})")
            return True
        
        # Сообщение удалено
        if "message can't be edited" in error_msg:
            logger.debug(f"Игнорируем: сообщение недоступно ({update_type})")
            return True
        
        # Бот заблокирован
        if "have no rights to send" in error_msg or "bot was blocked" in error_msg:
            logger.debug(f"Игнорируем: бот заблокирован пользователем ({update_type})")
            return True
        
        # Пустой текст сообщения
        if "message text is empty" in error_msg:
            logger.warning(f"Пустой текст сообщения ({update_type})")
            return True

    if isinstance(error, TelegramRetryAfter):
        # Лимит рассылки — уже обработано в broadcaster.py
        logger.debug(f"Лимит Telegram: ждём {error.retry_after} сек")
        return True
    
    if isinstance(error, TelegramNetworkError):
        # Сетевые ошибки — логируем как warning
        logger.warning(f"Сетевая ошибка Telegram ({update_type}): {error}")
        return True

    # ========== КРИТИЧЕСКИЕ ОШИБКИ (логируем с traceback) ==========
    
    logger.opt(exception=error).error(
        f"🔥 Критичная ошибка в {update_type}:\n"
        f"Update: {event.update}\n"
        f"Exception: {type(error).__name__}: {error}"
    )

    # Возвращаем True чтобы ошибка не пропагировалась
    return True
