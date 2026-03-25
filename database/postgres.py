"""
Подключение к PostgreSQL (Supabase, Neon и др.).
Использует asyncpg для асинхронной работы.
"""

import asyncpg
from typing import Optional

from config import settings
from database.models import CREATE_TABLES_POSTGRES_SQL, INSERT_DEFAULTS_POSTGRES_SQL
from logger import logger


class PostgresDatabase:
    """
    Менеджер подключений к PostgreSQL.
    
    Использует пул соединений для производительности.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None

    @property
    def pool(self) -> asyncpg.Pool:
        """Получить пул соединений."""
        if self._pool is None:
            raise RuntimeError("База данных не инициализирована!")
        return self._pool

    async def connect(self) -> None:
        """
        Инициализировать подключение к БД.
        
        Создаёт пул из 10 соединений (оптимально для бота).
        """
        try:
            self._pool = await asyncpg.create_pool(
                dsn=self.database_url,
                min_size=5,
                max_size=10,
                command_timeout=60,
            )
            logger.info(f"Подключение к PostgreSQL: {self.database_url[:50]}...")
        except Exception as e:
            logger.error(f"Ошибка подключения к PostgreSQL: {e}")
            raise

    async def disconnect(self) -> None:
        """Закрыть пул соединений."""
        if self._pool:
            await self._pool.close()
            logger.info("Подключение к PostgreSQL закрыто")

    async def init_tables(self) -> None:
        """
        Создать таблицы и заполнить дефолтными данными.
        
        Вызывается один раз при первом запуске.
        """
        async with self._pool.acquire() as conn:
            # Создаём таблицы
            await conn.execute(CREATE_TABLES_POSTGRES_SQL)
            
            # Вставляем дефолтные данные
            await conn.execute(INSERT_DEFAULTS_POSTGRES_SQL)

        logger.info("Таблицы БД созданы и заполнены")

    async def execute(self, query: str, *args, fetch: bool = False):
        """
        Выполнить SQL-запрос.
        
        Args:
            query: SQL-запрос
            *args: Параметры запроса
            fetch: Если True — вернуть результаты
            
        Returns:
            Результаты или None
        """
        async with self._pool.acquire() as conn:
            if fetch:
                return await conn.fetch(query, *args)
            else:
                return await conn.execute(query, *args)

    async def fetchone(self, query: str, *args):
        """Выполнить запрос и вернуть одну строку."""
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchall(self, query: str, *args):
        """Выполнить запрос и вернуть все строки."""
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)


# Глобальный экземпляр БД
db = PostgresDatabase(settings.database_url) if settings.database_url else None


async def get_db():
    """Получить экземпляр БД."""
    return db


async def init_db():
    """Инициализировать БД (подключение + таблицы)."""
    if db:
        await db.connect()
        await db.init_tables()
