"""
Миграция 003: Добавление колонки last_section в таблицу users
для отслеживания текущего открытого раздела.

Это предотвращает дублирование сообщений при быстрых нажатиях на одну кнопку.
"""

from logger import logger


async def migrate_003_add_last_section(cursor) -> bool:
    """
    Добавить колонку last_section в таблицу users.

    Args:
        cursor: Курсор БД

    Returns:
        True если миграция применена, False если уже существует
    """
    try:
        # Проверяем, существует ли колонка
        await cursor.execute(
            "PRAGMA table_info(users)"
        )
        columns = [col[1] for col in await cursor.fetchall()]

        if "last_section" in columns:
            logger.info("Миграция 003: колонка last_section уже существует")
            return False

        # Добавляем колонку
        await cursor.execute(
            "ALTER TABLE users ADD COLUMN last_section TEXT"
        )
        logger.info("Миграция 003: добавлена колонка last_section в таблицу users")
        return True

    except Exception as e:
        logger.error(f"Миграция 003: ошибка при добавлении last_section: {e}")
        raise
