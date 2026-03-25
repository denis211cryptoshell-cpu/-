"""
Утилиты для работы с ссылками Telegram.
"""

import re
from typing import Optional
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from logger import logger


async def get_channel_id_from_link(bot: Bot, link: str) -> Optional[str]:
    """
    Получить ID канала из пригласительной ссылки.

    Поддерживаемые форматы:
    - https://t.me/+AbCdEfGhIjK12345 (private invite link)
    - https://t.me/joinchat/AbCdEfGhIjK12345 (old join chat link)
    - https://t.me/username (обычная ссылка)
    - t.me/+AbCdEfGhIjK12345
    - t.me/joinchat/AbCdEfGhIjK12345
    - t.me/username

    Args:
        bot: Экземпляр бота
        link: Ссылка на канал

    Returns:
        ID канала (например, '-1001234567890') или None если не удалось
    """
    try:
        # Очищаем ссылку от лишних символов
        link = link.strip()

        # Проверяем полную URL-ссылку на канал (https://t.me/username)
        match = re.match(r'https?://t\.me/([a-zA-Z0-9_]+)', link, re.IGNORECASE)
        if match:
            username = match.group(1)
            # Проверяем, не invite link ли это
            if username.startswith('+'):
                # Это invite link, обрабатываем ниже
                pass
            else:
                # Это username - возвращаем с @
                return f"@{username}"

        # Извлекаем часть после t.me/ для invite links
        match = re.search(r't\.me/(?:joinchat/)?(\S+)', link, re.IGNORECASE)
        if not match:
            return None

        invite_hash = match.group(1)

        # Убираем возможные лишние символы (например, ?utm_source)
        invite_hash = invite_hash.split('?')[0].split('&')[0]

        # Проверяем, не username ли это (начинается с @ или букв)
        if invite_hash.startswith('@'):
            return invite_hash  # Это username, возвращаем как есть

        # Пытаемся получить информацию о чате через ссылку
        try:
            # Для private invite links используем chat_invite_link
            chat = await bot.get_chat(f"https://t.me/+{invite_hash}")
            return str(chat.id)
        except TelegramBadRequest as e:
            if "CHAT_INVITE_LINK_INVALID" in str(e):
                logger.error(f"Неверная пригласительная ссылка: {invite_hash}")
                return None
            # Пробуем как username
            try:
                chat = await bot.get_chat(f"@{invite_hash}")
                return str(chat.id)
            except:
                pass

        # Если не получилось, пробуем как обычный username
        try:
            chat = await bot.get_chat(f"@{invite_hash}")
            return str(chat.id)
        except:
            pass

        return None

    except Exception as e:
        logger.error(f"Ошибка получения ID из ссылки {link}: {e}")
        return None


def parse_channel_input(text: str) -> tuple[Optional[str], str]:
    """
    Разобрать ввод пользователя и определить тип.

    Args:
        text: Ввод пользователя

    Returns:
        Кортеж (channel_id, error_message)
        Если успешно: (channel_id, "")
        Если ошибка: (None, "сообщение об ошибке")
    """
    text = text.strip()

    if not text:
        return None, "❌ Введите корректное значение"

    # Приватная ссылка (t.me/+... или https://t.me/+...)
    if re.search(r'(?:https?://)?t\.me/\+', text, re.IGNORECASE):
        return None, "LINK"  # Специальный маркер для обработки ссылки

    # Ссылка на присоединение (t.me/joinchat/...)
    if re.search(r'(?:https?://)?t\.me/joinchat/', text, re.IGNORECASE):
        return None, "LINK"

    # Полная URL-ссылка (https://t.me/username)
    if re.match(r'https?://t\.me/([a-zA-Z0-9_]+)', text, re.IGNORECASE):
        match = re.match(r'https?://t\.me/([a-zA-Z0-9_]+)', text, re.IGNORECASE)
        if match:
            username = match.group(1)
            return f"@{username}", ""

    # Username (@channel или channel без @)
    if text.startswith('@'):
        return text, ""

    # ID канала (-100...)
    if text.startswith('-100'):
        return text, ""

    # Просто текст (считаем username без @)
    if re.match(r'^[a-zA-Z0-9_]+$', text):
        return f"@{text}", ""

    return None, "❌ Неверный формат. Используйте @username, -100...ID или ссылку t.me/..."
