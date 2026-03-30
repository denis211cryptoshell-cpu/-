"""
Миграция: добавление колонки last_message_id в таблицу users.
Версия: 001
Дата: 2026-03-27
Описание: Добавление поля для хранения ID последнего сообщения бота
"""

from logger import logger


async def migrate_001_add_last_message_id(cursor, db_type: str = "sqlite") -> None:
    """
    Добавить колонку last_message_id в таблицу users.

    Args:
        cursor: Курсор БД
        db_type: Тип БД (sqlite или postgres)
    """
    if db_type == "sqlite":
        # SQLite: добавляем колонку
        await cursor.execute(
            "ALTER TABLE users ADD COLUMN last_message_id INTEGER DEFAULT NULL"
        )
    else:
        # PostgreSQL: добавляем колонку
        await cursor.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_message_id BIGINT DEFAULT NULL"
        )

    logger.info("Миграция 001: добавлена колонка last_message_id в таблицу users")


async def rollback_001_remove_last_message_id(cursor, db_type: str = "sqlite") -> None:
    """
    Откат миграции: удаление колонки last_message_id.

    Внимание: SQLite не поддерживает DROP COLUMN до версии 3.35.0
    Для старых версий потребуется пересоздание таблицы.
    """
    if db_type == "sqlite":
        # Проверяем версию SQLite
        await cursor.execute("SELECT sqlite_version()")
        version = await cursor.fetchone()
        version_tuple = tuple(map(int, version[0].split(".")))

        if version_tuple >= (3, 35, 0):
            await cursor.execute("ALTER TABLE users DROP COLUMN last_message_id")
        else:
            # Для старых версий SQLite — предупреждение
            logger.warning(
                "SQLite < 3.35.0 не поддерживает DROP COLUMN. "
                "Колонка last_message_id будет удалена при следующем создании таблицы."
            )
            return
    else:
        await cursor.execute("ALTER TABLE users DROP COLUMN last_message_id")

    logger.info("Откат миграции 001: удалена колонка last_message_id")
