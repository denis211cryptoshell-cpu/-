"""
Абстрактный интерфейс и реализации кэша для Telegram Bot.

Поддерживает два бэкенда:
- LocalCacheBackend — In-Memory кэш (по умолчанию)
- RedisCacheBackend — Redis кэш (для масштабирования и персистентности)

Выбор бэкенда происходит через config.py (CACHE_BACKEND + REDIS_URL).
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, Union

from loguru import logger


# ============================================================================
# Абстрактный базовый класс
# ============================================================================

class CacheBackend(ABC):
    """Абстрактный интерфейс кэша."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Установить значение в кэш.

        Args:
            key: Ключ кэша.
            value: Значение (сериализуется автоматически).
            ttl: Время жизни в секундах (None = без ограничения).
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Удалить значение из кэша."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Очистить весь кэш."""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """
        Очистить просроченные записи.

        Returns:
            Количество удалённых записей.
        """
        pass

    @abstractmethod
    async def stats(self) -> Dict[str, int]:
        """Получить статистику кэша."""
        pass


# ============================================================================
# Local Cache Backend (In-Memory)
# ============================================================================

class LocalCacheBackend(CacheBackend):
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
                    logger.debug(f"[LocalCache] GET {key} -> HIT")
                    return value
                else:
                    del self._cache[key]
                    logger.debug(f"[LocalCache] GET {key} -> EXPIRED")
            logger.debug(f"[LocalCache] GET {key} -> MISS")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Установить значение в кэш."""
        async with self._lock:
            # TTL по умолчанию 5 минут
            if ttl is None:
                ttl = 300
            
            expires_at = time.time() + ttl
            self._cache[key] = (value, expires_at)
            logger.debug(f"[LocalCache] SET {key} (TTL: {ttl}s)")

    async def delete(self, key: str) -> None:
        """Удалить значение из кэша."""
        async with self._lock:
            self._cache.pop(key, None)
            logger.debug(f"[LocalCache] DELETE {key}")

    async def clear(self) -> None:
        """Очистить весь кэш."""
        async with self._lock:
            self._cache.clear()
            logger.info("[LocalCache] CLEAR — весь кэш очищен")

    async def cleanup_expired(self) -> int:
        """Очистить просроченные записи."""
        async with self._lock:
            now = time.time()
            expired_keys = [
                key for key, (_, expires_at) in self._cache.items()
                if now >= expires_at
            ]
            for key in expired_keys:
                del self._cache[key]
            if expired_keys:
                logger.debug(f"[LocalCache] CLEANUP — удалено {len(expired_keys)} записей")
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


# ============================================================================
# Redis Cache Backend
# ============================================================================

class RedisCacheBackend(CacheBackend):
    """
    Redis кэш с TTL.

    Требует установленный пакет redis и запущенный Redis сервер.
    Сериализует данные в JSON (безопасно).
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0", prefix: str = "bot_cache"):
        """
        Инициализация Redis кэша.

        Args:
            redis_url: URL подключения к Redis (redis://host:port/db).
            prefix: Префикс для всех ключей (для изоляции от других приложений).
        """
        self._redis_url = redis_url
        self._prefix = prefix
        self._redis: Optional[Any] = None
        self._lock = asyncio.Lock()
        self._connected = False

    async def connect(self) -> None:
        """Подключение к Redis."""
        if self._connected:
            return

        try:
            import redis.asyncio as redis
        except ImportError:
            logger.error("[RedisCache] redis пакет не установлен! Установите: pip install redis")
            raise

        try:
            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis.ping()
            self._connected = True
            logger.info(f"[RedisCache] Подключено к Redis: {self._redis_url}")
        except Exception as e:
            logger.error(f"[RedisCache] Ошибка подключения к Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Отключение от Redis."""
        if self._redis and self._connected:
            await self._redis.close()
            self._connected = False
            logger.info("[RedisCache] Отключено от Redis")

    def _make_key(self, key: str) -> str:
        """Создать полный ключ с префиксом."""
        return f"{self._prefix}:{key}"

    def _serialize(self, value: Any) -> str:
        """Сериализация значения в JSON."""
        return json.dumps(value, ensure_ascii=False, default=str)

    def _deserialize(self, data: Optional[str]) -> Optional[Any]:
        """Десериализация значения из JSON."""
        if data is None:
            return None
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"[RedisCache] Ошибка десериализации ключа: {data[:50]}...")
            return None

    async def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша."""
        if not self._connected:
            await self.connect()

        full_key = self._make_key(key)
        try:
            data = await self._redis.get(full_key)
            value = self._deserialize(data)
            logger.debug(f"[RedisCache] GET {key} -> {'HIT' if value is not None else 'MISS'}")
            return value
        except Exception as e:
            logger.error(f"[RedisCache] Ошибка GET {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Установить значение в кэш."""
        if not self._connected:
            await self.connect()

        full_key = self._make_key(key)
        serialized = self._serialize(value)

        try:
            if ttl:
                await self._redis.setex(full_key, ttl, serialized)
            else:
                await self._redis.set(full_key, serialized)
            logger.debug(f"[RedisCache] SET {key} (TTL: {ttl or 'None'}s)")
        except Exception as e:
            logger.error(f"[RedisCache] Ошибка SET {key}: {e}")

    async def delete(self, key: str) -> None:
        """Удалить значение из кэша."""
        if not self._connected:
            await self.connect()

        full_key = self._make_key(key)
        try:
            await self._redis.delete(full_key)
            logger.debug(f"[RedisCache] DELETE {key}")
        except Exception as e:
            logger.error(f"[RedisCache] Ошибка DELETE {key}: {e}")

    async def clear(self) -> None:
        """Очистить весь кэш (удалить все ключи с префиксом)."""
        if not self._connected:
            await self.connect()

        try:
            pattern = f"{self._prefix}:*"
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self._redis.delete(*keys)
                    deleted_count += len(keys)
                if cursor == 0:
                    break

            logger.info(f"[RedisCache] CLEAR — удалено {deleted_count} записей")
        except Exception as e:
            logger.error(f"[RedisCache] Ошибка CLEAR: {e}")

    async def cleanup_expired(self) -> int:
        """
        Очистка просроченных записей.

        В Redis TTL обрабатывается автоматически, поэтому эта функция
        только возвращает 0 (очистка не требуется).
        """
        return 0

    async def stats(self) -> Dict[str, int]:
        """Получить статистику кэша."""
        if not self._connected:
            await self.connect()

        try:
            pattern = f"{self._prefix}:*"
            cursor = 0
            total_keys = 0

            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                total_keys += len(keys)
                if cursor == 0:
                    break

            # Redis не хранит информацию о просроченных ключах после их удаления
            return {
                "total_keys": total_keys,
                "valid_keys": total_keys,
                "expired_keys": 0
            }
        except Exception as e:
            logger.error(f"[RedisCache] Ошибка получения статистики: {e}")
            return {
                "total_keys": 0,
                "valid_keys": 0,
                "expired_keys": 0
            }


