"""
Система миграций базы данных.
Управление версиями схемы БД.
"""

from pathlib import Path
from logger import logger


# Список миграций в порядке применения
MIGRATIONS = [
    {
        "name": "001_add_last_message_id",
        "description": "Добавление колонки last_message_id в таблицу users",
    },
    {
        "name": "002_add_greeting",
        "description": "Добавление приветствия (greeting) в таблицу content",
    },
    {
        "name": "003_add_last_section",
        "description": "Добавление колонки last_section в таблицу users для защиты от дублирования",
    },
]


async def get_current_version(cursor) -> int:
    """
    Получить текущую версию схемы БД.

    Args:
        cursor: Курсор БД

    Returns:
        Номер версии (0 если таблица migrations не существует)
    """
    # Проверяем существование таблицы migrations
    await cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'"
    )
    result = await cursor.fetchone()

    if not result:
        return 0

    # Получаем последнюю применённую миграцию
    await cursor.execute("SELECT version FROM migrations ORDER BY version DESC LIMIT 1")
    result = await cursor.fetchone()
    return result[0] if result else 0


async def apply_migration(cursor, version: int, migration_name: str) -> None:
    """
    Применить одну миграцию.

    Args:
        cursor: Курсор БД
        version: Номер версии миграции
        migration_name: Имя файла миграции
    """
    # Импортируем миграцию динамически
    module = __import__(
        f"database.migrations.{migration_name}",
        fromlist=["migrate"],
    )

    # Получаем функцию миграции по имени
    func_name = f"migrate_{migration_name}"
    if not hasattr(module, func_name):
        # Пробуем альтернативное имя функции
        func_name = f"migrate_{migration_name.replace('00', '')}"

    migrate_func = getattr(module, func_name)

    # Применяем миграцию
    await migrate_func(cursor)

    # Создаём таблицу migrations если не существует
    await cursor.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Записываем информацию о применённой миграции
    await cursor.execute(
        "INSERT INTO migrations (version, name) VALUES (?, ?)",
        (version, migration_name),
    )

    logger.info(f"Применена миграция v{version}: {migration_name}")


async def run_migrations(db) -> None:
    """
    Применить все ожидающие миграции.

    Args:
        db: Экземпляр подключения к БД
    """
    async with db.connection.cursor() as cursor:
        current_version = await get_current_version(cursor)
        target_version = len(MIGRATIONS)

        if current_version >= target_version:
<<<<<<< HEAD
            logger.info(f"База данных актуальна (версия схемы: v{current_version})")
            return

        logger.info(
            f"Применение миграций: с v{current_version} до v{target_version}",
=======
            logger.info("База данных актуальна (версия схемы: %d)", current_version)
            return

        logger.info(
            "Применение миграций: с v%d до v%d",
            current_version,
            target_version,
>>>>>>> 02571aafde88a33b7b0848222a3f85bbed954070
        )

        # Применяем миграции по очереди
        for i in range(current_version, target_version):
            migration = MIGRATIONS[i]
            await apply_migration(cursor, i + 1, migration["name"])

        await db.connection.commit()

    logger.info("Все миграции успешно применены")
