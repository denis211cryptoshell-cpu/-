"""
Сервис управления сообщениями.
Хранение message_id последнего сообщения бота для каждого пользователя.
"""

from aiogram import Bot
from aiogram.types import Message
from database import db_adapter


class MessageManager:
    """Управление последними сообщениями бота."""

    async def get_last_message_id(self, user_id: int) -> int | None:
        """
        Получить ID последнего сообщения бота пользователю.

        Args:
            user_id: Telegram ID пользователя

        Returns:
            message_id или None если сообщений ещё не было
        """
        row = await db_adapter.fetchone(
            "SELECT last_message_id FROM users WHERE telegram_id = ?",
            user_id,
        )
        return row[0] if row else None

    async def set_last_message_id(self, user_id: int, message_id: int) -> None:
        """
        Сохранить ID последнего сообщения бота.

        Args:
            user_id: Telegram ID пользователя
            message_id: ID сообщения в Telegram
        """
        await db_adapter.execute(
            "UPDATE users SET last_message_id = ? WHERE telegram_id = ?",
            message_id,
            user_id,
        )

    async def clear_last_message_id(self, user_id: int) -> None:
        """
        Очистить ID последнего сообщения (например, при выходе из меню).

        Args:
            user_id: Telegram ID пользователя
        """
        await db_adapter.execute(
            "UPDATE users SET last_message_id = NULL WHERE telegram_id = ?",
            user_id,
        )

    async def send_or_edit(
        self,
        bot: Bot,
        user_id: int,
        chat_id: int,
        text: str,
        reply_markup=None,
        parse_mode: str = "HTML",
    ) -> Message:
        """
        Отправить новое сообщение или отредактировать последнее.

        Args:
            bot: Экземпляр бота
            user_id: Telegram ID пользователя (для сохранения message_id)
            chat_id: ID чата для отправки
            text: Текст сообщения
            reply_markup: Inline-клавиатура (опционально).
                          ReplyKeyboardMarkup не поддерживается при редактировании!
            parse_mode: Режим парсинга (по умолчанию HTML)

        Returns:
            Отправленное/отредактированное сообщение
        """
        last_message_id = await self.get_last_message_id(user_id)

        if last_message_id:
            # Пытаемся отредактировать существующее сообщение
            try:
                # При редактировании НЕ передаём reply_markup если это ReplyKeyboardMarkup
                # Telegram не позволяет изменить reply-клавиатуру через edit_message_text
                edit_kwargs = {
                    "chat_id": chat_id,
                    "message_id": last_message_id,
                    "text": text,
                    "parse_mode": parse_mode,
                }
                
                # Передаём reply_markup только если это inline-клавиатура
                if reply_markup is not None:
                    from aiogram.types import InlineKeyboardMarkup
                    if isinstance(reply_markup, InlineKeyboardMarkup):
                        edit_kwargs["reply_markup"] = reply_markup

                await bot.edit_message_text(**edit_kwargs)
                # message_id не меняем при редактировании
            except Exception as e:
                # Если редактирование не удалось — сбрасываем last_message_id
                # и отправляем новое сообщение
                from logger import logger
                logger.debug(f"Редактирование не удалось (msg {last_message_id}): {e}")
                
                # Сбрасываем last_message_id чтобы следующее сообщение было новым
                await self.clear_last_message_id(user_id)
                
                # Отправляем новое сообщение
                msg = await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
                await self.set_last_message_id(user_id, msg.message_id)
                return msg
        else:
            # Отправляем новое сообщение
            msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            await self.set_last_message_id(user_id, msg.message_id)
            return msg

        # Возвращаем заглушку — при редактировании объект Message не возвращается
        # Создаём псевдо-объект для совместимости
        class FakeMessage:
            def __init__(self, chat_id, message_id, text):
                self.chat_id = chat_id
                self.message_id = message_id
                self.text = text
                self.from_user = None

        return FakeMessage(chat_id, last_message_id, text)