# ============================================================================
# Cache Factory
# ============================================================================

class CacheFactory:
    """Фабрика для создания кэша."""

    @staticmethod
    def create(backend: str = "local", **kwargs) -> CacheBackend:
        """
        Создать экземпляр кэша.

        Args:
            backend: Тип бэкенда ("local" или "redis").
            **kwargs: Дополнительные параметры для бэкенда.

        Returns:
            Экземпляр CacheBackend.
        """
        if backend == "redis":
            return RedisCacheBackend(
                redis_url=kwargs.get("redis_url", "redis://localhost:6379/0"),
                prefix=kwargs.get("prefix", "bot_cache"),
            )
        else:
            return LocalCacheBackend()


# ============================================================================
# Глобальный экземпляр (будет инициализирован в init_cache)
# ============================================================================

_cache: Optional[CacheBackend] = None


def init_cache(backend: str = "local", **kwargs) -> CacheBackend:
    """
    Инициализировать глобальный кэш.

    Вызывается один раз при старте бота.

    Args:
        backend: Тип бэкенда ("local" или "redis").
        **kwargs: Дополнительные параметры.

    Returns:
        Глобальный экземпляр кэша.
    """
    global _cache
    _cache = CacheFactory.create(backend, **kwargs)
    logger.info(f"[Cache] Инициализирован бэкенд: {backend}")
    return _cache


def get_cache() -> CacheBackend:
    """Получить глобальный кэш."""
    global _cache
    if _cache is None:
        logger.warning("[Cache] Кэш не инициализирован! Использую LocalCacheBackend по умолчанию.")
        _cache = LocalCacheBackend()
    return _cache


# ============================================================================
# Декоратор для кэширования
# ============================================================================

def cached(ttl: int = 300, prefix: str = ""):
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
            cache_backend = get_cache()

            # Формируем ключ кэша из аргументов
            key_parts = [prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args if isinstance(arg, (int, str)))
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()) if isinstance(v, (int, str)))
            cache_key = ":".join(key_parts)

            # Проверяем кэш
            cached_value = await cache_backend.get(cache_key)
            if cached_value is not None:
                logger.debug(f"[cached] {cache_key} -> из кэша")
                return cached_value

            # Вызываем функцию и сохраняем результат в кэш
            result = await func(*args, **kwargs)
            if result is not None:
                await cache_backend.set(cache_key, result, ttl)
                logger.debug(f"[cached] {cache_key} -> сохранено в кэш (TTL: {ttl}s)")
            return result

        return wrapper
    return decorator


# ============================================================================
# Утилиты
# ============================================================================

async def get_cache_stats() -> str:
    """Получить статистику кэша в виде строки."""
    cache_backend = get_cache()
    stats = await cache_backend.stats()
    backend_name = type(cache_backend).__name__
    return (
        f"📊 Статистика кэша ({backend_name}):\n"
        f"Всего ключей: {stats['total_keys']}\n"
        f"Активных: {stats['valid_keys']}\n"
        f"Просрочено: {stats['expired_keys']}"
    )
