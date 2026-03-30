"""
In-Memory кэш с TTL для Telegram Bot API.

Использование:
    @cache(ttl=300)  # 5 минут
    async def get_user_profile(user_id: int):
        return await bot.get_user_profile_photos(user_id)
"""

import asyncio
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple


class Cache:
    """In-Memory кэш с TTL."""

    def __init__(self):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша."""
        async with self._lock:
            if key in self._cache:
                value, expires_at = self._cache[key]
                if time.time() < expires_at:
                    return value
                else:
                    del self._cache[key]
            return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Установить значение в кэш."""
        async with self._lock:
            expires_at = time.time() + ttl
            self._cache[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        """Удалить значение из кэша."""
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        """Очистить весь кэш."""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self) -> int:
        """
        Очистить просроченные записи.
        
        Returns:
            Количество удалённых записей.
        """
        async with self._lock:
            now = time.time()
            expired_keys = [
                key for key, (_, expires_at) in self._cache.items()
                if now >= expires_at
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    async def stats(self) -> Dict[str, int]:
        """Получить статистику кэша."""
        async with self._lock:
            now = time.time()
            total = len(self._cache)
            valid = sum(
                1 for _, expires_at in self._cache.values()
                if now < expires_at
            )
            return {
                "total_keys": total,
                "valid_keys": valid,
                "expired_keys": total - valid
            }


# Глобальный экземпляр кэша
cache = Cache()


def cached(ttl: int, prefix: str = ""):
    """
    Декоратор для кэширования результатов асинхронных функций.

    Args:
        ttl: Время жизни кэша в секундах.
        prefix: Префикс для ключа кэша.

    Returns:
        Декорированная функция.

    Пример:
        @cached(ttl=300, prefix="user")
        async def get_user_profile(user_id: int):
            return await bot.get_user_profile_photos(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Формируем ключ кэша из аргументов
            key_parts = [prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args if isinstance(arg, (int, str)))
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()) if isinstance(v, (int, str)))
            cache_key = ":".join(key_parts)

            # Проверяем кэш
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Вызываем функцию и сохраняем результат в кэш
            result = await func(*args, **kwargs)
            if result is not None:
                await cache.set(cache_key, result, ttl)
            return result

        return wrapper
    return decorator


async def get_cache_stats() -> str:
    """Получить статистику кэша в виде строки."""
    stats = await cache.stats()
    return (
        f"📊 Статистика кэша:\n"
        f"Всего ключей: {stats['total_keys']}\n"
        f"Активных: {stats['valid_keys']}\n"
        f"Просрочено: {stats['expired_keys']}"
    )
