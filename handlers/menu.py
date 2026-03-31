"""
Обработчики кнопок главного меню.
"""

import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message

from database import db_adapter
from services.content_manager import ContentManager, StatsManager, PhotoManager
from services.message_manager import MessageManager
from logger import logger

router = Router()

# Временное хранилище для debouncing (защита от быстрых нажатий)
# Формат: {user_id: {"section": section_key, "timestamp": time}}
_user_clicks = {}
DEBOUNCE_SECONDS = 1.5  # Задержка между одинаковыми нажатиями


@router.message()
async def handle_menu_button(
    message: Message,
    db,
    bot: Bot,
    content_manager: ContentManager,
    stats_manager: StatsManager,
    message_manager: MessageManager,
    photo_manager: PhotoManager,
):
    """
    Обработка нажатий на кнопки главного меню.

    Получает текст раздела из БД и отправляет пользователю (редактируя последнее сообщение).
    """
    button_text = message.text

    if not button_text:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    # Находим ключ раздела по названию кнопки
    section_key = await _get_section_by_label(db, button_text)

    if not section_key:
        # Неизвестная кнопка (например, "🔧 Админка" — обрабатывается в admin.py)
        return

    # Проверяем, не нажал ли пользователь ту же кнопку недавно (debouncing)
    current_time = asyncio.get_event_loop().time()
    if user_id in _user_clicks:
        last_click = _user_clicks[user_id]
        time_diff = current_time - last_click["timestamp"]

        # Если нажата та же кнопка и прошло меньше DEBOUNCE_SECONDS — игнорируем
        if last_click["section"] == section_key and time_diff < DEBOUNCE_SECONDS:
            logger.debug(
                f"Пользователь {user_id}: пропущено дублирующееся нажатие на {section_key} "
                f"(прошло {time_diff:.2f}с)"
            )
            return

    # Сохраняем время нажатия
    _user_clicks[user_id] = {
        "section": section_key,
        "timestamp": current_time,
    }

    # Проверяем, открыт ли уже этот раздел (защита от дублирования сообщений)
    last_section = await message_manager.get_last_section(user_id)

    if last_section == section_key:
        logger.debug(
            f"Пользователь {user_id}: раздел {section_key} уже открыт, пропускаем"
        )
        return

    # Обновляем статистику
    await stats_manager.increment_click(section_key)

    # Получаем контент из БД
    content = await content_manager.get_content(section_key)

    if content:
        # Сохраняем текущий раздел
        await message_manager.set_last_section(user_id, section_key)

        # Проверяем наличие фото главного меню
        main_menu_photo_id = await photo_manager.get_photo("main_menu")
        
        if main_menu_photo_id:
            # Отправляем фото с текстом и caption
            await message_manager.send_or_edit_photo(
                bot=bot,
                user_id=user_id,
                chat_id=chat_id,
                photo=main_menu_photo_id,
                caption=content,
                reply_markup=None,  # Клавиатура остаётся той же (reply keyboard)
                parse_mode="HTML",
            )
        else:
            # Если фото нет — отправляем текст
            await message_manager.send_or_edit(
                bot=bot,
                user_id=user_id,
                chat_id=chat_id,
                text=content,
                reply_markup=None,
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
