"""
Утилиты для управления сообщениями (UX/UI).

Принципы:
- Удалять старые сообщения при переходе в новую сцену
- Редактировать сообщения в пределах одного контекста
- Оставлять новые сообщения для ошибок и важных уведомлений
"""

from aiogram.types import Message, CallbackQuery
from loguru import logger


async def delete_message(message: Message) -> bool:
    """
    Удалить сообщение безопасно.
    
    Args:
        message: Сообщение для удаления
    
    Returns:
        True если успешно, False если не удалось
    """
    try:
        await message.delete()
        return True
    except Exception as e:
        logger.debug(f"Не удалось удалить сообщение: {e}")
        return False


async def replace_message(
    message: Message,
    text: str,
    parse_mode: str = "HTML",
    reply_markup=None,
) -> None:
    """
    Заменить сообщение: удалить старое и отправить новое.
    
    Используется при переходе в новую сцену (например, кнопка меню → раздел).
    
    Args:
        message: Старое сообщение (будет удалено)
        text: Текст нового сообщения
        parse_mode: Режим разметки
        reply_markup: Клавиатура
    """
    await delete_message(message)
    await message.answer(
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
    )


async def edit_message(
    callback: CallbackQuery,
    text: str,
    parse_mode: str = "HTML",
    reply_markup=None,
) -> None:
    """
    Отредактировать сообщение callback.
    
    Используется в пределах одного контекста (админка, навигация).
    
    Args:
        callback: CallbackQuery для редактирования
        text: Новый текст
        parse_mode: Режим разметки
        reply_markup: Новая клавиатура
    """
    try:
        await callback.message.edit_message_text(
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
    except Exception as e:
        # Если сообщение нельзя отредактировать — удаляем и отправляем новое
        logger.debug(f"Не удалось отредактировать сообщение: {e}")
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )


def is_error_message(text: str) -> bool:
    """
    Проверить, является ли сообщение ошибкой.
    
    Args:
        text: Текст сообщения
    
    Returns:
        True если содержит маркеры ошибки
    """
    error_markers = ["❌", "Ошибка", "Error", "⚠️"]
    return any(marker in text for marker in error_markers)
