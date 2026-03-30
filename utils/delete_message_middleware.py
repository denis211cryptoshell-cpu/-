"""
Middleware для удаления сообщений от пользователей.

При нажатии на reply-кнопку текст кнопки отправляется в чат.
Этот middleware удаляет такие сообщения чтобы не засорять историю.

Логика:
- Админ: сообщения НЕ удаляются (нужно для редактирования контента в админке)
- Не админ: сообщения удаляются (чисто в чате)
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from config import settings
from logger import logger


class DeleteUserMessageMiddleware(BaseMiddleware):
    """
    Middleware для удаления сообщений пользователей после нажатия кнопок.

    Работает только для сообщений с текстом (кнопки).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Обрабатываем только сообщения
        if isinstance(event, Message):
            # Проверяем, есть ли текст (нажатие кнопки)
            if event.text:
                user_id = event.from_user.id
                message_id = event.message_id
                text = event.text

                # Проверяем, является ли пользователь админом
                is_admin = settings.is_admin(user_id)

                # Пропускаем команды — не удаляем
                if text.startswith('/'):
                    logger.debug(f"Пропуск команды {message_id}: {text}")
                    return await handler(event, data)
                
                # Пропускаем кнопки админки
                elif text in ["🔧 Админка", "🔙 Назад", "✏️ Редактировать", "📢 Каналы", 
                              "👤 Кнопки", "📨 Рассылка", "📊 Статистика", "⚙️ Контент",
                              "🔙 В админку", "💾 Сохранить", "❌ Отмена", "👁️ Просмотреть"]:
                    logger.debug(f"Пропуск кнопки админки: '{text}'")
                    return await handler(event, data)
                
                # Админ — НЕ удаляем сообщение (нужно для редактирования контента)
                elif is_admin:
                    logger.debug(f"Пропуск сообщения от админа {user_id}: '{text}'")
                    return await handler(event, data)
                
                # Не админ — удаляем сообщение
                else:
                    logger.info(f"🗑️ Удаление кнопки: '{text}'")

                # Сначала выполняем хендлер (чтобы бот ответил)
                try:
                    result = await handler(event, data)
                except Exception as e:
                    # Если хендлер упал — всё равно пытаемся удалить сообщение
                    logger.error(f"Ошибка в хендлере: {e}")
                    result = None

                # Затем удаляем сообщение пользователя
                try:
                    await event.delete()
                    logger.debug(f"✅ Сообщение {message_id} удалено")
                except Exception as e:
                    # Не критично если не удалось удалить
                    logger.debug(f"Не удалось удалить сообщение {message_id}: {e}")

                return result

        # Для всех остальных событий — просто пропускаем
        return await handler(event, data)
