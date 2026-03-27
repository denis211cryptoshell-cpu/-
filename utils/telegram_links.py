"""
Утилиты для работы с ссылками Telegram.
"""

import re
from typing import Optional, Tuple
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

        # Извлекаем часть после t.me/
        match = re.search(r't\.me/(?:joinchat/)?(\S+)', link, re.IGNORECASE)
        if not match:
            return None

        invite_hash = match.group(1)

        # Убираем возможные лишние символы (например, ?utm_source)
        invite_hash = invite_hash.split('?')[0].split('&')[0]

        # Пытаемся получить информацию о чате разными способами
        
        # 1. Пробуем как private invite link (с +)
        try:
            chat = await bot.get_chat(f"https://t.me/+{invite_hash}")
            return str(chat.id)
        except TelegramBadRequest:
            pass

        # 2. Пробуем как username (с @)
        try:
            chat = await bot.get_chat(f"@{invite_hash}")
            return str(chat.id)
        except TelegramBadRequest:
            pass

        # 3. Пробуем без ничего (вдруг это ID)
        try:
            chat = await bot.get_chat(invite_hash)
            return str(chat.id)
        except TelegramBadRequest:
            pass

        return None

    except Exception as e:
        logger.error(f"Ошибка получения ID из ссылки {link}: {e}")
        return None


def parse_channel_input(text: str) -> Tuple[Optional[str], str]:
    """
    Разобрать ввод пользователя и определить тип.

    Поддерживает ВСЕ форматы:
    - @username
    - username (без @)
    - -1001234567890 (ID)
    - t.me/username
    - t.me/+invitehash (private link)
    - t.me/joinchat/invitehash
    - https://t.me/username
    - https://t.me/+invitehash

    Args:
        text: Ввод пользователя

    Returns:
        Кортеж (channel_id, error_message)
        Если успешно: (channel_id, "")
        Если ссылка: (None, "LINK") — специальная обработка
        Если ошибка: (None, "сообщение об ошибке")
    """
    text = text.strip()

    if not text:
        return None, "❌ Введите корректное значение"

    # Приватная ссылка (t.me/+... или https://t.me/+...)
    if re.search(r'(?:https?://)?t\.me/\+', text, re.IGNORECASE):
        return None, "LINK"

    # Ссылка на присоединение (t.me/joinchat/...)
    if re.search(r'(?:https?://)?t\.me/joinchat/', text, re.IGNORECASE):
        return None, "LINK"

    # Полная URL-ссылка (https://t.me/username или t.me/username)
    match = re.match(r'(?:https?://)?t\.me/([a-zA-Z0-9_]+)', text, re.IGNORECASE)
    if match:
        username = match.group(1)
        # Проверяем, не начинается ли с + (это уже обработано выше)
        if not username.startswith('+'):
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
