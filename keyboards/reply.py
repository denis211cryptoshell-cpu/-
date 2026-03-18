"""
Reply-клавиатуры (главное меню).
Динамическая генерация из БД.
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


async def get_main_menu(db) -> ReplyKeyboardMarkup:
    """
    Построить главное меню из БД.

    Только активные кнопки отображаются пользователю.
    Кнопка админки показывается только для админа (проверка в хендлере).
    """
    async with db.connection.cursor() as cursor:
        await cursor.execute(
            "SELECT label FROM buttons WHERE is_active = 1 ORDER BY id"
        )
        rows = await cursor.fetchall()

    # Формируем кнопки по 2 в ряд
    keyboard: list[list[KeyboardButton]] = []
    row: list[KeyboardButton] = []

    for (label,) in rows:
        row.append(KeyboardButton(text=label))
        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    # Кнопка админки (всегда в конце)
    keyboard.append([KeyboardButton(text="🔧 Админка")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )
