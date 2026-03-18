"""
Подключение к SQLite и управление соединениями (aiosqlite).
"""

import aiosqlite
from pathlib import Path

from config import settings
from database.models import create_tables, insert_defaults
from logger import logger


class Database:
    """
    Менеджер подключений к SQLite.
    
    Использует одно соединение на всё приложение (достаточно для бота).
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection: aiosqlite.Connection | None = None

    @property
    def connection(self) -> aiosqlite.Connection:
        """Получить активное соединение."""
        if self._connection is None:
            raise RuntimeError("База данных не инициализирована!")
        return self._connection

    async def connect(self) -> None:
        """
        Инициализировать подключение к БД.
        
        Создаёт директорию для БД если не существует.
        """
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection = await aiosqlite.connect(self.db_path)
        await self._connection.execute("PRAGMA journal_mode=WAL;")
        await self._connection.commit()

        logger.info(f"Подключение к БД: {self.db_path}")

    async def disconnect(self) -> None:
        """Закрыть подключение к БД."""
        if self._connection:
            await self._connection.close()
            logger.info("Подключение к БД закрыто")

    async def init_tables(self) -> None:
        """
        Создать таблицы и заполнить дефолтными данными.
        
        Вызывается один раз при первом запуске.
        """
        async with self._connection.cursor() as cursor:
            await create_tables(cursor)
            await insert_defaults(cursor)
            await self._connection.commit()

        logger.info("Таблицы БД созданы и заполнены")

    async def get_cursor(self):
        """
        Получить курсор для выполнения запросов.
        
        Возвращает контекстный менеджер для безопасной работы.
        """
        return self._connection.cursor()


# Глобальный экземпляр БД
db = Database(settings.database_path)


async def get_db() -> Database:
    """Получить экземпляр БД (для внедрения в хендлеры)."""
    return db


async def init_db() -> None:
    """Инициализировать БД (подключение + таблицы)."""
    await db.connect()
    await db.init_tables()
