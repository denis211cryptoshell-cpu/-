"""
Миграция 005: Добавление колонок button_label и last_clicked в таблицу stats.
"""

from aiosqlite import Cursor
from logger import logger


async def migrate_005_add_last_seen_stats(cursor: Cursor) -> None:
    """
    Добавить колонки button_label и last_clicked в таблицу stats.
    """
    # Проверяем, существует ли уже колонка button_label
    await cursor.execute("PRAGMA table_info(stats)")
    columns = await cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    # Добавляем колонку button_label если не существует
    if 'button_label' not in column_names:
        await cursor.execute("""
            ALTER TABLE stats ADD COLUMN button_label TEXT NOT NULL DEFAULT ''
        """)
        logger.info("Добавлена колонка button_label в таблицу stats")
    
    # Добавляем колонку last_clicked если не существует
    if 'last_clicked' not in column_names:
        await cursor.execute("""
            ALTER TABLE stats ADD COLUMN last_clicked DATETIME DEFAULT CURRENT_TIMESTAMP
        """)
        logger.info("Добавлена колонка last_clicked в таблицу stats")
    
    # Обновляем button_label из таблицы buttons
    await cursor.execute("""
        UPDATE stats
        SET button_label = (
            SELECT label FROM buttons WHERE buttons.name = stats.button_name
        )
        WHERE button_label = '' OR button_label IS NULL
    """)
    
    logger.info("Обновлены button_label из таблицы buttons")
