"""
Middleware для Rate Limiting — защита от спама.

Ограничивает количество запросов от пользователя в единицу времени.
Использует sliding window подход.
"""

import asyncio
from typing import Callable, Dict, Any, Awaitable
from collections import defaultdict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.types import ErrorEvent

from config import settings
from logger import logger
from messages.texts import RATE_LIMIT_MESSAGE, RATE_LIMIT_CALLBACK


class RateLimitError(Exception):
    """Исключение при превышении лимита запросов."""
    
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds")


class RateLimiter:
    """
    Sliding window rate limiter.
    
    Хранит временные метки запросов для каждого пользователя
    и проверяет лимиты при новых запросах.
    """
    
    def __init__(self):
        # {user_id: [timestamp1, timestamp2, ...]}
        self._requests: Dict[int, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def is_rate_limited(self, user_id: int) -> tuple[bool, int]:
        """
        Проверить, превышен ли лимит запросов.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            (is_limited, retry_after) — кортеж с флагом и временем ожидания
        """
        async with self._lock:
            now = asyncio.get_event_loop().time()
            window_start = now - settings.rate_limit_window
            
            # Очищаем старые запросы за пределами окна
            self._requests[user_id] = [
                ts for ts in self._requests[user_id]
                if ts > window_start
            ]
            
            # Проверяем лимит
            if len(self._requests[user_id]) >= settings.rate_limit_max_requests:
                # Вычисляем время до освобождения слота
                oldest_request = min(self._requests[user_id])
                retry_after = int(oldest_request + settings.rate_limit_window - now) + 1
                return True, max(1, retry_after)
            
            # Добавляем текущий запрос
            self._requests[user_id].append(now)
            return False, 0
    
    async def reset(self, user_id: int) -> None:
        """Сбросить историю запросов пользователя (для админа)."""
        async with self._lock:
            self._requests[user_id].clear()


# Глобальный экземпляр
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware для ограничения частоты запросов от пользователей.
    
    Блокирует запросы если пользователь превысил лимит.
    Администратор освобождён от ограничений.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Получаем пользователя
        user = None
        is_callback = False
        
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            is_callback = True
        elif isinstance(event, ErrorEvent):
            # Для ошибок пропускаем
            return await handler(event, data)
        
        # Если нет пользователя — пропускаем
        if not user:
            return await handler(event, data)
        
        # Администраторы освобождены от rate limiting
        if settings.is_admin(user.id):
            return await handler(event, data)
        
        # Проверяем лимит
        is_limited, retry_after = await rate_limiter.is_rate_limited(user.id)
        
        if is_limited:
            logger.warning(
                f"🚫 Rate Limit: Пользователь {user.id} (@{user.username}) "
                f"превысил лимит. Ждать {retry_after} сек."
            )
            
            # Отправляем уведомление (только для сообщений, не для callback)
            if isinstance(event, Message):
                try:
                    await event.answer(
                        text=RATE_LIMIT_MESSAGE.format(retry_after=retry_after),
                        show_alert=False,
                    )
                except Exception as e:
                    logger.debug(f"Не удалось отправить уведомление о rate limit: {e}")
            
            # Для callback отправляем answer
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer(
                        text=RATE_LIMIT_CALLBACK.format(retry_after=retry_after),
                        show_alert=True,
                    )
                except Exception as e:
                    logger.debug(f"Не удалось отправить уведомление о rate limit: {e}")
            
            # Прерываем обработку — хендлер не выполнится
            return None
        
        # Лимит не превышен — продолжаем
        return await handler(event, data)
