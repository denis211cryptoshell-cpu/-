"""
Миграция 004: Добавление таблицы photos для хранения фото
(приветствие и главное меню).
"""

from logger import logger


async def migrate_004_add_photos_table(cursor) -> bool:
    """
    Добавить таблицу photos для хранения фото.

    Args:
        cursor: Курсор БД

    Returns:
        True если миграция применена, False если уже существует
    """
    try:
        # Проверяем, существует ли таблица photos
        await cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='photos'"
        )
        result = await cursor.fetchone()

        if result:
            logger.info("Миграция 004: таблица photos уже существует")
            return False

        # Создаём таблицу photos
        await cursor.execute("""
            CREATE TABLE photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_type TEXT UNIQUE NOT NULL,
                file_id TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Создаём индекс
        await cursor.execute(
            "CREATE INDEX idx_photos_type ON photos(photo_type)"
        )

        logger.info("Миграция 004: добавлена таблица photos")
        return True

    except Exception as e:
        logger.error(f"Миграция 004: ошибка при создании таблицы photos: {e}")
        raise
