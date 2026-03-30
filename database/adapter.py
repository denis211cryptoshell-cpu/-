"""
Адаптер для унифицированной работы с SQLite и PostgreSQL.
"""

from typing import Any, List, Optional, Tuple
from database import DB_TYPE


class DatabaseAdapter:
    """
    Универсальный адаптер для работы с SQLite и PostgreSQL.
    
    Предоставляет единый интерфейс для всех сервисов.
    """

    def __init__(self, db):
        self.db = db
        self.db_type = DB_TYPE

    async def fetchone(self, query: str, *params) -> Optional[Any]:
        """
        Выполнить запрос и вернуть одну строку.
        
        Args:
            query: SQL-запрос
            *params: Параметры запроса
            
        Returns:
            Одна строка или None
        """
        if self.db_type == "sqlite":
            async with self.db.connection.cursor() as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchone()
        else:  # postgresql
            return await self.db.fetchone(query, *params)

    async def fetchall(self, query: str, *params) -> List[Any]:
        """
        Выполнить запрос и вернуть все строки.
        
        Args:
            query: SQL-запрос
            *params: Параметры запроса
            
        Returns:
            Список строк
        """
        if self.db_type == "sqlite":
            async with self.db.connection.cursor() as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchall()
        else:  # postgresql
            return await self.db.fetchall(query, *params)

    async def execute(self, query: str, *params) -> bool:
        """
        Выполнить SQL-запрос (INSERT, UPDATE, DELETE).
        
        Args:
            query: SQL-запрос
            *params: Параметры запроса
            
        Returns:
            True если успешно
        """
        try:
            if self.db_type == "sqlite":
                async with self.db.connection.cursor() as cursor:
                    await cursor.execute(query, params)
                    await self.db.connection.commit()
            else:  # postgresql
                await self.db.execute(query, *params)
            return True
        except Exception:
            return False

    async def executemany(self, query: str, params_list: List[Tuple]) -> bool:
        """
        Выполнить SQL-запрос для нескольких наборов параметров.
        
        Args:
            query: SQL-запрос
            params_list: Список наборов параметров
            
        Returns:
            True если успешно
        """
        try:
            if self.db_type == "sqlite":
                async with self.db.connection.cursor() as cursor:
                    await cursor.executemany(query, params_list)
                    await self.db.connection.commit()
            else:  # postgresql
                async with self.db.pool.acquire() as conn:
                    await conn.executemany(query, params_list)
            return True
        except Exception:
            return False


# Глобальный адаптер (создаётся после импорта db)
def get_db_adapter(db) -> DatabaseAdapter:
    """Получить адаптер для БД."""
    return DatabaseAdapter(db)
