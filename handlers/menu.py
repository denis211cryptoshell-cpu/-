"""
Обработчики кнопок главного меню.
"""

from aiogram import Router, F, Bot
from aiogram.types import Message

from database import db_adapter
from services.content_manager import ContentManager, StatsManager
from services.message_manager import MessageManager
from logger import logger

router = Router()


@router.message()
async def handle_menu_button(
    message: Message,
    db,
    bot: Bot,
    content_manager: ContentManager,
    stats_manager: StatsManager,
    message_manager: MessageManager,
):
    """
    Обработка нажатий на кнопки главного меню.

    Получает текст раздела из БД и отправляет пользователю (редактируя последнее сообщение).
    """
    button_text = message.text

    if not button_text:
        return

    # Находим ключ раздела по названию кнопки
    section_key = await _get_section_by_label(db, button_text)

    if not section_key:
        # Неизвестная кнопка (например, "🔧 Админка" — обрабатывается в admin.py)
        return

    # Обновляем статистику
    await stats_manager.increment_click(section_key)

    # Получаем контент из БД
    content = await content_manager.get_content(section_key)

    user_id = message.from_user.id
    chat_id = message.chat.id

    if content:
        await message_manager.send_or_edit(
            bot=bot,
            user_id=user_id,
            chat_id=chat_id,
            text=content,
            reply_markup=None,  # Клавиатура остаётся той же (reply keyboard)
            parse_mode="HTML",
        )
        logger.debug(f"Пользователь {user_id} открыл раздел {section_key}")
    else:
        await message_manager.send_or_edit(
            bot=bot,
            user_id=user_id,
            chat_id=chat_id,
            text="⚠️ Раздел временно недоступен",
            reply_markup=None,
            parse_mode="HTML",
        )
        logger.warning(f"Раздел {section_key} не найден в БД")


async def _get_section_by_label(db, label: str) -> str | None:
    """
    Найти ключ раздела по видимому названию кнопки.

    Args:
        db: Экземпляр БД
        label: Текст кнопки от пользователя

    Returns:
        Ключ раздела или None
    """
    row = await db_adapter.fetchone(
        "SELECT name FROM buttons WHERE label = ?",
        label,
    )
    return row[0] if row else None
