"""
Миграция 002: Добавление приветствия (greeting) в таблицу content.
"""

from logger import logger


async def migrate_002_add_greeting(cursor) -> None:
    """
    Добавить запись приветствия в таблицу content.
    """
    # Проверяем существование записи
    await cursor.execute(
        "SELECT id FROM content WHERE section = ?",
        ("greeting",),
    )
    result = await cursor.fetchone()

    if result:
        logger.info("Запись 'greeting' уже существует в content")
        return

    # Добавляем дефолтное приветствие
    default_greeting = "👋 <b>Привет! Я бот-визитка разработчика.</b>\n\nВыберите раздел в меню ниже, чтобы узнать больше обо мне и моих услугах."

    await cursor.execute(
        "INSERT INTO content (section, text) VALUES (?, ?)",
        ("greeting", default_greeting),
    )

    logger.info("Добавлена запись 'greeting' в таблицу content")
